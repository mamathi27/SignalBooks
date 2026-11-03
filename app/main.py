import json
from typing import Annotated

import psycopg
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from app.config import Settings, get_settings
from app.schemas import ChatRequest, ChatResponse
from app.services.llm import FakeLLM, FallbackLLM
from app.services.openai_compat import OpenAICompatibleLLM
from app.services.usage import get_usage_summary, record_usage

app = FastAPI(title="SignalBooks", version="0.3.0")

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_llm(settings: SettingsDep) -> FallbackLLM:
    """Build the configured primary model and its fallback."""
    if settings.llm_provider == "fake":
        primary = FakeLLM("fake-primary")
    elif settings.llm_provider == "openai_compatible":
        primary = OpenAICompatibleLLM(settings)
    else:
        raise ValueError(
            f"Unsupported LLM provider: {settings.llm_provider}"
        )

    fallback = FakeLLM(settings.llm_fallback_model)

    return FallbackLLM(
        primary=primary,
        fallback=fallback,
    )


LLMDep = Annotated[FallbackLLM, Depends(get_llm)]


@app.get("/health")
def health(settings: SettingsDep) -> dict:
    """Liveness: must not call the LLM or database."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
    }


@app.get("/ready")
def ready(settings: SettingsDep) -> dict:
    """Readiness: check PostgreSQL connectivity and pgvector."""
    if not settings.database_url:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "reason": "DATABASE_URL is not configured",
            },
        )

    try:
        with psycopg.connect(
            settings.database_url,
            connect_timeout=2,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT extversion FROM pg_extension "
                    "WHERE extname = 'vector'"
                )
                result = cursor.fetchone()

        if result is None:
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "not_ready",
                    "reason": "pgvector extension is not installed",
                },
            )

        return {
            "status": "ready",
            "database": "connected",
            "pgvector": "available",
            "pgvector_version": result[0],
        }

    except psycopg.Error:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "reason": "PostgreSQL connection or query failed",
            },
        ) from None


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, llm: LLMDep) -> ChatResponse:
    """Answer a question and record model usage."""
    result = llm.generate(request.question)

    record_usage(
        model=result.model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cost_paise=result.cost_paise,
        latency_ms=result.latency_ms,
        fallback_used=result.fallback_used,
        usage_estimated=result.usage_estimated,
    )

    return ChatResponse(
        answer=result.answer,
        model=result.model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cost_paise=result.cost_paise,
        latency_ms=result.latency_ms,
        fallback_used=result.fallback_used,
        usage_estimated=result.usage_estimated,
    )


@app.post("/chat/stream")
def chat_stream(
    request: ChatRequest,
    llm: LLMDep,
) -> StreamingResponse:
    """Stream provider-generated tokens using server-sent events."""

    def event_stream():
        final_response = None
        metadata_sent = False

        try:
            for event in llm.stream(request.question):
                if event.text:
                    if not metadata_sent:
                        metadata = {
                            "model": event.model or "unknown",
                            "fallback_used": event.fallback_used,
                            "usage_estimated": None,
                        }
                        yield (
                            f"event: metadata\ndata: "
                            f"{json.dumps(metadata)}\n\n"
                        )
                        metadata_sent = True

                    yield (
                        f"event: token\ndata: "
                        f"{json.dumps({'text': event.text})}\n\n"
                    )

                if event.final_response is not None:
                    final_response = event.final_response

            if final_response is None:
                yield (
                    "event: error\ndata: "
                    '{"message":"The model stream ended without a completion."}'
                    "\n\n"
                )
                return

            if not metadata_sent:
                metadata = {
                    "model": final_response.model,
                    "fallback_used": final_response.fallback_used,
                    "usage_estimated": final_response.usage_estimated,
                }
                yield (
                    f"event: metadata\ndata: "
                    f"{json.dumps(metadata)}\n\n"
                )

            record_usage(
                model=final_response.model,
                input_tokens=final_response.input_tokens,
                output_tokens=final_response.output_tokens,
                cost_paise=final_response.cost_paise,
                latency_ms=final_response.latency_ms,
                fallback_used=final_response.fallback_used,
                usage_estimated=final_response.usage_estimated,
            )

            completion = {
                "input_tokens": final_response.input_tokens,
                "output_tokens": final_response.output_tokens,
                "cost_paise": final_response.cost_paise,
                "latency_ms": final_response.latency_ms,
                "usage_estimated": final_response.usage_estimated,
            }
            yield (
                f"event: done\ndata: "
                f"{json.dumps(completion)}\n\n"
            )

        except Exception:
            yield (
                "event: error\ndata: "
                '{"message":"Streaming failed."}'
                "\n\n"
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

@app.get("/usage")
def usage() -> dict:
    """Return cumulative usage grouped by UTC date."""
    return get_usage_summary()
