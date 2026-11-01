from app.services.usage import get_usage_summary, record_usage


def test_empty_usage_summary_when_log_is_missing(tmp_path, monkeypatch):
    log_path = tmp_path / "cost.jsonl"
    monkeypatch.setattr("app.services.usage.LOG_PATH", log_path)

    summary = get_usage_summary()

    assert summary == {
        "total_requests": 0,
        "total_cost_paise": 0.0,
        "estimated_usage_requests": 0,
        "by_date": {},
    }


def test_usage_records_are_summarized(tmp_path, monkeypatch):
    log_path = tmp_path / "cost.jsonl"
    monkeypatch.setattr("app.services.usage.LOG_PATH", log_path)

    record_usage(
        model="fake-primary",
        input_tokens=5,
        output_tokens=11,
        cost_paise=0.0,
        latency_ms=0,
        fallback_used=False,
    )
    record_usage(
        model="fake-fallback",
        input_tokens=3,
        output_tokens=7,
        cost_paise=0.0,
        latency_ms=0,
        fallback_used=True,
        usage_estimated=True,
    )

    summary = get_usage_summary()

    assert summary["total_requests"] == 2
    assert summary["total_cost_paise"] == 0.0
    assert summary["estimated_usage_requests"] == 1

    daily = next(iter(summary["by_date"].values()))
    assert daily["requests"] == 2
    assert daily["input_tokens"] == 8
    assert daily["output_tokens"] == 18
    assert daily["estimated_usage_requests"] == 1
