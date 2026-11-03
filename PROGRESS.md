# SignalBooks Progress

Commit after every class. Tag each week only after all planned tasks are completed and verified.

## Week 1 (Tag: week-1)

- [x] Repo created from the Examate template and registered on the form
- [x] README top section filled from my project card
- [x] `/health` runs locally
- [x] `docs/QUESTIONS.md`: 10 real questions
- [x] 50+ pages collected, DATASET.md filled, sample in `data/sample/`
- [x] Tag `week-1` pushed

## Week 2 (Tag: week-2)

- [x] `POST /chat` calls an LLM and returns structured JSON
- [x] Streaming, timeouts, retry and fallback model foundations implemented
- [x] Cost log and `GET /usage`
- [ ] Docker Compose (API + Postgres/pgvector) full runtime verification
- [x] CI green and live deployment link in README
- [x] Tag `week-2` pushed

### Week 2 follow-up notes

- Docker image build and container `/health` smoke test completed successfully.
- Full Docker Compose API + PostgreSQL/pgvector runtime verification remains pending.
- Render `/health` currently reports `environment: local`; this is a non-blocking configuration follow-up.
- Gemini integration was tested successfully through the deployed API.

## Week 3 (Tag: week-3 by Fri 6 Nov)

- [ ] Parser keeps page numbers and headings
- [ ] 500+ pages chunked, embedded and stored in pgvector
- [ ] `POST /ask` answers with `[document, page]` citations
- [ ] `docs/EVAL_v0.md` with my 10 questions scored
- [ ] Tests, lint and documentation verified
- [ ] Tag `week-3` pushed

## Daily log

| Date | What I did | Commit(s) |
|---|---|---|
| 2026-10-21 | Created the initial repository, added the README and project name | `950e7d9`, `8d38c6f`, `3cfb9c3` |
| 2026-10-22 | Removed large research PDFs from Git tracking and documented the dataset inventory | `03fa9df`, `d76ed2c` |
| 2026-10-23 | Completed Week 1 dataset collection and documentation; fixed CI import path and dependency/lint issues | `a6c1a58`, `a5ee1f3`, `a0d1e3c` |
| 2026-10-29 | Added reliable LLM retry and usage foundations | `b8d947f` |
| 2026-11-01 | Implemented LLM integration and cost tracking, added PostgreSQL/pgvector readiness, completed Week 2 documentation and deployment setup, isolated tests from external LLM configuration, and documented Gemini configuration and usage costs | `7f005c2`, `d007a51`, `6c7390f`, `ae19395`, `7fe4716` |