# Handoff

## Current State

The project has a runnable first-phase business loop and completed frontend redesign. It has a backend, frontend, database migration, Docker Compose stack, and documentation set.

Implemented foundations:

- FastAPI app with `/api/health`.
- SQLAlchemy models for candidates, candidate login challenges, questions, options, exams, attempts, attempt question snapshots, answers, practice answers, and import batches.
- Alembic initial migration `202606110001_initial_schema.py`.
- Candidate-facing and admin-facing API routes.
- Scoring service with tested multiple-choice set comparison.
- Question Excel import persistence for valid questions, options, and import batches.
- Candidate Excel import persistence for valid candidates and import batches.
- Failure report Excel download for question, candidate, and exam-candidate import batches.
- Independent video learning module with local admin upload, draft/published/archived video status, candidate playback, 90% completion tracking, and learning report export.
- Exam-scoped candidate list persistence via `exam_candidate_scope`, including import, listing, removal, and retake grant endpoints.
- Exam configuration create/update/list persistence, available time windows, and candidate-facing active exam listing.
- Publish-time frozen question pool via `exam_question_pool`.
- Exam start persistence with fixed 50-question equivalent paper generation, attempt creation, and question snapshots.
- Answer autosave persistence and hand-in scoring from persisted attempt snapshots.
- Attempt result pass status based on `question_rule.pass_score`.
- Signed admin session tokens returned from login and checked by `X-Admin-Token`.
- Candidate login uses a two-step email OTP challenge before issuing signed candidate tokens; issued tokens are still checked by `X-Candidate-Token` for candidate-facing exam/practice APIs.
- Candidate frontend clears stale sessions on logout or 401 responses; `/exams` only queries `/api/exams/active` when a candidate session exists.
- Bounded Excel imports: default 5 MiB upload limit, 5000 data rows, and 1 worksheet.
- Excel export cells are escaped before writing failure reports and report workbooks.
- Production settings reject default admin password, default token secret, and unsafe CORS origins.
- Docker Compose publishes Nginx on `0.0.0.0:8080` so the browser entry can be used from the same LAN; PostgreSQL `5432` and the direct frontend `5173` stay bound to `127.0.0.1`.
- Public login rate limiting hashes unauthenticated identifiers before storing in memory, and login request fields have bounded lengths. Candidate OTP request and verification endpoints share this lightweight rate-limit boundary.
- Practice question and answer APIs require `X-Candidate-Token` and re-check that the token belongs to an active candidate.
- Save/submit paths reload in-progress attempts with database row locks before mutation.
- React/Vite frontend with Academic Editorial design tokens, UI primitives, candidate layout, and admin layout.
- Candidate login uses a clean email OTP auth canvas without candidate navigation or footer; authenticated candidate pages keep the shared top navigation without a global footer.
- Candidate page eyebrow copy is centralized in `frontend/src/lib/pageCopy.ts`; page/state labels use the shared product terminology, while numbered labels are reserved for real question positions.
- Admin pages for login, dashboard, question list/import, exam list/edit, candidate import, and reports.
- Docker Compose stack for PostgreSQL, backend, frontend, and Nginx.
- Time-based auto-submit background check.
- Ranking, exam-filterable admin report SQL queries, and multi-sheet Excel report export.
- Learning media served through Nginx `/media/learning/` from the `learning_media` volume.

## Verified Commands

Video learning gates verified on 2026-07-02:

```bash
cd backend
UV_CACHE_DIR=/private/tmp/uv-cache-internal-exam uv run ruff format . --check
UV_CACHE_DIR=/private/tmp/uv-cache-internal-exam uv run ruff check .
UV_CACHE_DIR=/private/tmp/uv-cache-internal-exam uv run ty check
UV_CACHE_DIR=/private/tmp/uv-cache-internal-exam uv run pytest
cd ../frontend
npm run format:check
npm test -- --run
npm run lint
npm run build
cd ..
docker compose --env-file .env config
docker compose --env-file .env up -d --build
docker compose --env-file .env exec -T backend uv run alembic upgrade head
docker compose --env-file .env exec -T nginx nginx -t
curl -f http://127.0.0.1:8080/api/health
curl -f http://127.0.0.1:8080/docs
```

