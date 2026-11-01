import json
from typing import Annotated

from fastapi import Depends, FastAPI
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
    """Stream a completed answer using simulated SSE chunks."""
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

    def event_stream():
        metadata = {
            "model": result.model,
            "fallback_used": result.fallback_used,
            "usage_estimated": result.usage_estimated,
        }
        yield f"event: metadata\ndata: {json.dumps(metadata)}\n\n"

        # This simulates token chunks; it is not provider-side streaming.
        chunk_size = 12
        for start in range(0, len(result.answer), chunk_size):
            chunk = result.answer[start : start + chunk_size]
            yield f"event: token\ndata: {json.dumps({'text': chunk})}\n\n"

        completion = {
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "cost_paise": result.cost_paise,
            "latency_ms": result.latency_ms,
            "usage_estimated": result.usage_estimated,
        }
        yield f"event: done\ndata: {json.dumps(completion)}\n\n"

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
