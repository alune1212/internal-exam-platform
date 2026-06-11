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

- Backend tests: 10 passed, with one Starlette TestClient deprecation warning.
- Frontend build: passed, with one Vite chunk size warning.
- Docker Compose: PostgreSQL healthy; backend, frontend, and Nginx running.
- `/api/health`: returned `{"success":true,"data":{"status":"ok","service":"internal-exam-platform"},"message":"ok"}`.

## Known Gaps

- Question import validates Excel rows and persists valid questions, options, and an import batch with failure details.
- Candidate import validates Excel rows and persists valid candidates plus an import batch with failure details.
- Exam creation/update/list services currently return skeleton data.
- Exam start returns a response shape but does not yet persist attempt snapshots.
- Answer autosave, submit scoring across persisted attempt questions, ranking, and reports still need real database queries.
- Admin authentication is a simple configured username/password placeholder.
- No frontend auth/session guard exists yet.

## Recommended Next Work

1. Add question import failure report download.
2. Define how an exam is scoped to imported candidates.
3. Implement active exam listing and exam CRUD persistence.
4. Implement exam start snapshot creation from active questions.
5. Implement answer autosave and submit scoring from snapshots.
6. Implement score, accuracy, wrong-question, and absent-candidate reports.
