# LexiLearn

LexiLearn is a FastAPI and React application for English classes, assignments, submissions,
and IELTS Speaking practice. The primary application stays in `backend/` and `frontend/`.
The current implementation is a modular monolith; the live module and route map is in
[`docs/architecture/current-system.md`](docs/architecture/current-system.md).

Teacher access currently uses the configured teacher code. Learners join from a class link and
enter a name stored in browser local storage. These flows are existing application context, not
an Admin/RBAC security system.

## Documentation

- [Current system map](docs/architecture/current-system.md): modules, routes, API clients, data and provider boundaries.
- [Refactor handoff report](docs/verification/refactor-handoff-report.md): compatibility checks, test results, limitations and screenshots.
- [Whisper runtime hardening](docs/verification/whisper-runtime-hardening.md): concurrency, fallback, timeouts, configuration and real model checks.
- [Product design direction](DESIGN.md): design principles and planned roles; Admin pages are not implemented.
- [Role/page inventory](docs/design/role-page-inventory.md) and [Stitch brief](docs/design/stitch-redesign-brief.md): inputs for the next design phase.
- [Current cleanup plan](docs/plans/project-cleanup-refactor-plan.md).
- [Historical documents](docs/archive/README.md): original plans and research preserved with root filename links.

## Current architecture

```text
Browser ──► React/Vite or nginx ──► FastAPI ──► PostgreSQL or SQLite tests
                                      │
                                      ├── feature modules: classes, assignments, submissions,
                                      │                    speaking, writing
                                      ├── integrations: audio, storage, STT, LLM, OCR
                                      └── persistent Speaking jobs + worker
```

Speaking results use the existing `speaking-v3` contract. Partial results, null bands, uncertainty,
and evidence IDs remain part of the response. Pronunciation is not inferred from transcript text
or ASR confidence. These are diagnostic practice results, not official IELTS scores.

The UI layout has not been redesigned in this refactor. Use the Stitch brief and review the actual
route/API gaps before changing production screens.

## Development

```bash
# Backend
cd backend
./.venv/bin/python -m pytest -q
./.venv/bin/ruff check app tests scripts
./.venv/bin/uvicorn app.main:app --reload

# Frontend
cd frontend
npm ci
npm run lint
npm run build
npx playwright test
```

The Playwright config starts Vite and FastAPI on temporary ports with a disposable SQLite database,
temporary storage, and explicit mock providers. It does not reuse an already-running development
server. The API diagnostic scripts also use a disposable database and storage; see
[`backend/scripts/diagnostics/README.md`](backend/scripts/diagnostics/README.md).

For a local Docker stack, configure `.env` from `.env.example`, then run `docker compose up --build`.
The compose stack uses persistent named volumes; do not point it at test or production data without
checking the configured environment first.

## Scope and next step

The current API supports teacher class/assignment management, student join and submissions, and
Speaking practice/mock/history. Admin management, account-based RBAC, attendance, teacher approval
and release settings are not implemented. The next planned project phase is UI design in Stitch,
starting with Speaking practice, Mock, feedback, and teacher review.
