# Current system map

Updated 2026-10-18 after the modular monolith refactor. This describes the routes and modules
present in the repository; it does not describe planned Admin or teacher review capabilities as
implemented features.

## Runtime shape

```text
Browser → React routes/layouts → Vite / nginx → FastAPI routers → feature modules
                                                        ├─ SQLAlchemy Base + session
                                                        ├─ audio / storage / STT / LLM / OCR adapters
                                                        └─ durable Speaking jobs + worker
```

Vite proxies `/api` and `/storage` to FastAPI in development. Nginx proxies `/api/` and `/storage/`
in the container. FastAPI mounts local media at `/storage`. Production compose config uses
PostgreSQL and named volumes; tests and Playwright use disposable SQLite and storage paths.

## Frontend routes and shells

The route tree is in `frontend/src/app/App.jsx`; `frontend/src/main.jsx` remains the Vite entry.

| Route | View | Shell |
|---|---|---|
| `/` | Redirects to `/teacher` | — |
| `/join` | Join a class with a share code | `PublicLayout` |
| `/teacher` | Teacher dashboard and access-code state | `TeacherLayout` |
| `/teacher/class/:classId` | Class workspace and submission review | `TeacherLayout` |
| `/teacher/class/:classId/new` | Assignment builder | `TeacherLayout` |
| `/teacher/class/:classId/edit/:assignmentId` | Assignment editor | `TeacherLayout` |
| `/student/:classId` | Learner class home and history | `StudentLayout` |
| `/student/:classId/assignment/:assignmentId` | Assignment attempt | `StudentLayout` |
| `/speaking` | Speaking dashboard | `SpeakingLayout` |
| `/speaking/practice` | Topic selection and practice | `SpeakingLayout` |
| `/speaking/practice/:topicId` | Topic-specific practice | `SpeakingLayout` |
| `/speaking/mock-test` | Mock session for the first available topic | `SpeakingLayout` |
| `/speaking/mock-test/:testId` | Mock session selected by topic ID | `SpeakingLayout` |
| `/speaking/history` | Speaking history and progress | `SpeakingLayout` |

The mock route parameter is resolved as a topic ID by `useMockController`; loading that route
creates a new server session. It does not restore a saved session from a session ID. Treat resume
and reconnect as design/backend gaps until the session URL and API are changed deliberately.

The layouts are presentation and navigation boundaries. Teacher access code and learner name
remain the current context mechanism; the role shells are not authorization or RBAC.

## Backend ownership

| Area | Owner |
|---|---|
| App creation, settings, access dependency, lifecycle, readiness | `backend/app/main.py`, `core/`, `modules/registry.py` |
| SQLAlchemy metadata, engine/session, model registration | `db/base.py`, `db/session.py`, `db/registry.py` |
| Class routes, schema, model | `modules/classes/` |
| Assignment routes, schema, model, delete use case | `modules/assignments/` |
| Submissions, review, roster, objective grading | `modules/submissions/` |
| Practice, mock turns, durable job processing, assessment, result adapters | `modules/speaking/` |
| Writing assessment and OCR coordination | `modules/writing/` and `integrations/ocr/` |
| Provider and media boundaries | `integrations/audio/`, `storage/`, `stt/`, `llm/`, `ocr/` |
| Budget guard, retention, speaking seed data | `operations/` |
| Shared Writing background helper | `core/background.py` |

`db/base.py` defines the sole declarative `Base`. `db/registry.py` imports every model before
`core/bootstrap.py` calls `create_all`. Startup also preserves the prior additive `classes.level`
bootstrap, seed behavior, provider readiness, durable worker start/recovery, and retention lifecycle.
Worker jobs open their own database session; no request session is kept for later work.

Speaking assessment orchestration lives in `modules/speaking/assessment/engine.py`. Contracts,
raters, rubric and scoring are separate modules. Pronunciation acoustic analysis/alignment are
under `modules/speaking/pronunciation/`. Provider transport is in `integrations/llm/`; speech
recognition is in `integrations/stt/`. Provider mock mode is explicit. Missing production
credentials report not-ready or fail the provider request; the app does not silently substitute a
mock. ASR confidence and transcript text do not create pronunciation scores.

