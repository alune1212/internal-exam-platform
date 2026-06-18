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
- Failure report Excel download for question, candidate, and exam-candidate import batches.
- Exam-scoped candidate list persistence via `exam_candidate_scope`, including import, removal, and retake grant endpoints.
- Exam configuration create/update/list persistence, available time windows, and candidate-facing active exam listing.
- Publish-time frozen question pool via `exam_question_pool`.
- Exam start persistence with fixed 50-question equivalent paper generation, attempt creation, and question snapshots.
- Answer autosave persistence and submit scoring from persisted attempt snapshots.
- Attempt result pass status based on `question_rule.pass_score`.
- Signed admin session tokens returned from login and checked by `X-Admin-Token`.
- Signed candidate tokens checked by `X-Candidate-Token` for candidate-facing exam/practice APIs.
- Bounded Excel imports: default 5 MiB upload limit, 5000 data rows, and 1 worksheet.
- Excel export cells are escaped before writing failure reports and report workbooks.
- Production settings reject default admin password, default token secret, and unsafe CORS origins.
- Save/submit paths reload in-progress attempts with database row locks before mutation.
- React/Vite frontend with Academic Editorial design tokens, UI primitives, candidate layout, and admin layout.
- Candidate pages for login, practice, exam list, exam start, exam taking, result, and ranking.
- Admin pages for login, dashboard, question list/import, exam list/edit, candidate import, and reports.
- Docker Compose stack for PostgreSQL, backend, frontend, and Nginx.
- Time-based auto-submit background check.
- Ranking, exam-filterable admin report SQL queries, and multi-sheet Excel report export.

## Verified Commands

Quality gates verified on 2026-06-18:

```bash
cd backend && uv run ruff format . --check
cd backend && uv run ruff check .
cd backend && uv run ty check
cd backend && uv run pytest
cd backend && uv run --with pip-audit pip-audit
cd frontend && npm run format:check
cd frontend && npm test -- --run
cd frontend && npm run lint
cd frontend && npm run build
cd frontend && npm audit --audit-level=high
docker-compose --env-file .env config
curl http://localhost:8000/api/health
curl http://localhost:8080/api/health
```

Observed results:

- Backend format/lint/type gates: passed.
- Backend tests: 161 passed.
- Backend dependency audit: `No known vulnerabilities found`.
- Frontend format/lint/build gates: passed.
- Frontend tests: 39 files / 190 tests passed. jsdom still logs the known `Not implemented: navigation to another Document` warning in the 401 redirect test.
- Frontend dependency audit: 0 vulnerabilities at `--audit-level=high`.
- Frontend lint: 0 errors and 0 warnings.
- Frontend build: passed, with Vite dynamic-import/chunk-size warnings.
- Docker Compose config passed; backend/db/frontend/nginx were Up with the database healthy during the gate.
- `http://localhost:8000/api/health` and `http://localhost:8080/api/health` returned ok.

## Implemented Business Loop

- Question import validates Excel rows and persists valid questions, options, and an import batch with failure details.
- Candidate import validates Excel rows and persists valid candidates plus an import batch with failure details.
- Import failure report download returns an Excel workbook with batch metadata and row-level failure details.
- Exam configuration create/update/list services persist to the `exam` table, and candidate-facing active listing requires `X-Candidate-Token` and returns only active exams in that candidate's `exam_candidate_scope`.
- `available_from` and `available_until` limit new exam starts. Existing in-progress attempts can be resumed after `available_until` and still submit based on `started_at + duration_minutes`.
- Publishing an exam from draft to active freezes the current active question bank into `exam_question_pool`; start exam samples from that frozen pool while keeping attempt question snapshots.
- Exam start creates an in-progress attempt and stores question snapshots.
- Non-empty `question_rule` with `question_count` uses fixed-paper mode. The admin editor default template is 50 questions, total score 100, pass score 60, and type counts `single: 30`, `multiple: 10`, `judge: 10`.
- Fixed-paper rules must explicitly provide positive integer `question_count`, positive integer `total_score`, and `type_counts` whose `single`/`multiple`/`judge` values are non-negative integers summing to `question_count`.
- Fixed-paper selection only uses active questions, avoids duplicate stems in the same paper, covers `category_1`, question types, and available `category_1 + question_type` combinations.
- Fixed-paper scores are integer and evenly distributed from `question_rule.total_score`; 50 questions with total score 100 gives every question 2 points.
- Empty `question_rule = {}` remains compatible with the legacy all-active question behavior.
- Exam candidate import adds rows to `exam_candidate_scope`; existing candidates are reused by employee number, or by name when no employee number exists.
- Answer autosave writes to `exam_attempt_answer`; submit scoring updates persisted answers and attempt totals.
- The exam-taking page uses the final question primary action as “提交试卷”; earlier questions still show “下一题”.
- Time-based auto-submit runs as an asyncio background task, checking every 30 seconds.
- Ranking and reports (score, accuracy, wrong questions, absent candidates) use real SQL queries.
- Score, accuracy, wrong-question, absent-candidate, and export reports support `exam_id` filtering. Global reports remain available as an optional view.
- Report export returns one Excel workbook with sheets for score report, question accuracy, wrong questions, and absent candidates.
- Admin authentication uses a configured username/password login plus signed session token; frontend stores the token and redirects on 401.
- Practice mode uses `X-Candidate-Token` for answer submission; practice question lists do not expose correct answers or analysis before submission.

