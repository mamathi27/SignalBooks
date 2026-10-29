
import json
from datetime import UTC, datetime
from pathlib import Path

LOG_PATH = Path("logs/cost.jsonl")


def record_usage(
    *,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost_paise: float,
    latency_ms: int,
    fallback_used: bool,
) -> None:
    """Append one successful model call to the JSONL usage log."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_paise": cost_paise,
        "latency_ms": latency_ms,
        "fallback_used": fallback_used,
    }

    with LOG_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")


def get_usage_summary() -> dict:
    """Summarize logged calls grouped by UTC date."""
    if not LOG_PATH.exists():
        return {"total_requests": 0, "total_cost_paise": 0.0, "by_date": {}}

    by_date = {}

    with LOG_PATH.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue

            record = json.loads(line)
            date = record["timestamp"][:10]

            daily = by_date.setdefault(
                date,
                {
                    "requests": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_paise": 0.0,
                },
            )

            daily["requests"] += 1
            daily["input_tokens"] += record["input_tokens"]
            daily["output_tokens"] += record["output_tokens"]
            daily["cost_paise"] += record["cost_paise"]

    return {
        "total_requests": sum(day["requests"] for day in by_date.values()),
        "total_cost_paise": round(
            sum(day["cost_paise"] for day in by_date.values()), 4
        ),
        "by_date": by_date,
    }
