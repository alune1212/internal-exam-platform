# Handoff

## Current State

The project has a runnable first-phase business loop and completed frontend redesign. It has a backend, frontend, database migration, Docker Compose stack, and documentation set.

Implemented foundations:

- FastAPI app with `/api/health`.
- SQLAlchemy models for candidates, questions, options, exams, attempts, attempt question snapshots, answers, practice answers, and import batches.
- Alembic initial migration `202606110001_initial_schema.py`.
- Candidate-facing and admin-facing API routes.
- Scoring service with tested multiple-choice set comparison.
- Question Excel import persistence for valid questions, options, and import batches.
- Candidate Excel import persistence for valid candidates and import batches.
- Exam configuration create/update/list persistence and candidate-facing active exam listing.
- Exam start persistence with fixed 60-question paper generation, attempt creation, and question snapshots.
- Answer autosave persistence and submit scoring from persisted attempt snapshots.
- Attempt result pass status based on `question_rule.pass_score`.
- React/Vite frontend with Academic Editorial design tokens, UI primitives, candidate layout, and admin layout.
- Candidate pages for login, practice, exam list, exam start, exam taking, result, and ranking.
- Admin pages for login, dashboard, question list/import, exam list/edit, candidate import, and reports.
- Docker Compose stack for PostgreSQL, backend, frontend, and Nginx.
- Time-based auto-submit background check.
- Ranking and basic admin report SQL queries.

## Verified Commands

Verified on 2026-06-15:

```bash
cd backend && UV_CACHE_DIR=.uv-cache uv run pytest -q
cd frontend && npm test -- --run
cd frontend && npm run lint
cd frontend && npm run format:check
cd frontend && npm run build
docker compose up -d --build
curl http://localhost:8000/api/health
curl http://localhost:8080/api/health
```

Observed results:

- Backend tests: 50 passed, with Starlette/httpx deprecation warnings.
- Frontend tests: 138 passed.
- Frontend lint: 0 errors, with two existing Fast Refresh export warnings in `badge.tsx` and `button.tsx`.
- Frontend build: passed, with one Vite chunk size warning.
- Docker Compose: PostgreSQL healthy; backend, frontend, and Nginx running.
- `/api/health`: returned `{"success":true,"data":{"status":"ok","service":"internal-exam-platform"},"message":"ok"}` through backend and Nginx.

## Implemented Business Loop

- Question import validates Excel rows and persists valid questions, options, and an import batch with failure details.
- Candidate import validates Excel rows and persists valid candidates plus an import batch with failure details.
- Exam configuration create/update/list services persist to the `exam` table, and active listing returns only `active` exams.
- Exam start creates an in-progress attempt and stores question snapshots.
- Non-empty `question_rule` with `question_count` uses fixed-paper mode. The default rule is 60 questions, total score 100, pass score 60, and type counts `single: 15`, `multiple: 40`, `judge: 5`.
- Fixed-paper selection only uses active questions, covers `category_1`, question types, and available `category_1 + question_type` combinations, then stores `fixed_question_ids` on the exam for later candidates.
- Empty `question_rule = {}` remains compatible with the legacy all-active question behavior.
- Answer autosave writes to `exam_attempt_answer`; submit scoring updates persisted answers and attempt totals.
- The exam-taking page uses the final question primary action as “提交试卷”; earlier questions still show “下一题”.
- Time-based auto-submit runs as an asyncio background task, checking every 30 seconds.
- Ranking and reports (score, accuracy, wrong questions, absent candidates) use real SQL queries.
- Admin authentication is a simple configured username/password placeholder.
- No frontend auth/session guard exists yet.

## Known Gaps

- Question import failure report download is not implemented.
- Exam scope is not explicitly linked to imported candidate groups yet.
- Report export keeps the route/schema shape but does not generate a file yet.
- Admin authentication remains a simple configured username/password placeholder.
- No frontend auth/session guard exists yet.

## Recommended Next Work

1. Add question import failure report download.
2. Define how an exam is scoped to imported candidates.
3. Add frontend auth/session guard for candidate and admin pages.

## Phase 7 — States & Polish（完成日期 2026-06-14）

- **视觉系统**：前端已完成 Academic Editorial redesign。设计令牌、UI primitives、editorial components、candidate/admin layouts、P0/P1/P2 页面和报表容器均已接入。
- **空态 / 错态**：共享 `EmptyState` 支持 `tone="error"` 和主/次操作按钮；页面级空态、加载态和部分操作错误已统一到 shared primitives。
- **加载态**：新增 `ContentSkeleton`，基于 `Skeleton` shimmer 和 `role="status"` / `aria-busy`。
- **倒计时 pulse**：`Timer.tsx` 在剩余时间小于等于 5 分钟时使用 `text-error` + pulse，并保留 `aria-live="polite"`。
- **键盘快捷键**：考试作答页支持 `←/→` 切题、`1-9` 与 `A-D` 选择当前题选项；input / textarea / contenteditable 聚焦时不拦截快捷键。最后一道题的主按钮显示“提交试卷”并走现有手动交卷流程。
- **可访问性**：移动端题号导航使用 Radix Sheet；选项卡暴露 radio / checkbox 语义；图标按钮均保留可访问名称。
- **当前验证口径**：`npm test`、`npx tsc --noEmit`、`npm run lint`、`npm run format:check`、`npm run build` 均需通过。`npm run lint` 当前为 0 errors，仍有 `badge.tsx` / `button.tsx` 两个 Fast Refresh export warnings。

## Docker Rebuild — 2026-06-15

- `docker compose up -d --build` 已完成，backend 与 frontend 容器已重新创建。
- `http://localhost:8000/api/health` 与 `http://localhost:8080/api/health` 均返回 `{"success":true,"data":{"status":"ok","service":"internal-exam-platform"},"message":"ok"}`。
- Docker build 期间 frontend build 仍有 Vite chunk size warning；这不是当前功能阻断项。