Observed results:

- Backend ruff format/lint and `ty check`: passed.
- Backend tests: 196 passed, 4 skipped.
- Frontend format/lint/build gates: passed.
- Frontend tests: 59 files / 300 tests passed.
- Docker Compose config and build passed; db, backend, auto-submit-worker, frontend, and nginx stayed Up.
- Container Alembic upgrade used `PostgresqlImpl` and reached head; startup logs ran `202606250001 -> 202607020001, video_learning`.
- `nginx -t` passed.
- `http://127.0.0.1:8080/api/health` returned ok; `http://127.0.0.1:8080/docs` returned the Swagger UI HTML.
- Browser smoke through `8080` covered candidate `/learning` and `/learning/1`, plus admin `/admin/learning` and `/admin/learning/reports`, using local smoke data. The candidate detail rendered one `<video>` element and no console warning/error was observed.

Quality gates verified on 2026-07-02 after the Build Web Apps frontend audit:

```bash
cd frontend
npm run format:check
npm test -- --run
npm run lint
npm run build
cd ../backend
UV_CACHE_DIR=/private/tmp/uv-cache-internal-exam uv run pytest
cd ..
docker compose --env-file .env config
docker compose --env-file .env up -d --build
docker compose exec -T backend uv run alembic upgrade head
docker compose exec -T nginx nginx -t
curl -f http://127.0.0.1:8080/api/health
curl -f http://127.0.0.1:8080/docs
```

Observed results:

- Backend tests: 186 passed, 4 skipped.
- Frontend format/lint/build gates: passed.
- Frontend tests: 56 files / 284 tests passed.
- Frontend lint: 0 errors and 0 warnings.
- Frontend build: passed.
- Docker Compose config and build passed; db, backend, auto-submit-worker, frontend, and nginx stayed Up.
- Container Alembic upgrade reached head; `nginx -t` passed.
- `http://127.0.0.1:8080/api/health` returned ok; `http://127.0.0.1:8080/docs` returned the Swagger UI HTML.
- Browser audit through `8080` covered desktop and mobile candidate/admin surfaces: candidate login, no-session `/exams` redirect to login, active exam list, exam start, exam taking, answer selection, submit/result, result wrong-only filter, admin login/dashboard, exam list/edit/candidates, question list/import, report pages, absent status filters, and mobile admin menu. No console warning/error, framework overlay, blank page, or horizontal overflow was observed.

Earlier full quality gates verified on 2026-06-29:

- Backend format/lint/type gates: passed.
- Backend tests: 186 passed, 4 skipped.
- Frontend format/lint/build gates: passed.
- Frontend tests: 55 files / 257 tests passed.
- Frontend lint: 0 errors and 0 warnings.
- Frontend build: passed.
- Docker Compose config and build passed; db, backend, auto-submit-worker, frontend, and nginx stayed Up.
- Container Alembic upgrade reached head; `nginx -t` passed.
- `http://localhost:8080/api/health` returned ok; `http://localhost:8080/docs` returned the Swagger UI HTML.
- Browser smoke through `8080` rendered `/exams` without a session as the candidate login page, rendered `/admin/login`, and produced no console warning/error. Nginx logs showed no anonymous `/api/exams/active` request for the no-session `/exams` load.

Security remediation gates verified on 2026-07-01:

```bash
cd backend
UV_CACHE_DIR=/private/tmp/uv-cache-internal-exam uv run pytest
UV_CACHE_DIR=/private/tmp/uv-cache-internal-exam uv run ruff check .
UV_CACHE_DIR=/private/tmp/uv-cache-internal-exam uv run ruff format . --check
UV_CACHE_DIR=/private/tmp/uv-cache-internal-exam uv run ty check
cd ..
docker-compose --env-file .env.example config
```