## HTTP API inventory

The inventory below is the generated OpenAPI surface. The refactor comparison found the same
23 paths, 29 operations and 21 schemas as the baseline.

| Owner | Methods and paths |
|---|---|
| Classes | `GET, POST /api/v1/classes`; `GET, PATCH, DELETE /api/v1/classes/{class_id}`; `GET /api/v1/classes/{class_id}/assignments`; `GET /api/v1/classes/{class_id}/roster`; `GET /api/v1/join` |
| Assignments | `POST /api/v1/assignments`; `GET, PATCH, DELETE /api/v1/assignments/{assignment_id}`; `GET /api/v1/teacher/assignments/{assignment_id}` |
| Submissions | `POST /api/v1/assignments/{assignment_id}/submit`; `GET /api/v1/assignments/{assignment_id}/submissions`; `GET, PATCH /api/v1/submissions/{submission_id}` |
| Speaking | `GET /api/v1/speaking/history`; `POST /api/v1/speaking/mock-sessions`; `GET /api/v1/speaking/mock-sessions/{session_id}`; `POST /api/v1/speaking/mock-sessions/{session_id}/complete`; `POST /api/v1/speaking/mock-sessions/{session_id}/turns`; `POST /api/v1/speaking/practice`; `GET /api/v1/speaking/practice/{session_id}`; `GET /api/v1/speaking/progress`; `GET /api/v1/speaking/questions`; `GET /api/v1/speaking/topics` |
| Runtime | `GET /health`; `GET /ready` |

Feature API clients call a shared fetch transport in `frontend/src/shared/api/transport.js`:
`features/classes/api.js`, `assignments/api.js`, `submissions/api.js`, and `speaking/api.js`.
They retain the existing URLs, form field names, headers and response handling.

## Persistent data

The ORM snapshot contains the same 12 tables and columns, foreign keys, relationship targets and
cascades as the baseline:

`assignments`, `classes`, `exam_sets`, `practice_sessions`, `questions`,
`speaking_assessment_jobs`, `speaking_mock_sessions`, `speaking_questions`, `speaking_topics`,
`speaking_turns`, `submissions`, and `topics`.

The generic `Topic`/`Question` models remain registered as legacy data; they were not merged with
the Speaking-specific models. Production PostgreSQL, SQLite test databases, existing storage,
audio and model-cache paths remain in place.

## Speaking state ownership

`usePracticeController` and `useMockController` own question/session loading, part/question state,
preparation countdowns, submit/poll state, cancellation and error transitions. Part 2 preparation
uses a fixed deadline so delayed background timer ticks do not extend the minute. API requests and
polls use `AbortController`; unmount aborts active work. The recorder owns the microphone stream,
MediaRecorder, timer and WaveSurfer instance; cleanup stops tracks, clears the timer, destroys the
waveform and revokes its object URL. Recording start cancels browser speech synthesis. Practice
and Mock remain separate workflows because their persisted session semantics differ.

The external result contract remains `speaking-v3`: nullable/partial criteria, uncertainty,
evidence identifiers and the legacy result adapter are retained. A missing pronunciation band
stays null; no band is inferred from a transcript or ASR confidence.

## Design/data gaps for the next phase

- `DESIGN.md` includes Admin and richer teacher workflows, but there is no Admin route, account
  system, RBAC or Admin backend in this codebase.
- Teacher Speaking review, teacher release/approval and request-a-record-again lifecycle are not
  implemented. Existing submission edits do not provide a review audit trail.
- Progress is limited to current Speaking history/progress endpoints; do not invent cross-skill
  learner profiles or KPI values in a design.
- A Mock route with `:testId` currently selects a topic and starts a fresh session; it is not a
  session-resume URL.
- Microphone setup/level testing, server-side reconnect/resume, and several audio-expiry/review
  states in the design inventory need API/product decisions before implementation.

Use `docs/design/role-page-inventory.md` and `docs/design/stitch-redesign-brief.md` for the planned
screen IDs and state matrix. No UI redesign or Stitch project was created in this refactor.
