
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
