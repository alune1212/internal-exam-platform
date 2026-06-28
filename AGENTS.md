# AGENTS.md

This project is a lightweight internal exam and practice platform. Keep changes simple, local, and aligned with the first-phase scaffold.

## Project Shape

- Backend: `backend/`, FastAPI, Pydantic, SQLAlchemy 2.0, Alembic, PostgreSQL, openpyxl.
- Frontend: `frontend/`, React, TypeScript, Vite, Tailwind CSS, shadcn-compatible local components, React Router, TanStack Query/Table, React Hook Form, Zod.
- Deployment: `docker-compose.yml` launches PostgreSQL, backend, frontend, and Nginx. Public API paths stay under `/api`.
- Runtime entrypoints: backend dev port `8000`, browser entry (Compose/Nginx) `8080`.
- Docs: `README.md` as startup guide; `docs/requirements.md`, `docs/database-design.md`, `docs/api-design.md`, `docs/import-templates.md`, `docs/official-exam-uat-checklist.md`, and `docs/handoff.md` are the reference docs.

## Hard Boundaries

- Do not add Redis, Celery, microservices, complex RBAC, or queue-based imports in the first phase.
- Do not add Word parsing. The first import path is standardized Excel only.
- Keep backend business logic in `backend/app/services/`; route files should stay thin.
- All request and response shapes should use Pydantic schemas from `backend/app/schemas/`.
- Preserve exam snapshot semantics: historical attempts must use saved question, option, answer, analysis, score, and order snapshots.
- Preserve fixed-paper semantics:
  - empty `exam.question_rule = {}` keeps legacy all-active behavior.
  - non-empty `question_rule` with `question_count` must pick active unique stems from frozen paper rules, using `type_counts` that sum to `question_count`.
  - integer scores must be distributed evenly from `total_score`.
  - snapshots must be persisted per attempt.
- Multiple-choice scoring must compare answer sets, not raw strings.
- Keep frontend API calls in `frontend/src/api/`; pages should not hand-roll fetch details.
- Preserve the frontend redesign system: use `frontend/src/index.css` tokens, Tailwind aliases, local UI primitives, and editorial components instead of reintroducing HSL shadcn tokens or ad hoc page styling.
- Current hardening boundary remains lightweight internal-tool scope (no LMS, no full anti-cheat/monitoring suite).

## Commands

Backend:

```bash
cd backend
uv sync
uv run ruff format . --check
uv run ruff check .
uv run ty check
uv run pytest
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run format:check
npm test -- --run
npm run lint
npm run build
npm run dev
```

Docker:

```bash
docker-compose --env-file .env config
docker-compose up -d --build
```

Health checks:

```bash
curl http://localhost:8000/api/health
curl http://localhost:8080/api/health
curl http://localhost:8080/docs
```

## Current Stage

The project has an end-to-end first-phase business loop and completed Academic Editorial frontend redesign, with DB migration and deployment wiring in place.

- Question Excel import and candidate Excel import validate rows, enforce bounded uploads (default 5 MiB, 5000 rows, 1 sheet), persist valid records, and persist `import_batch` metadata.
- Failure report export is available as Excel for question, candidate, and exam-candidate imports.
- Exam configuration create/update/list, candidate-scoped active exam listing, publish-time frozen `exam_question_pool`, and fixed-paper generation are implemented.
- Exam start creates in-progress attempts with persisted question snapshots and supports answer autosave + resume.
- Submit flow persists answers, scores from snapshot data, calculates pass status, and handles retake grants.
- Time-based auto-submit background checks run periodically (every 30s).
- Ranking and report SQL queries support exam filter and multi-sheet Excel report export (score, accuracy, wrong questions, absent candidates).
- Candidate login uses name + phone last 4 digits (optional employee number), and candidate-practice APIs are token-gated via `X-Candidate-Token`.
- Admin login/session uses signed tokens, with `X-Admin-Token` protection and production-safe defaults checks for secret/password/CORS.
- Route/service boundaries, token handling, schema usage, and import/report persistence are all persisted against real DB state.

Current known quality baseline includes passing backend format/lint/type/tests and frontend format/lint/build/tests from the latest verification pass.
