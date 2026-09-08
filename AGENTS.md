# AGENTS.md

This project is a lightweight internal exam and practice platform. Keep changes simple, local, and aligned with the deployed lightweight internal-tool scope.

## Project Shape

- Backend: `backend/`, FastAPI, Pydantic, SQLAlchemy 2.0, Alembic, PostgreSQL, openpyxl.
- Frontend: `frontend/`, React, TypeScript, Vite, Tailwind CSS, shadcn-compatible local components, React Router, TanStack Query/Table, React Hook Form, Zod.
- Deployment: `docker-compose.yml` launches PostgreSQL, backend, frontend, and Nginx. Public API paths stay under `/api`.
- Runtime: the current internal Mac deployment is live. Read `docs/minimal-macos-deployment.md` before production operations; read `docs/handoff.md` for version and acceptance evidence.
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

Docker development commands and port mappings are in `README.md`. Current
production commands are only in `docs/minimal-macos-deployment.md`; keep that
runbook as the single operational source instead of duplicating commands here.

## Current Stage

Formally live on the office LAN since 2026-09-08. Deployment and acceptance
status belong in `docs/handoff.md`, not in repeated chronological appendices.

- Email OTP authenticates accounts. New accounts complete a display name; formal exam access additionally requires a frozen per-exam roster scope.
- Admin and candidate APIs retain `X-Admin-Token` and `X-Candidate-Token` authentication. Release-package signing is separate from mandatory login-token signing.
- Imports accept standardized question and per-exam roster Excel files; account identity is email-based, and roster display fields are frozen per exam.
- Snapshot scoring, autosave/resume, device takeover, timed submission, retake grants, and result-detail release are implemented. Use the current main OpenSpec specs for their contracts.
- Signed release packages, paired backups, second copies, restore drills, and cross-host migration are not enabled in the selected deployment. Their existing tools and historical specifications do not make them current startup requirements.

## Documentation maintenance

- `README.md` is the entry point; the runbook owns operations, `docs/handoff.md` owns current status, and requirements/API/database/import documents own their respective contracts.
- Update the owning document and its links when behavior changes. Preserve archived OpenSpec facts; consult `openspec/README.md` for historical scope.
- Remove superseded duplicate prose after migrating useful content. Never turn a historical or unexecuted check into a passed acceptance item.