## Known Gaps

- No blocking P0 gap is currently documented in code. Production readiness still requires a real human UAT pass through the Docker/Nginx `8080` entrypoint and production secrets/backup checks.
- Optional follow-ups: PostgreSQL lock-wait integration coverage for concurrent save/submit, worker or gateway CPU timeout around large openpyxl parsing, and frontend token storage review if the threat model expands beyond the first-phase internal tool.

## Recommended Next Work

1. Run `docs/official-exam-uat-checklist.md` as a human browser UAT against the Docker/Nginx `8080` entrypoint.
2. Before production use, set non-default `POSTGRES_PASSWORD`, `DATABASE_URL`, `ADMIN_PASSWORD`, and `TOKEN_SECRET`; configure `CORS_ORIGINS` with only production HTTPS origins, not `*`, localhost, 127.0.0.1, or 0.0.0.0; then back up the database before running migrations.
3. Keep auth lightweight unless the product scope expands beyond the first-phase internal tool.

## Phase 7 — States & Polish（完成日期 2026-06-14）

- **视觉系统**：前端已完成 Academic Editorial redesign。设计令牌、UI primitives、editorial components、candidate/admin layouts、P0/P1/P2 页面和报表容器均已接入。
- **空态 / 错态**：共享 `EmptyState` 支持 `tone="error"` 和主/次操作按钮；页面级空态、加载态和部分操作错误已统一到 shared primitives。
- **加载态**：新增 `ContentSkeleton`，基于 `Skeleton` shimmer 和 `role="status"` / `aria-busy`。
- **倒计时 pulse**：`Timer.tsx` 在剩余时间小于等于 5 分钟时使用 `text-error` + pulse，并保留 `aria-live="polite"`。
- **键盘快捷键**：考试作答页支持 `←/→` 切题、`1-9` 与 `A-D` 选择当前题选项；input / textarea / contenteditable 聚焦时不拦截快捷键。最后一道题的主按钮显示“提交试卷”并走现有手动交卷流程。
- **可访问性**：移动端题号导航使用 Radix Sheet；选项卡暴露 radio / checkbox 语义；图标按钮均保留可访问名称。
- **当前验证口径**：`npm test`、`npx tsc --noEmit`、`npm run lint`、`npm run format:check`、`npm run build` 均需通过。2026-06-16 前端打磨验证中，`npm run lint` 为 0 errors / 0 warnings。

## Frontend Polish Audit — 2026-06-16

- 管理登录页浅底 `Wordmark` 改回默认浅背景配色，避免白色品牌字在白底上失去对比。
- 管理仪表盘活动列表将 ISO 时间显示为 `MM/DD HH:mm`，同时保留 `<time datetime>` 语义。
- `data-stagger` 入场动画收敛为 280ms、40ms delay step，并从 72% opacity 开始，避免移动端截图/首帧显得页面未加载完成。
- 浏览器验证覆盖 `/admin/login`、`/admin/dashboard`、`/exams` 桌面视口，以及 `/exams` 移动视口菜单交互。

## Docker Rebuild — 2026-06-15

- `docker compose up -d --build` 已完成，backend 与 frontend 容器已重新创建。
- `http://localhost:8000/api/health` 与 `http://localhost:8080/api/health` 均返回 `{"success":true,"data":{"status":"ok","service":"internal-exam-platform"},"message":"ok"}`。
- Docker build 期间 frontend build 仍有 Vite chunk size warning；这不是当前功能阻断项。
- Compose no longer embeds default database/admin credentials; copy `.env.example` to `.env`, replace secrets, and use `docker compose --env-file .env config` for config validation.
