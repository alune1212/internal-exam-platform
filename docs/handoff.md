# Handoff

## Current State

The project has a runnable first-phase business loop, completed frontend redesign, and an implemented internal-deployment hardening layer. It has a backend, frontend, database migration, Docker Compose stack, operational backup tooling, and a Mac-first formal-host documentation set. The current formal target is Apple Silicon macOS + Docker Desktop; Windows Docker Desktop + WSL2 remains a future migration target.

Implemented foundations:

- FastAPI app with shallow `/api/health` liveness and dependency-aware `/api/ready` checks for PostgreSQL and learning media access.
- SQLAlchemy models for candidates, candidate login challenges, questions, options, exams, attempts, attempt question snapshots, answers, practice answers, and import batches.
- Alembic migrations through `202608070001_formal_writer_fence.py`, including compatibility backfill for existing result visibility/formal-attempt state and persistent cross-host writer-fence lineage.
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
- Signed four-hour admin sessions for named primary/backup operators, checked by `X-Admin-Token`; the equal-permission backup operator is disabled by default.
- Candidate login uses a two-step email OTP challenge before issuing signed candidate tokens; issued tokens are still checked by `X-Candidate-Token` for candidate-facing exam/practice APIs.
- Candidate frontend clears stale sessions on logout or 401 responses; `/exams` only queries `/api/exams/active` when a candidate session exists.
- Bounded Excel imports: default 5 MiB upload limit, 5000 data rows, and 1 worksheet.
- Excel export cells are escaped before writing failure reports and report workbooks.
- Runtime profiles support `development`, controlled-LAN HTTP `internal`, and HTTPS-only `production`; backend/worker roles validate only their required settings, and formal profiles reject sample database credentials.
- `internal` backend settings fail closed unless Nginx binds an explicit private LAN IP, CORS exactly matches that HTTP origin, secrets are non-default, and SMTP delivery is configured. `production` continues to require HTTPS origins.
- Docker Compose publishes only the candidate gateway on `${INTERNAL_LAN_BIND_IP}:8080`. The loopback operator gateway uses `127.0.0.1:8081`; PostgreSQL `5432` and direct frontend `5173` also stay on loopback. Candidate ingress denies admin, operations, readiness detail, docs, and OpenAPI routes. Worker containers do not receive admin, token-signing, or SMTP secrets.
- Public login rate limiting hashes unauthenticated identifiers before storing in memory, and login request fields have bounded lengths. Candidate OTP request and verification endpoints share this lightweight rate-limit boundary.
- Practice question and answer APIs require `X-Candidate-Token` and re-check that the token belongs to an active candidate.
- Save/submit paths reload in-progress attempts with database row locks before mutation.
- React/Vite frontend with Academic Editorial design tokens, UI primitives, candidate layout, and admin layout.
- Candidate login uses a clean email OTP auth canvas without candidate navigation or footer; authenticated candidate pages keep the shared top navigation without a global footer.
- Candidate page eyebrow copy is centralized in `frontend/src/lib/pageCopy.ts`; page/state labels use the shared product terminology, while numbered labels are reserved for real question positions.
- Admin pages for login, dashboard, question list/import, exam list/edit, candidate import, and reports.
- Digest-pinned, locally patched Docker Compose images for PostgreSQL, backend, frontend, and the shared candidate/operator Nginx gateway.
- Time-based auto-submit background check with an atomic heartbeat and container healthcheck; successful zero-result scans also refresh health, failed scans do not.
- Ranking, exam-filterable admin report SQL queries, and multi-sheet Excel report export.
- Learning media served through Nginx `/media/learning/` from the `learning_media` volume.
- Candidate OTP delivery supports mutually exclusive STARTTLS and implicit SSL transports, retries transient SMTP/network failures with short bounded backoff, stops on permanent failures, and logs challenge/attempt/error type without recipient or OTP data.
- Paired backup tooling creates a PostgreSQL custom dump and `learning_media` archive with manifest, SHA-256 checksums, and a last-written `SUCCESS`; restore verification only accepts disposable Compose project names and validates migration head, representative table counts, media count, and non-empty samples.
- Formal attempts use one active device credential, monotonic answer revisions, session-scoped offline drafts, fresh-OTP takeover, terminal voiding, one-time result-detail release, and audited preview-first bulk retakes without changing saved question/answer/score snapshots.
- Practice submissions are immutable and return immediate answer/analysis feedback; wrong-question review is candidate-scoped and derives mastery from the latest attempt.
- macOS operations include a protected host layout, ARM64 release bundle validation/build/install, isolated staging, promotion/status/start/stop, opportunistic and pre/post-exam paired backups, encrypted second-copy synchronization, restore drills, guarded rollback, and backup-operator control. The Mac adapter is intentionally thin; application operations remain in versioned containers.
- Windows PowerShell operations remain preserved as the future Docker Desktop + WSL2 migration adapter. They are not current Mac acceptance evidence.

