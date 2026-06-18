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
- Preserve fixed-paper semantics: non-empty `exam.question_rule` with `question_count` samples an active, unique-stem paper by rule, assigns integer scores evenly from `total_score`, and stores attempt snapshots; empty `{}` keeps the legacy all-active behavior.
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

The scaffold is runnable and the first-phase business loop is implemented. Question Excel import and candidate Excel import validate rows and persist records plus import batches; import failure reports are downloadable as Excel. Exam configuration create/update/list, exam-scoped candidate import, candidate-scoped active exam listing, fixed 50-question equivalent papers, exam start snapshots, answer autosave, submit scoring with pass status, time-based auto-submit checks, ranking, report SQL queries, Excel report export, and signed admin session tokens persist/query real database state. The hardening gate adds bounded Excel uploads, escaped Excel exports, production config checks for secrets/CORS, and locked save/submit attempt loading. The frontend has completed the Academic Editorial redesign across tokens, primitives, layouts, P0/P1/P2 pages, states, polish, and Docker rebuild verification.


<!-- headroom:rtk-instructions -->
# RTK (Rust Token Killer) - Token-Optimized Commands

When running shell commands, **always prefix with `rtk`**. This reduces context
usage by 60-90% with zero behavior change. If rtk has no filter for a command,
it passes through unchanged — so it is always safe to use.

## Key Commands
```bash
# Git (59-80% savings)
rtk git status          rtk git diff            rtk git log

# Files & Search (60-75% savings)
rtk ls <path>           rtk read <file>         rtk grep <pattern>
rtk find <pattern>      rtk diff <file>

# Test (90-99% savings) — shows failures only
rtk pytest tests/       rtk cargo test          rtk test <cmd>

# Build & Lint (80-90% savings) — shows errors only
rtk tsc                 rtk lint                rtk cargo build
rtk prettier --check    rtk mypy                rtk ruff check

# Analysis (70-90% savings)
rtk err <cmd>           rtk log <file>          rtk json <file>
rtk summary <cmd>       rtk deps                rtk env

# GitHub (26-87% savings)
rtk gh pr view <n>      rtk gh run list         rtk gh issue list

# Infrastructure (85% savings)
rtk docker ps           rtk kubectl get         rtk docker logs <c>

# Package managers (70-90% savings)
rtk pip list            rtk pnpm install        rtk npm run <script>
```

## Rules
- In command chains, prefix each segment: `rtk git add . && rtk git commit -m "msg"`
- For debugging, use raw command without rtk prefix
- `rtk proxy <cmd>` runs command without filtering but tracks usage
<!-- /headroom:rtk-instructions -->