Observed results:

- Backend tests: 186 passed, 4 skipped.
- Backend ruff format/lint and `ty check`: passed.
- Docker Compose config passed; PostgreSQL, frontend, and Nginx published ports resolved to `host_ip: 127.0.0.1`.

## 8080 Business UAT Evidence

Scripted business UAT verified on 2026-06-29 using only `http://localhost:8080`:

- UAT prefix: `UAT-20260629110754-77f1db`.
- Temporary local artifacts: `/private/tmp/internal-exam-uat/UAT-20260629110754-77f1db-questions.xlsx`, `/private/tmp/internal-exam-uat/UAT-20260629110754-77f1db-candidates.xlsx`, and `/private/tmp/internal-exam-uat/UAT-20260629110754-77f1db-report.xlsx`.
- Covered admin login, question import with a failure row, candidate import with a failure row, exam create/update/publish, candidate login, active exam listing, start, answer save, resume, hand-in, result, retake grant, retake start, score/accuracy/wrong/absent reports, report export, and template downloads.
- Question import batch `20`: `success_count=4`, `failed_count=1`; failed row `6`, reason `正确答案必须存在于选项中`.
- Candidate import batch `21`: `success_count=2`, `failed_count=1`; failed row `4`, reason `姓名不能为空`.
- Created `exam_id=1`, `primary_candidate_id=1`, `attempt_id=1`, and `retake_attempt_id=2`.
- Report query sizes: scores `1`, accuracy `4`, wrong questions `1`, absent candidates `1`.
- Template download smoke: question template sheet `题库导入模板`, candidate template sheet `应考名单导入模板`.
- Backend and nginx logs for the UAT requests were HTTP 200, and Compose services remained Up after the run.

## Implemented Business Loop

