import json
import time
from collections.abc import Iterator

import httpx

from app.config import Settings
from app.services.llm import LLMResponse, LLMStreamEvent
from app.services.retry import (
    PermanentLLMError,
    TransientLLMError,
    classify_http_status,
)


class OpenAICompatibleLLM:
    """Client for APIs that support the OpenAI chat-completions format."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def generate(self, question: str) -> LLMResponse:
        if not self.settings.llm_api_key:
            raise PermanentLLMError("LLM API key is not configured.")

        url = f"{self.settings.llm_base_url.rstrip('/')}/chat/completions"

        payload = {
            "model": self.settings.llm_model,
            "messages": [
                {"role": "user", "content": question},
            ],
        }

        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }

        started = time.perf_counter()

        try:
            with httpx.Client(
                timeout=self.settings.llm_timeout_seconds
            ) as client:
                response = client.post(
                    url,
                    json=payload,
                    headers=headers,
                )

        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise TransientLLMError(str(exc)) from exc

        if response.status_code >= 400:
            error_type = classify_http_status(response.status_code)
            raise error_type(
                f"LLM provider returned HTTP {response.status_code}."
            )

        try:
            data = response.json()
            answer = data["choices"][0]["message"]["content"]

            if not isinstance(answer, str):
                raise ValueError("Provider returned non-text content.")

        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise PermanentLLMError(
                "Invalid response format from LLM provider."
            ) from exc

        usage = data.get("usage") or {}
        usage_estimated = not (
            isinstance(usage.get("prompt_tokens"), int)
            and isinstance(usage.get("completion_tokens"), int)
        )

        if usage_estimated:
            input_tokens = max(
                1,
                len(question) // self.settings.estimated_chars_per_token,
            )
            output_tokens = max(
                1,
                len(answer) // self.settings.estimated_chars_per_token,
            )
        else:
            input_tokens = usage["prompt_tokens"]
            output_tokens = usage["completion_tokens"]

        cost_usd = (
            input_tokens * self.settings.price_input_per_million
            + output_tokens * self.settings.price_output_per_million
        ) / 1_000_000

        cost_paise = cost_usd * self.settings.usd_to_inr_rate * 100

        return LLMResponse(
            answer=answer,
            model=data.get("model", self.settings.llm_model),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_paise=round(cost_paise, 6),
            latency_ms=int((time.perf_counter() - started) * 1000),
            usage_estimated=usage_estimated,
        )


    def stream(self, question: str) -> Iterator[LLMStreamEvent]:
        """Stream text chunks from an OpenAI-compatible provider."""
        if not self.settings.llm_api_key:
            raise PermanentLLMError("LLM API key is not configured.")

        url = f"{self.settings.llm_base_url.rstrip('/')}/chat/completions"

        payload = {
            "model": self.settings.llm_model,
            "messages": [{"role": "user", "content": question}],
            "stream": True,
            "stream_options": {"include_usage": True},
        }

        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }

        started = time.perf_counter()
        answer_parts = []
        provider_usage = None
        model_name = self.settings.llm_model

        try:
            with httpx.Client(
                timeout=self.settings.llm_timeout_seconds
            ) as client:
                with client.stream(
                    "POST",
                    url,
                    json=payload,
                    headers=headers,
                ) as response:
                    if response.status_code >= 400:
                        error_type = classify_http_status(response.status_code)
                        raise error_type(
                            f"LLM provider returned HTTP {response.status_code}."
                        )

                    for line in response.iter_lines():
                        if not line.startswith("data:"):
                            continue

                        data_text = line.removeprefix("data:").strip()

                        if data_text == "[DONE]":
                            break

                        try:
                            data = json.loads(data_text)
                        except json.JSONDecodeError as exc:
                            raise PermanentLLMError(
                                "Invalid streaming response from LLM provider."
                            ) from exc

                        model_name = data.get("model", model_name)

                        usage = data.get("usage")
                        if isinstance(usage, dict):
                            provider_usage = usage

                        choices = data.get("choices") or []
                        for choice in choices:
                            delta = choice.get("delta") or {}
                            text = delta.get("content")

                            if isinstance(text, str) and text:
                                answer_parts.append(text)
                                yield LLMStreamEvent(
                                    text=text,
                                    model=model_name,
                                )

        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise TransientLLMError(str(exc)) from exc

        answer = "".join(answer_parts)

        usage = provider_usage or {}
        usage_estimated = not (
            isinstance(usage.get("prompt_tokens"), int)
            and isinstance(usage.get("completion_tokens"), int)
        )

        if usage_estimated:
            input_tokens = max(
                1,
                len(question) // self.settings.estimated_chars_per_token,
            )
            output_tokens = max(
                1,
                len(answer) // self.settings.estimated_chars_per_token,
            )
        else:
            input_tokens = usage["prompt_tokens"]
            output_tokens = usage["completion_tokens"]

        cost_usd = (
            input_tokens * self.settings.price_input_per_million
            + output_tokens * self.settings.price_output_per_million
        ) / 1_000_000

        cost_paise = cost_usd * self.settings.usd_to_inr_rate * 100

        result = LLMResponse(
            answer=answer,
            model=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_paise=round(cost_paise, 6),
            latency_ms=int((time.perf_counter() - started) * 1000),
            usage_estimated=usage_estimated,
        )

        yield LLMStreamEvent(final_response=result)