## Final Stabilization Verification

Local engineering release gates (not designated-host acceptance) were rerun on 2026-08-07 against the Mac-first portability implementation and native `linux/arm64` final images:

- Backend format, Ruff, and `ty` passed. The local SQLite suite passed `493` tests with `10` PostgreSQL-only skips. A fresh disposable PostgreSQL 16 project upgraded every migration through `202608070001` and passed the complete `503`-test suite with no skips, including migration and advisory-lock concurrency coverage.
- Frontend format, `349` tests across `64` files, lint, production build, accessibility contracts, and offline-asset gate passed; the built runtime contained `0` public-Internet references.
- All three active OpenSpec changes passed strict validation. All `28` macOS zsh operations parsed and retained mode `0700`; both LaunchAgent templates passed `plutil`. Development and synthetic formal Compose renders passed. Formal exposure was candidate `192.168.2.34:8080`, operator `127.0.0.1:8081`, PostgreSQL and direct frontend loopback-only, with backend and worker unexposed.
- Playwright passed the minimum formal workflow through real Nginx/backend/PostgreSQL/fake-SMTP containers. The accepted 100-client capacity gate completed `100/100` submissions with `0` errors: start/save/submit p95 `617/572/524 ms`, database connection peak `17`, and worker heartbeat age `6.062 s` on `linux/arm64`.
- A fresh four-image `linux/arm64` security build passed the final policy evaluator with `0` blocking findings, `0` binding errors, and `0` security-evaluator errors. `pip-audit` found no known vulnerability. Trivy reported only four Medium and one Low backend finding below the release threshold. npm reported two High rows for one React Router advisory; the lock resolves the upstream patched `7.18.2`, the application has no unstable RSC API surface, and both rows are explicitly recorded as non-exploitable dispositions in `ops/security/dispositions.json`.
- The writer-fence and cutover implementation was adversarially reviewed for atomic state recovery, generation replay, source retirement, exact backup/release binding, backup/fence mutual exclusion, same-host rollback, and pre/post-write cross-host rollback. Backup write-freezes and formal writer fences now require explicit release; diagnostic TTL expiry never reopens writers.
- The current formal target remains the designated Apple Silicon Mac. Repository implementation and local engineering gates are complete, but real host configuration, LaunchAgent loading/retry evidence, independent encrypted second-device restore, real network negatives, formal staging/promotion, SMTP and desktop/phone UAT remain host-acceptance work. PowerShell parsing and Windows workflow checks remain future Windows static evidence; real Windows native AMD64 staging, cutover, and UAT are intentionally unclaimed.

## Historical Verified Commands

