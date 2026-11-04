
import json


def test_chat_stream_returns_sse_events(client, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.usage.LOG_PATH",
        tmp_path / "cost.jsonl",
    )

    response = client.post(
        "/chat/stream",
        json={"question": "What is ARPU?"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    body = response.text

    assert "event: metadata\n" in body
    assert "event: token\n" in body
    assert "event: done\n" in body

    # Parse SSE data and reconstruct the answer from token chunks.
    events = []
    for block in body.strip().split("\n\n"):
        lines = block.splitlines()
        event_name = next(
            (line.removeprefix("event: ") for line in lines if line.startswith("event: ")),
            None,
        )
        data_line = next(
            (line.removeprefix("data: ") for line in lines if line.startswith("data: ")),
            None,
        )

        if event_name and data_line:
            events.append((event_name, json.loads(data_line)))

    metadata = next(data for name, data in events if name == "metadata")
    chunks = [data["text"] for name, data in events if name == "token"]
    completion = next(data for name, data in events if name == "done")

    assert metadata["model"] == "fake-primary"
    assert "".join(chunks) == (
        "[Simulated answer from fake-primary] You asked: What is ARPU?"
    )
    assert completion["cost_paise"] == 0.0
    assert (tmp_path / "cost.jsonl").exists()


def test_chat_stream_rejects_empty_question(client):
    response = client.post(
        "/chat/stream",
        json={"question": ""},
    )

    assert response.status_code == 422

def test_chat_stream_reports_fallback_metadata(client, tmp_path, monkeypatch):
    from app.main import app, get_llm
    from app.services.llm import FakeLLM, FallbackLLM

    monkeypatch.setattr(
        "app.services.usage.LOG_PATH",
        tmp_path / "fallback-cost.jsonl",
    )
    monkeypatch.setattr(
        "app.services.retry.time.sleep",
        lambda delay: None,
    )

    app.dependency_overrides[get_llm] = lambda: FallbackLLM(
        FakeLLM("primary", should_fail=True),
        FakeLLM("fake-fallback"),
    )

    response = client.post(
        "/chat/stream",
        json={"question": "What is ARPU?"},
    )

    body = response.text
    metadata_block = next(
        block for block in body.split("\n\n")
        if block.startswith("event: metadata")
    )
    metadata = json.loads(
        next(
            line.removeprefix("data: ")
            for line in metadata_block.splitlines()
            if line.startswith("data: ")
        )
    )

    assert response.status_code == 200
    assert metadata["model"] == "fake-fallback"
    assert metadata["fallback_used"] is True
    assert "event: done\n" in body
    assert (tmp_path / "fallback-cost.jsonl").exists()


def test_chat_stream_reports_error_after_partial_output(
    client,
    tmp_path,
    monkeypatch,
):
    from app.main import app, get_llm
    from app.services.llm import FallbackLLM, LLMStreamEvent
    from app.services.retry import TransientLLMError

    class PartialFailureLLM:
        def generate(self, question):
            raise AssertionError("generate() must not be called")

        def stream(self, question):
            yield LLMStreamEvent(
                text="partial answer",
                model="primary",
            )
            raise TransientLLMError("Connection lost")

    class NeverUseFallback:
        def generate(self, question):
            raise AssertionError("Fallback must not be called")

        def stream(self, question):
            raise AssertionError("Fallback must not be called")
            yield

    usage_path = tmp_path / "failed-cost.jsonl"
    monkeypatch.setattr(
        "app.services.usage.LOG_PATH",
        usage_path,
    )

    app.dependency_overrides[get_llm] = lambda: FallbackLLM(
        PartialFailureLLM(),
        NeverUseFallback(),
    )

    response = client.post(
        "/chat/stream",
        json={"question": "What is ARPU?"},
    )

    body = response.text

    assert response.status_code == 200
    assert "event: token\n" in body
    assert "partial answer" in body
    assert "event: error\n" in body
    assert "event: done\n" not in body
    assert not usage_path.exists()
