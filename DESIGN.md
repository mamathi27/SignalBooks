# SignalBooks â€” System Design

## 1. Overview

SignalBooks is a FastAPI-based question-answering application designed to help ECE students prepare for interviews at telecom and network-equipment companies.

The application supports configurable LLM providers, retry and fallback handling, token usage tracking, and estimated request-cost reporting.

## 2. Technology Stack

| Component | Technology |
|---|---|
| Backend API | FastAPI |
| Language | Python |
| Request validation | Pydantic |
| HTTP client | HTTPX |
| LLM integration | OpenAI-compatible API |
| Development provider | FakeLLM |
| Usage logging | JSON Lines (JSONL) |
| Database | PostgreSQL 16 |
| Vector extension | pgvector |
| Containerization | Docker |
| Local orchestration | Docker Compose |

## 3. Application Structure

    app/
    â”œâ”€â”€ main.py
    â”œâ”€â”€ config.py
    â”œâ”€â”€ schemas.py
    â””â”€â”€ services/
        â”œâ”€â”€ llm.py
        â”œâ”€â”€ openai_compat.py
        â”œâ”€â”€ retry.py
        â””â”€â”€ usage.py

### Module Responsibilities

- `main.py`: FastAPI application, dependency injection, API endpoints, and database readiness checks.
- `config.py`: Environment-based application, LLM, pricing, and database configuration.
- `schemas.py`: Pydantic request and response validation.
- `services/llm.py`: LLM interface, fake provider, response model, and fallback orchestration.
- `services/openai_compat.py`: HTTP integration with OpenAI-compatible chat-completion APIs and token-cost calculation.
- `services/retry.py`: HTTP error classification and retry handling.
- `services/usage.py`: JSONL usage logging and daily usage aggregation.

## 4. API Design

| Method | Endpoint | Responsibility |
|---|---|---|
| GET | `/health` | Application liveness check |
| GET | `/ready` | PostgreSQL connectivity and pgvector readiness check |
| POST | `/chat` | Generate an answer and record usage |
| POST | `/chat/stream` | Return a completed answer through simulated SSE chunks |
| GET | `/usage` | Return cumulative usage statistics grouped by UTC date |

### Chat Request

    {
      "question": "What was Airtel's ARPU?"
    }

The question must contain between 1 and 4000 characters.

### Chat Response

The response includes:

- Answer text
- Model name
- Input and output token counts
- Estimated cost in paise
- Request latency in milliseconds
- Fallback usage indicator
- Estimated token usage indicator

## 5. LLM Request Flow

1. The client submits a question to `/chat`.
2. FastAPI validates the request using `ChatRequest`.
3. Dependency injection constructs the configured primary LLM and fallback.
4. The primary provider processes the question.
5. Transient failures are retried up to three attempts.
6. If the primary remains unavailable after transient failures, the fallback provider is used.
7. The resulting response is recorded in the usage log.
8. The API returns a structured `ChatResponse`.

The current fallback configured by the application is a `FakeLLM`.

## 6. Retry and Error Handling

The retry service classifies provider errors into:

- Transient errors: HTTP 429, 500, 502, 503, and 504, along with other HTTP 5xx responses.
- Permanent errors: HTTP 400, 401, 403, 404, and other responses not classified as transient.

Transient failures use exponential backoff with full jitter.

Retry configuration:

- Maximum attempts: 3
- Base delay: 0.5 seconds
- Maximum backoff limit: 8 seconds

Permanent failures are not retried.

## 7. Usage and Cost Tracking

Successful model calls are appended to:

`logs/cost.jsonl`

Each record contains:

- UTC timestamp
- Model name
- Input tokens
- Output tokens
- Cost in paise
- Latency
- Fallback indicator
- Estimated usage indicator

The `/usage` endpoint aggregates request counts, token counts, and costs by UTC date.

### Cost Calculation

The cost calculation uses configurable USD prices per million tokens.

    Cost USD =
    (Input Tokens Ã— Input Price per Million
     + Output Tokens Ã— Output Price per Million)
    / 1,000,000

    Cost Paise = Cost USD Ã— USD-to-INR Rate Ã— 100

When provider token counts are unavailable, token usage is estimated using the configured characters-per-token value.

See `docs/COST.md` for detailed cost-tracking documentation.

## 8. Streaming Behavior

The `/chat/stream` endpoint currently generates the complete LLM response before emitting Server-Sent Events.

It then sends metadata, simulated text chunks, and completion usage information.

This is simulated SSE delivery and is not genuine provider-side token streaming.

## 9. Database and Readiness

SignalBooks includes PostgreSQL 16 with the pgvector extension through Docker Compose.

The initialization script enables the vector extension.

The `/ready` endpoint:

1. Checks whether `DATABASE_URL` is configured.
2. Connects to PostgreSQL.
3. Checks whether the `vector` extension is installed.
4. Returns the extension version when available.

At this stage, PostgreSQL is used for readiness verification. Usage records are stored separately in the JSONL file and are not persisted to PostgreSQL.

## 10. Health Checks

- `/health` checks application liveness without contacting the LLM or database.
- `/ready` checks database connectivity and pgvector availability.

Docker Compose uses a database health check before starting the API service.

## 11. Current Limitations

- The default application provider is the fake provider.
- Real provider integration requires valid API credentials and provider configuration.
- The configured fallback is a fake provider.
- Usage tracking currently uses a local JSONL file.
- PostgreSQL is not yet used for application usage persistence.
- Streaming currently simulates SSE chunks after completing generation.
- Document retrieval and source-grounded answering are not yet described as implemented in this architecture.

## 12. Future Architecture Work

Potential future improvements include:

- Persistent usage storage in PostgreSQL.
- Document ingestion and text extraction.
- Vector embeddings and pgvector-based retrieval.
- Retrieval-augmented generation with source references.
- Genuine provider-side streaming.
- More robust evaluation of routing quality and cost.
