# Handoff

## Current State

The project is at first-phase scaffold completion. It has a runnable backend, frontend, database migration, Docker Compose stack, and documentation set.

Implemented foundations:

- FastAPI app with `/api/health`.
- SQLAlchemy models for candidates, questions, options, exams, attempts, attempt question snapshots, answers, practice answers, and import batches.
- Alembic initial migration `202606110001_initial_schema.py`.
- Candidate-facing and admin-facing API route skeletons.
- Scoring service with tested multiple-choice set comparison.
- Question Excel import persistence for valid questions, options, and import batches.
- Candidate Excel import persistence for valid candidates and import batches.
- Exam configuration create/update/list persistence and candidate-facing active exam listing.
- Exam start persistence with attempt creation and question snapshots.
- Answer autosave persistence and submit scoring from persisted attempt snapshots.
- React/Vite frontend with candidate and admin layouts.
- Candidate pages for login, practice, exam list, exam start, exam taking, result, and ranking.
- Admin pages for login, dashboard, question list/import, exam list/edit, candidate import, and reports.
- Docker Compose stack for PostgreSQL, backend, frontend, and Nginx.

## Verified Commands

Verified on 2026-06-11:

```bash
cd backend && uv run pytest
cd frontend && npm run build
docker-compose config
DATABASE_URL=postgresql+psycopg://exam:exam@localhost:5432/internal_exam uv run alembic upgrade head
docker-compose up -d --build
curl http://localhost:8080/api/health
curl -I http://localhost:8080
curl -I http://localhost:8080/docs
```

Observed results:

- Backend tests: 28 passed, with one Starlette TestClient deprecation warning.
- Frontend build: passed, with one Vite chunk size warning.
- Docker Compose: PostgreSQL healthy; backend, frontend, and Nginx running.
- `/api/health`: returned `{"success":true,"data":{"status":"ok","service":"internal-exam-platform"},"message":"ok"}`.

## Known Gaps

- Question import validates Excel rows and persists valid questions, options, and an import batch with failure details.
- Candidate import validates Excel rows and persists valid candidates plus an import batch with failure details.
- Exam configuration create/update/list services persist to the `exam` table, and active listing returns only `active` exams.
- Exam start creates an in-progress attempt and stores question snapshots.
- Answer autosave writes to `exam_attempt_answer`; submit scoring updates persisted answers and attempt totals.
- Time-based auto-submit runs as an asyncio background task, checking every 30 seconds.
- Ranking and reports (score, accuracy, wrong questions, absent candidates) use real SQL queries.
- Admin authentication is a simple configured username/password placeholder.
- No frontend auth/session guard exists yet.

## Recommended Next Work

1. Add question import failure report download.
2. Define how an exam is scoped to imported candidates.
3. Add frontend auth/session guard for candidate and admin pages.