- Question import validates Excel rows and persists valid questions, options, and an import batch with failure details.
- Candidate import validates Excel rows and persists valid candidates plus an import batch with failure details.
- Candidate and exam-candidate imports require usable email data for strict email OTP login; existing candidates without email can be backfilled from an exam-candidate import row, while conflicting email values fail that row.
- Import failure report download returns an Excel workbook with batch metadata and row-level failure details.
- Exam configuration create/update/list services persist to the `exam` table, and candidate-facing active listing requires `X-Candidate-Token` and returns only active exams in that candidate's `exam_candidate_scope`.
- `available_from` and `available_until` limit new exam starts. Existing in-progress attempts can be resumed after `available_until` and still hand in based on `started_at + duration_minutes`.
- Publishing an exam from draft to active freezes the current active question bank into `exam_question_pool`; start exam samples from that frozen pool while keeping attempt question snapshots.
- Exam start creates an in-progress attempt and stores question snapshots.
- Non-empty `question_rule` with `question_count` uses fixed-paper mode. The admin editor default template is 50 questions, total score 100, pass score 60, and type counts `single: 30`, `multiple: 10`, `judge: 10`.
- Fixed-paper rules must explicitly provide positive integer `question_count`, positive integer `total_score`, and `type_counts` whose `single`/`multiple`/`judge` values are non-negative integers summing to `question_count`.
- Fixed-paper selection only uses active questions, avoids duplicate stems in the same paper, covers `category_1`, question types, and available `category_1 + question_type` combinations.
- Fixed-paper scores are integer and evenly distributed from `question_rule.total_score`; 50 questions with total score 100 gives every question 2 points.
- Empty `question_rule = {}` remains compatible with the legacy all-active question behavior.
- Exam candidate import adds rows to `exam_candidate_scope`; existing candidates are reused by employee number, or by name when no employee number exists.
- Exam candidate management can list scoped candidates, remove a candidate from one exam scope, and grant one retake. An unused retake grant allows a submitted candidate to start a new `retake` attempt, which consumes the grant.
- Answer autosave writes to `exam_attempt_answer`; hand-in scoring updates persisted answers and attempt totals.
- The exam-taking page uses the final question primary action as “交卷”; earlier questions still show “下一题”.
- Time-based auto-submit runs as an asyncio background task, checking every 30 seconds.
- Ranking and reports (score, accuracy, wrong questions, absent candidates) use real SQL queries.
- Score, accuracy, wrong-question, absent-candidate, and export reports support `exam_id` filtering. Global reports remain available as an optional view.
- Report export returns one Excel workbook with sheets for `个人成绩`, `题目正确率`, `错题排行`, and `参考状态`.
- Admin authentication uses a configured username/password login plus signed session token; frontend stores the token and redirects on 401.
- Candidate authentication requires `name` + `email` + optional `employee_no` to request an email OTP; `/api/candidates/login/verify` consumes a valid challenge before returning the signed candidate token. Candidate frontend clears stale local session state on logout or 401, and no-session candidate pages return to `/login` without calling candidate-scoped APIs.
- Candidate login challenge request returns a uniform 200 envelope regardless of the lookup outcome (unknown / ambiguous / inactive / missing-email / valid). Unknown-identity requests persist a `CandidateLoginChallenge` against a designated sentinel candidate (see `database-design.md` §sentinel) and skip the email send, so the response, status code, and row count cannot be used to enumerate the roster. The route commits the challenge row before scheduling email delivery through FastAPI `BackgroundTasks`; SMTP failures are logged at WARN with `event=candidate_login.email_delivery_failed` and do not roll back the persisted state or surface a 5xx. Unknown-identity attempts additionally emit a rate-limited structured WARN `event=candidate_login.unknown_identity` for operator audit. The verify step rejects sentinel / consumed / expired / attempt-exhausted challenges with 404.
- Practice mode uses `X-Candidate-Token` for question listing and answer submission, re-checks active candidate status, and does not expose correct answers or analysis before submission.
- Video learning uses `X-Candidate-Token` for published video listing, detail, and progress heartbeat. Watched intervals are merged server-side so repeated playback and seek jumps do not inflate completion.
- Video learning completion is independent from exam eligibility, exam start/submit, scoring, ranking, and practice behavior. The current completion threshold is 90%.
- Admin learning pages support local `mp4` / `webm` upload, client-side duration extraction, publish/archive actions, title/description edits, video/status-filtered learning report, and Excel export.

## Known Gaps

- No blocking P0 gap is currently documented in code. A scripted Docker/Nginx `8080` business UAT passed on 2026-06-29; production rollout should still run a short human browser walkthrough with real exam data and operators.
- Production readiness still requires non-default production secrets, production HTTPS CORS, configured SMTP sender/host for candidate login OTP delivery, and a database backup before migration.
- Production backup must include both PostgreSQL and the `learning_media` volume/local media directory; otherwise learning video metadata may restore without playable files.
- Optional follow-ups: PostgreSQL lock-wait integration coverage for concurrent save/submit, worker or gateway CPU timeout around large openpyxl parsing, enterprise SSO/passkey evaluation, and frontend token storage review if the threat model expands beyond the first-phase internal tool.

## Recommended Next Work

1. Run a short human browser walkthrough against the Docker/Nginx `8080` entrypoint with production-like exam data, using `docs/official-exam-uat-checklist.md` as the checklist.
2. Before production use, set non-default `POSTGRES_PASSWORD`, `DATABASE_URL`, `ADMIN_PASSWORD`, and `TOKEN_SECRET`; configure `CORS_ORIGINS` with only production HTTPS origins, not `*`, localhost, 127.0.0.1, or 0.0.0.0; configure `CANDIDATE_LOGIN_EMAIL_DELIVERY_MODE=smtp`, `CANDIDATE_LOGIN_EMAIL_FROM`, and `CANDIDATE_LOGIN_SMTP_HOST`; then back up the database before running migrations.
3. Keep auth lightweight unless the product scope expands beyond the first-phase internal tool; if the identity risk increases, evaluate enterprise SSO/MFA separately instead of expanding this email OTP flow into a full account system.