Internal deployment readiness gates verified on 2026-07-10:

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
openspec validate --all --strict
docker compose --env-file .env config --quiet
docker compose --env-file .env up -d --build
docker compose --env-file .env exec -T backend uv run --no-sync alembic upgrade head
docker compose --env-file .env exec -T nginx nginx -t
curl -f http://127.0.0.1:8080/api/health
curl -f http://127.0.0.1:8080/api/ready
curl -f http://127.0.0.1:8080/docs
```

Observed results:

- Backend format/lint/`ty`: passed; backend tests: 273 passed, 4 skipped.
- Frontend format/lint/build: passed; frontend tests: 59 files / 303 tests passed.
- OpenSpec strict validation: 8 passed, 0 failed. Development and synthetic internal Compose configurations rendered successfully with `config --quiet`.
- Compose images built and the db, backend, and auto-submit-worker services became healthy. Alembic was at head, `nginx -t` passed, `/api/health` and `/api/ready` returned HTTP 200, `/docs` loaded through `8080`, and a missing `/media/learning/` object returned 404 through the media route.
- Runtime evidence exposed and then fixed startup-time dependency synchronization: container commands now use `uv run --no-sync`; the rebuilt worker became healthy without downloading dev dependencies.
- On 2026-07-20, implicit SMTP SSL was verified through the rebuilt backend on the configured port: strict certificate validation, SMTP authentication, and a real test OTP message were accepted by the server.
- On 2026-07-20, `./scripts/test-backend-full.sh -q -rs` ran the complete backend suite against the disposable `internal_exam_test` PostgreSQL service: 280 passed, 0 skipped. The test container and temporary data were removed automatically after the run.
- A live paired backup was created at `backups/backup-20260710T032923Z`; the final implementation restored it into `internal-exam-restore-verify-20260710b`, verified database/media consistency including a real media-byte read, and cleaned up. The original stack was restarted and returned to healthy.

Operational commands and failure recovery are documented in `docs/internal-deployment-operations.md`. The essential maintenance-window flow is:

```bash
cd backend
uv run python -m app.ops.internal_backup backup --output-root ../backups --env-file ../.env
cd ..
docker compose --env-file .env stop
cd backend
uv run python -m app.ops.internal_backup verify ../backups/<backup-directory> \
  --env-file ../.env \
  --project-name internal-exam-restore-verify-<unique-suffix>
cd ..
docker compose --env-file .env up -d
```

Routine pre-exam acceptance should continue to follow `docs/official-exam-uat-checklist.md` through the deployed Nginx entry.

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

- Real Mac formal-host staging, promotion, host/Docker restart recovery, desktop/phone UAT, real SMTP, and second-copy restore have not yet been executed on the designated host. These are blocking operator acceptance steps, not completed evidence.
- Future Windows Docker Desktop + WSL2 native AMD64 staging, paired-backup restore, Windows service recovery, desktop/phone UAT, and formal promotion have not been executed. Mac evidence cannot satisfy those Windows gates.
- Controlled-LAN `internal` mode intentionally uses HTTP on the shared office LAN. Candidate bearer tokens, questions, answers, and released results are not transport-encrypted and can be intercepted or modified by a device with network visibility. This is the explicitly accepted first-phase exception in `security-http-exception.md`; it has no calendar expiry but must be reassessed on the documented scope, network, incident, or policy triggers.
- The platform is one best-effort 24x7 Mac host with Docker/LaunchAgent container recovery, not high availability. A serious host, disk, Docker Desktop, power, or office-network failure may require pausing or rescheduling an exam.
- The local 100-client gate passed on the final rerun but showed host-load variance in the immediately preceding run. Formal Mac staging must produce its own passing host-bound evidence; future Windows staging must rerun the gate and cannot reuse the Mac artifact.
- SMTP retry is deliberately short and in-process, not a durable queue. A backend restart can interrupt delivery; operators must retain resend and final-failure monitoring procedures.

## Recommended Next Work

1. On the designated Mac host, execute native ARM64 staging, Mac status/preflight checks, split-route checks, real SMTP fail-closed tests, service/Docker recovery, paired backup, independent encrypted second-copy restore, browser UAT, and the 100-client gate from `official-exam-uat-checklist.md`.
2. Create the formal pre-upgrade paired backup, promote only the tested commit-tagged ARM64 images, run desktop and phone UAT, then close sessions and retain the checksummed Mac evidence bundle. Do not call this Windows acceptance.
3. Keep HTTP `internal` exposure within the accepted office-LAN boundary. If a reassessment trigger occurs, stop expanding use and establish trusted HTTPS/network isolation before proceeding.
4. For a later Windows move, stop the Mac writer, create a final paired backup and writer-generation evidence, restore on native Windows AMD64 staging, and complete every Windows-specific gate before cutover.
