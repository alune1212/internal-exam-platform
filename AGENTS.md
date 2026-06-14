# AGENTS.md

This project is a lightweight internal exam and practice platform. Keep changes simple, local, and aligned with the first-phase scaffold.

## Project Shape

- Backend: `backend/`, FastAPI, Pydantic, SQLAlchemy 2.0, Alembic, PostgreSQL, openpyxl.
- Frontend: `frontend/`, React, TypeScript, Vite, Tailwind CSS, shadcn-compatible local components, React Router, TanStack Query/Table, React Hook Form, Zod.
- Deployment: `docker-compose.yml` starts PostgreSQL, backend, frontend, and Nginx. Public API paths stay under `/api`.
- Docs: `README.md` is the startup guide. `docs/requirements.md`, `docs/database-design.md`, `docs/api-design.md`, `docs/import-templates.md`, and `docs/handoff.md` are the handoff references.

## Hard Boundaries

- Do not add Redis, Celery, microservices, or complex RBAC in the first phase.
- Do not add Word parsing. The first import path is standardized Excel only.
- Keep backend business logic in `backend/app/services/`; route files should stay thin.
- All request and response shapes should use Pydantic schemas from `backend/app/schemas/`.
- Preserve exam snapshot semantics: historical attempts must use saved question, option, answer, analysis, score, and order snapshots.
- Multiple-choice scoring must compare answer sets, not raw strings.
- Keep frontend API calls in `frontend/src/api/`; pages should not hand-roll fetch details.
- Preserve the frontend redesign system: use `frontend/src/index.css` tokens, Tailwind aliases, local UI primitives, and editorial components instead of reintroducing HSL shadcn tokens or ad hoc page styling.

## Commands

Backend:

```bash
cd backend
uv run pytest
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run build
npm run dev
```

Docker:

```bash
docker-compose config
docker-compose up -d --build
```

Health checks:

```bash
curl http://localhost:8000/api/health
curl http://localhost:8080/api/health
```

## Current Stage

The scaffold is runnable and the first-phase business loop is implemented. Question Excel import and candidate Excel import validate rows and persist records plus import batches. Exam configuration create/update/list, candidate-facing active exam listing, exam start snapshots, answer autosave, submit scoring, time-based auto-submit checks, ranking, and basic report SQL persist/query real database state. Remaining first-phase gaps are import failure report download, explicit exam-to-candidate scoping, report file export, and frontend/admin session guards. The frontend has completed the Academic Editorial redesign across tokens, primitives, layouts, P0/P1/P2 pages, states, polish, and Docker rebuild verification.
