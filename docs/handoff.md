# Handoff

## Current State

The project has a runnable first-phase business loop, completed frontend redesign, and an implemented internal-deployment hardening layer. It has a backend, frontend, database migration, Docker Compose stack, operational backup tooling, and a Mac-first formal-host documentation set. The current formal target is Apple Silicon macOS + Docker Desktop; Windows Docker Desktop + WSL2 remains a future migration target.

Implemented foundations:

- FastAPI app with shallow `/api/health` liveness and dependency-aware `/api/ready` checks for PostgreSQL and learning media access.
- SQLAlchemy compatibility account rows, email-bound login challenges, frozen exam scopes, questions, options, exams, attempts, attempt question snapshots, answers, practice answers, and import batches.
- Alembic migrations through `202608300001_practice_answer_aggregate.py`, including the compatibility backfill/writer-fence lineage, email-account and frozen-roster migration, and additive practice aggregate. The destructive legacy-field step remains gated by the account-migration preflight and restore-only rollback contract below.
- Candidate-facing and admin-facing API routes.
- Scoring service with tested multiple-choice set comparison.
- Question Excel import persistence for valid questions, options, and import batches.
- Single-exam roster Excel import persistence for normalized-email rows and import batches; standalone global account/person import is removed.
- Failure report Excel download for question and exam-roster import batches.
- Independent video learning module with local admin upload, draft/published/archived video status, active-user playback, 90% completion tracking, and learning report export.
- Exam-scoped roster persistence via `exam_candidate_scope`, including frozen identity, publication freeze, invitation outcomes, listing, removal of draft rows, and retake grant endpoints.
- Exam configuration create/update/list persistence, available time windows, and candidate-facing active exam listing.
- Publish-time frozen question pool via `exam_question_pool`.
- Exam start persistence with fixed 50-question equivalent paper generation, attempt creation, and question snapshots.
- Answer autosave persistence and hand-in scoring from persisted attempt snapshots.
- Attempt result pass status based on `question_rule.pass_score`.
- Signed four-hour admin sessions for named primary/backup operators, checked by `X-Admin-Token`; the equal-permission backup operator is disabled by default.
- Unified email-only OTP login uses six digits, ten-minute expiry, single use, five attempts, 60-second resend cooldown, and persisted per-email/source/global limits. Existing active accounts receive signed candidate tokens; new/pending accounts must complete display name first; inactive accounts cannot self-register a replacement.
- Candidate frontend clears stale sessions on logout or 401 responses; `/exams` only queries `/api/exams/active` when a candidate session exists.
- Bounded Excel imports: default 5 MiB upload limit, 5000 data rows, and 1 worksheet.
- Excel export cells are escaped before writing failure reports and report workbooks.
- Runtime profiles support `development`, controlled-LAN HTTP `internal`, and HTTPS-only `production`; backend/worker roles validate only their required settings, and formal profiles reject sample database credentials.
- `internal` backend settings fail closed unless Nginx binds an explicit private LAN IP, CORS exactly matches that HTTP origin, secrets are non-default, and SMTP delivery is configured. `production` continues to require HTTPS origins.
- Docker Compose publishes only the candidate gateway on `${INTERNAL_LAN_BIND_IP}:8080`. The loopback operator gateway uses `127.0.0.1:8081`; PostgreSQL `5432` and direct frontend `5173` also stay on loopback. Candidate ingress denies admin, operations, readiness detail, docs, and OpenAPI routes. Worker containers do not receive admin, token-signing, or SMTP secrets.
- Public login rate limiting hashes unauthenticated identifiers before storing in memory, and login request fields have bounded lengths. Candidate OTP request and verification endpoints share this lightweight rate-limit boundary.
- Practice question and answer APIs require `X-Candidate-Token` and re-check that the token belongs to an active account.
- Save/submit paths reload in-progress attempts with database row locks before mutation.
- React/Vite frontend with Academic Editorial design tokens, UI primitives, candidate layout, and admin layout.
- Candidate login uses a clean email OTP auth canvas without candidate navigation or footer; authenticated candidate pages keep the shared top navigation without a global footer.
- Candidate page eyebrow copy is centralized in `frontend/src/lib/pageCopy.ts`; page/state labels use the shared product terminology, while numbered labels are reserved for real question positions.
- Admin pages for login, dashboard, question list/import, exam list/edit, account directory, exam-roster import/invitation controls, and reports.
- Digest-pinned, locally patched Docker Compose images for PostgreSQL, backend, frontend, and the shared candidate/operator Nginx gateway.
- Time-based auto-submit background check with an atomic heartbeat and container healthcheck; successful zero-result scans also refresh health, failed scans do not.
- Ranking, exam-filterable admin report SQL queries, and multi-sheet Excel report export.
- Learning media is served by the backend through short-lived candidate/video-bound playback credentials; both gateways deny the legacy `/media/learning/` path.
- Candidate OTP delivery supports mutually exclusive STARTTLS and implicit SSL transports, retries transient SMTP/network failures with short bounded backoff, stops on permanent failures, and logs challenge/attempt/error type without recipient or OTP data.
- Paired backup tooling creates a PostgreSQL custom dump and `learning_media` archive with manifest, SHA-256 checksums, and a last-written `SUCCESS`; restore verification only accepts disposable Compose project names and validates migration head, representative table counts, media count, and non-empty samples.
- Formal attempts use one active device credential, monotonic answer revisions, session-scoped offline drafts, fresh-OTP takeover, terminal voiding, one-time result-detail release, and audited preview-first bulk retakes without changing saved question/answer/score snapshots.
- Practice submissions are immutable and return immediate answer/analysis feedback; wrong-question review is account-scoped and derives mastery from the latest attempt.
- The admin exam workspace is available at `GET /api/admin/exams/{exam_id}/workspace`; it returns one `observed_at`, exam/readiness, roster/invitation/attendance/attempt/incident aggregates, and a server-derived advisory next action without roster identity fields.
- Candidate credentials and answer drafts remain tab-scoped in `sessionStorage`: a reload in the same tab can recover them and resume revisioned synchronization, while a closed tab/window, another tab/device, or a host cutover is outside the recovery guarantee and requires OTP login or takeover.
- `chromium-mobile` is a controlled Playwright project for the formal exam action area (save, navigator sheet, submit reachability, and overflow); it is disposable engineering evidence only and does not replace real Safari/phone UAT or Mac/Windows host acceptance.
- macOS operations include a protected host layout, ARM64 release bundle validation/build/install, isolated staging, promotion/status/start/stop, opportunistic and pre/post-exam paired backups, encrypted second-copy synchronization, restore drills, guarded rollback, and backup-operator control. The Mac adapter is intentionally thin; application operations remain in versioned containers.
- Windows PowerShell operations remain preserved as the future Docker Desktop + WSL2 migration adapter. They are not current Mac acceptance evidence.

## Reliable Exam Experience Verification (2026-08-14)

The OpenSpec change `improve-reliable-exam-experience` completed its local engineering gates. These results verify the repository implementation; they do not replace designated-host commissioning or formal Mac/Windows acceptance:

- Backend format, Ruff, and `ty` passed. The ordinary local suite passed `611` tests with `13` expected PostgreSQL-only skips. The disposable PostgreSQL 16 full gate passed all `624` tests with no skips, including start-versus-archive ordering, writer-fence resume, existing start/save/submit/takeover races, and migration coverage.
- Frontend format and lint passed. The deterministic Vitest suite passed `387` tests across `73` files in two consecutive runs. Production build and offline-asset validation passed with `0` external runtime references.
- The disposable Compose browser gate passed `7/7` Playwright journeys through Nginx, backend, PostgreSQL, and fake SMTP: admin workspace publish/invitation guidance, candidate login/start/autosave/same-tab resume/submit/result, revision-conflict recovery, and controlled mobile Chromium action-area/focus coverage.
- OpenSpec strict validation, Compose configuration rendering, and `git diff --check` passed. This change adds no migration, service, dependency, Redis/Celery queue, LMS expansion, or anti-cheat subsystem.
- Candidate recovery remains deliberately tab-scoped. Closing the tab/window, moving to another device, or host cutover still requires OTP login or takeover; the browser gate is engineering evidence only.
- Real LaunchAgent loading/retry, approved LAN reservation and negative exposure checks, formal SMTP, independent encrypted second-copy restore, designated-host staging/promotion, and real macOS Chrome/Safari plus Android/iOS UAT remain external formal-host work. Windows native AMD64 staging/cutover/UAT remains a separate future target.

## Final Stabilization Verification

Local engineering release gates (not designated-host acceptance) were rerun on 2026-08-07 against the Mac-first portability implementation and native `linux/arm64` final images:

- Backend format, Ruff, and `ty` passed. The local SQLite suite passed `493` tests with `10` PostgreSQL-only skips. A fresh disposable PostgreSQL 16 project upgraded every migration through `202608070001` and passed the complete `503`-test suite with no skips, including migration and advisory-lock concurrency coverage.
- Frontend format, `349` tests across `64` files, lint, production build, accessibility contracts, and offline-asset gate passed; the built runtime contained `0` public-Internet references.
- All three active OpenSpec changes passed strict validation. All `28` macOS zsh operations parsed and retained mode `0700`; both LaunchAgent templates passed `plutil`. Development and synthetic formal Compose renders passed. Historical synthetic render evidence used candidate `192.168.2.34:8080` and operator `127.0.0.1:8081`; this address is not normative formal configuration, which uses `<FORMAL_LAN_IP>`. PostgreSQL and direct frontend remained loopback-only, with backend and worker unexposed.
- Playwright passed the minimum formal workflow through real Nginx/backend/PostgreSQL/fake-SMTP containers. The accepted 100-client capacity gate completed `100/100` submissions with `0` errors: start/save/submit p95 `617/572/524 ms`, database connection peak `17`, and worker heartbeat age `6.062 s` on `linux/arm64`.
- A fresh four-image `linux/arm64` security build passed the final policy evaluator with `0` blocking findings, `0` binding errors, and `0` security-evaluator errors. `pip-audit` found no known vulnerability. Trivy reported only four Medium and one Low backend finding below the release threshold. npm reported two High rows for one React Router advisory; the lock resolves the upstream patched `7.18.2`, the application has no unstable RSC API surface, and both rows are explicitly recorded as non-exploitable dispositions in `ops/security/dispositions.json`.
- The writer-fence and cutover implementation was adversarially reviewed for atomic state recovery, generation replay, source retirement, exact backup/release binding, backup/fence mutual exclusion, same-host rollback, and pre/post-write cross-host rollback. Backup write-freezes and formal writer fences now require explicit release; diagnostic TTL expiry never reopens writers.
- The current formal target remains the designated Apple Silicon Mac. Repository implementation and local engineering gates are complete, but real host configuration, LaunchAgent loading/retry evidence, independent encrypted second-device restore, real network negatives, formal staging/promotion, SMTP and desktop/phone UAT remain host-acceptance work. PowerShell parsing and Windows workflow checks remain future Windows static evidence; real Windows native AMD64 staging, cutover, and UAT are intentionally unclaimed.
- Email-first account/invitation work must retain its own migration gate: destructive legacy-column removal is blocked until read-only conflict preflight, verified paired backup/second copy, isolated restore, writer fence and no-in-progress-attempt evidence exist. Local code/tests or this handoff do not count as real SMTP invitation/OTP UAT.

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

Operational commands and failure recovery are documented in `docs/internal-deployment-operations.md`. Paired backup creation must use the guarded `container-backup` entry point through the formal host adapter; the unguarded legacy creation entry point is no longer available. The essential maintenance-window flow is:

```bash
zsh ops/macos/Invoke-PairedBackup.zsh \
  --kind pre-upgrade \
  --root "$HOME/Library/Application Support/InternalExam"
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
- Temporary local artifacts: `/private/tmp/internal-exam-uat/UAT-20260629110754-77f1db-questions.xlsx`, `/private/tmp/internal-exam-uat/UAT-20260629110754-77f1db-roster.xlsx`, and `/private/tmp/internal-exam-uat/UAT-20260629110754-77f1db-report.xlsx`.
- Covered admin login, question import with a failure row, single-exam roster import with a failure row, exam create/update/publish, OTP login, active scoped-exam listing, start, answer save, resume, hand-in, result, retake grant, retake start, score/accuracy/wrong/absent reports, report export, and question/roster template downloads. This is historical evidence and does not satisfy the new destructive migration or real invitation UAT gates.
- Question import batch `20`: `success_count=4`, `failed_count=1`; failed row `6`, reason `正确答案必须存在于选项中`.
- Roster import batch `21`: `success_count=2`, `failed_count=1`; failed row `4`, reason `姓名不能为空`.
- Created `exam_id=1`, `primary_candidate_id=1`, `attempt_id=1`, and `retake_attempt_id=2`.
- Report query sizes: scores `1`, accuracy `4`, wrong questions `1`, absent candidates `1`.
- Template download smoke: question template sheet `题库导入模板`, historical roster template sheet `应考名单导入模板`.
- Backend and nginx logs for the UAT requests were HTTP 200, and Compose services remained Up after the run.

## Implemented Business Loop

- Question import validates Excel rows and persists valid questions, options, and an import batch with failure details.
- Single-exam roster import validates normalized email/name rows and persists frozen-scope accounts plus an import batch with failure details; standalone global account/person import is not a supported route.
- Roster imports reuse active/pending accounts by normalized email or create pending accounts; missing/invalid/duplicate/inactive rows fail without name-based merge or automatic access.
- Import failure report download returns an Excel workbook with batch metadata and row-level failure details.
- Exam configuration create/update/list services persist to the `exam` table, and active-user listing requires `X-Candidate-Token` and returns published exams in that account's frozen `exam_candidate_scope`, including upcoming opening time.
- `available_from` and `available_until` limit new exam starts. Existing in-progress attempts can be resumed after `available_until` and still hand in based on `started_at + duration_minutes`.
- Publishing an exam from draft to active freezes the current active question bank into `exam_question_pool`; start exam samples from that frozen pool while keeping attempt question snapshots.
- Exam start creates an in-progress attempt and stores question snapshots.
- Non-empty `question_rule` with `question_count` uses fixed-paper mode. The admin editor default template is 50 questions, total score 100, pass score 60, and type counts `single: 30`, `multiple: 10`, `judge: 10`.
- Fixed-paper rules must explicitly provide positive integer `question_count`, positive integer `total_score`, and `type_counts` whose `single`/`multiple`/`judge` values are non-negative integers summing to `question_count`.
- Fixed-paper selection only uses active questions, avoids duplicate stems in the same paper, covers `category_1`, question types, and available `category_1 + question_type` combinations.
- Fixed-paper scores are integer and evenly distributed from `question_rule.total_score`; 50 questions with total score 100 gives every question 2 points.
- Empty `question_rule = {}` remains compatible with the legacy all-active question behavior.
- Exam-roster import adds email-keyed rows to `exam_candidate_scope`; publication freezes roster name/email/organization identity. Draft rows may be removed; published rows are immutable. Initial invitations are explicit and resend is failed-only.
- Exam candidate management can list frozen scope rows and grant one retake. An unused retake grant allows a submitted account to start a new `retake` attempt, which consumes the grant.
- Answer autosave writes to `exam_attempt_answer`; hand-in scoring updates persisted answers and attempt totals.
- The exam-taking page uses the final question primary action as “交卷”; earlier questions still show “下一题”.
- Time-based auto-submit runs as an asyncio background task, checking every 30 seconds.
- Ranking and reports (score, accuracy, wrong questions, absent candidates) use real SQL queries.
- Score, accuracy, wrong-question, absent-candidate, and export reports support `exam_id` filtering. Global reports remain available as an optional view.
- Report export returns one Excel workbook with sheets for `个人成绩`, `题目正确率`, `错题排行`, and `参考状态`.
- Admin authentication uses a configured username/password login plus signed session token; frontend stores the token and redirects on 401.
- Candidate authentication accepts only normalized `email`; `/api/candidates/login/verify` returns authenticated, registration-required, or account-unavailable outcomes. New/pending accounts complete display name before token issuance; candidate frontend clears stale session state on logout, expiry, guarded revocation, or inactive-account 401 and preserves safe invitation return paths.
- Login challenge rows are email-bound and commit before bounded SMTP delivery; the six-digit/ten-minute/single-use/five-attempt/60-second contracts and persisted per-email/source/global limits prevent enumeration and burst abuse. No sentinel row, shared code, or manual login bypass remains in the live contract.
- Practice mode uses `X-Candidate-Token` for question listing and answer submission, re-checks active account status, and does not expose correct answers or analysis before submission.
- Video learning uses `X-Candidate-Token` for published video listing, detail, and progress heartbeat. Watched intervals are merged server-side so repeated playback and seek jumps do not inflate completion; learning reports use account identity, while formal reports use frozen roster identity.
- Video learning completion is independent from exam eligibility, exam start/submit, scoring, ranking, and practice behavior. The current completion threshold is 90%.
- Admin learning pages support local `mp4` / `webm` upload, client-side duration extraction, publish/archive actions, title/description edits, video/status-filtered learning report, and Excel export.

## macOS Acceptance Implementation Verification (2026-08-11)

The macOS acceptance implementation was reverified after adding generation-1 writer commissioning, schema-2 staging evidence, privileged host evidence, release sealing, and crash-resumable writer lineage handling. These are engineering-gate results, not substitutes for the remaining real-host evidence:

- Backend: 564 passed, 10 skipped; Ruff and `ty` passed.
- Frontend: 64 files / 349 tests passed; Prettier, ESLint, and the production build passed.
- OpenSpec strict validation: 11/11 specs and changes passed. The macOS change remains 39/44 tasks complete; real tasks 4.5, 6.7, and 8.1–8.3 remain open.
- All macOS zsh entrypoints parsed successfully; LaunchAgent plist templates and Compose configuration checks passed.
- A disposable PostgreSQL migration/concurrency run passed and removed its scoped test project afterward.
- Docker Desktop is configured for login auto-start with Resource Saver disabled. The live host still lacks an approved reserved LAN address, a mounted independent encrypted second-copy disk, complete formal/staging configuration, an installed current release, and loaded formal LaunchAgents.
- No formal service was started and no real SMTP, second-device/CIDR, desktop/mobile UAT, restart/reboot, or second-copy restore result was represented as passed.

## Email Registration And Invited Exams Implementation Verification (2026-08-11)

`open-email-registration-with-invited-exams` was archived on 2026-08-12 after implementation and local verification reached `85/88` tasks. The operator explicitly directed OpenSpec to archive and synchronize the change while waiving the three remaining gates (`12.4`, `12.6`, and `12.8`). The archived task file retains those unchecked items as an accurate warning; the archive action does not relabel them as formal-writer, independent-second-copy, or verification evidence.

- Before archive, `openspec validate open-email-registration-with-invited-exams --strict --no-interactive` passed. After main-spec synchronization and overlap rebasing, `openspec validate --specs --strict --no-interactive` passed `10/10` specs and `openspec validate --all --strict --no-interactive` passed `13/13` specs and active changes. `python3 scripts/check-legacy-contracts.py`, `git diff --check`, and `docker compose --env-file .env config --quiet` also passed.
- Backend format, Ruff lint, and `ty check` passed. The ordinary local suite passed `596` tests with `10` PostgreSQL-only tests skipped because `POSTGRES_TEST_DATABASE_URL` was unset. `bash scripts/test-backend-full.sh` then created a disposable PostgreSQL project, upgraded from the historical release chain through `202608110001`, ran those migration/concurrency cases, and passed all `606` tests before cleaning the project.
- Frontend Prettier, ESLint, TypeScript/Vite production build, and Vitest passed; Vitest reported `65` files and `359` tests, including bounded invitation polling and explicit final-status refresh after slow background delivery.
- `sh ops/e2e/run-browser-gate.sh` passed `3/3` Playwright flows through disposable Nginx/backend/PostgreSQL/fake-SMTP containers: open registration with invitation return and pre-open rejection, explicit invitation initial-send/failed-only resend, and inactive-account/deactivation session cleanup. Publication did not implicitly send invitation mail, and captured links carried no bearer credential.
- The implementation now uses email-only OTP, pending/active/inactive accounts, read-only account email, editable display name, frozen per-exam roster identity, scope-only formal authorization, explicit invitation delivery state, shared practice/formal question-bank semantics, and frozen-identity reporting. The legacy employee-number, phone-suffix, global-attendance, sentinel-login, and standalone candidate-import runtime contracts are guarded against reintroduction.
- Main specs were synchronized during archive: 22 requirements were added, 23 modified, and 2 removed across 7 capabilities. Formal-writer evidence and independent encrypted second-copy work are deferred outside this archived change. Windows evidence remains a future independent target and cannot reuse Mac-local proof.

### Historical Local LAN Deployment And Real-SMTP UAT (2026-08-12)

This is historical local operating evidence for a temporary LAN address, not normative deployment configuration, formal-writer commissioning, or independent-second-copy acceptance:

- The historical Docker deployment bound the candidate gateway to `http://192.168.2.29:8080` (synthetic/local evidence only) and the operator gateway to `http://127.0.0.1:8081`. The backend CORS origin and bearer-free invitation base URL used the same candidate origin, and candidate access to `/operations`, `/admin`, admin/operations/readiness APIs, docs, and OpenAPI returned `404`.
- Compose rendered successfully and all six services (`db`, `backend`, `auto-submit-worker`, `frontend`, candidate Nginx, and operator Nginx) returned after a whole-project restart. Candidate health and operator readiness returned `200`; the database remained at migration head `202608110001` with one active account and one consumed OTP challenge.
- The user confirmed receipt of the real OTP and completed first registration/login. Candidate learning, practice, and exam-list API requests then returned `200`, with no mailbox address, OTP, candidate token, or SMTP credential emitted in the recorded operator evidence.
- A local-only future exam was published with one frozen scope. Publication left invitation counts at `not_sent=1`, `sent=0`, and `failed=0`, proving that publication did not send mail automatically.
- For the explicit initial invitation action, the SMTP host was temporarily changed to an unreachable loopback endpoint. The configured three-attempt bounded retry ended in `failed=1`, released the delivery claim, and recorded only sanitized audit counts/classes. The original SMTP host was restored immediately and the backend returned healthy before the next action.
- The explicit failed-only resend selected exactly that one failed row and reached `sent=1`, `failed=0`, `not_sent=0` with the claim cleared. Protected audit metadata recorded the initial failed outcome and the resend sent outcome. The configured link resolved to the historical local address `http://192.168.2.29:8080/exams/1/start` with no query string, bearer credential, OTP, email, scope identifier, or invite code.
- After the whole Compose restart, the existing browser session still loaded the invited exam as `应考人员 · 已受邀`, displayed the future opening time, kept `尚未开放` disabled, and produced no browser console warning or error.
- The pre-deployment database/media backup and disposable isolated restore rehearsal remain local recovery evidence only. Per the current operator decision, independent encrypted second-copy work is deferred; it is not represented as complete.

The user confirmed that the resent invitation arrived and contained the expected local link, completing task `12.5`. The change was then archived at `85/88` with explicit authorization to bypass the remaining `12.4`, `12.6`, and `12.8` gates. Its canonical archived path is `openspec/changes/archive/2026-08-12-open-email-registration-with-invited-exams/`; the unchecked tasks remain visible there and are treated as waived or deferred, not passed.

## Frontend Visual System Implementation Verification (2026-08-14)

The active OpenSpec change `unify-frontend-visual-system` was implemented as a
frontend-only visual-system hardening pass. It retains the Academic Editorial
direction while defining Candidate Calm, Admin Workbench, Exam Focus, and
chrome-free Auth Canvas compositions. `frontend/DESIGN.md` is now the canonical
human-readable contract for the live CSS tokens, offline-safe font stacks,
surface ownership, state language, navigation, motion, accessibility, and
responsive acceptance rules.

Observed final engineering gates:

- `npm run format:check`, `npm run lint`, `npm run build`, and
  `npm run check:offline` passed from `frontend/`; the offline check reported
  `external_runtime_references=0`.
- Vitest passed `80/80` files and `430/430` tests.
- `sh ops/e2e/run-browser-gate.sh` passed `161/161` Playwright tests: six
  formal desktop flows, one formal mobile flow, and 154 deterministic visual
  system cases in the `chromium-visual-system` project.
- The rendered matrix covered 320x844, 375x812, 414x896, 430x932, 768x1024,
  and 1280x900, plus 844x390 and 896x414 landscape checks, reduced motion, and
  a 200-percent zoom spot check. It exercised candidate/auth/admin/focus
  layouts, grouped navigation, mobile Sheets, heading order, visible focus,
  action reachability, stale data, and saved/saving/offline/conflict/submitted
  states with root clipping disabled during overflow assertions.
- The rendered gate exposed and verified fixes for a 768px roster-table
  overflow and a wide learning-report overflow. `SimpleDataTable` now uses
  cards below the wide-layout breakpoint and keeps tables with more than seven
  columns in the card renderer instead of hiding overflow.
- Static scans found the only raw `<select>` in the shared native Select
  primitive; no production italic class, legacy HSL token, independent
  768/1024 media literal, or numeric z-index utility remains. Raw visual colors
  are limited to the canonical `index.css` tokens and the documented
  data-derived avatar palette exception. Admin `stagger` call-site props remain
  inert because `PageShell` only emits `data-stagger` for its governed calm
  orientation density.

The browser artifacts under `.runtime/e2e/browser-output/` are disposable
Chromium engineering evidence and are not committed. They do not constitute
formal Mac/Windows host acceptance, Safari/iOS/Android acceptance, real-device
UAT, or a production promotion decision. This change did not modify backend
endpoints, API payloads, route definitions, authentication, exam snapshots,
scoring, deadlines, retake, polling, or auto-submit semantics.

## Frontend Design System V2 Convergence Verification (2026-08-14)

The active OpenSpec change `converge-frontend-design-system-v2` completed the
route-wide convergence pass on top of the Academic Editorial direction. The
implemented contract now has one token source, one page-frame width owner,
shared surface/form/status/action/table patterns, and explicit Auth Canvas,
Candidate Calm, Admin Workbench, and Exam Focus family rules. The current
human-readable contract is `frontend/DESIGN.md`.

Observed final engineering gates:

- `npm run format:check`, `npm run lint`, `npm run build`, and
  `npm run check:offline` passed from `frontend/`; the offline check reported
  `external_runtime_references=0`.
- Vitest passed `92/92` files and `576/576` tests. The focused design-token,
  copy, accessibility, hierarchy, and presentation-policy gate passed `5/5`
  files and `39/39` tests.
- `npm run test:e2e:visual` passed `237/237` cases with system Google Chrome
  `151.0.7922.138`, with zero failed or skipped tests.
- `sh ops/e2e/run-browser-gate.sh` rebuilt the isolated production-like stack
  and passed `244/244` cases with Chromium `139.0.7258.5`: six formal desktop
  flows, one formal mobile flow, and 237 visual-system cases, with zero failed
  or skipped tests. The script removed its disposable containers, network,
  PostgreSQL, learning-media, and worker-state volumes after the run.
- The rendered matrix covered 320x844, 375x812, 414x896, 430x932, 768x1024,
  and 1280x900, plus 844x390 and 896x414 landscape viewports, reduced motion,
  and 200-percent zoom. It exercised every declared auth, candidate, admin,
  and active-exam route/state entry, including long CJK and unbroken content,
  loading/empty/error/stale/pending/success states, result release boundaries,
  saved/saving/offline/conflict/submitted/auto-submitted states, mobile Sheets,
  Dialog scrolling, keyboard focus, touch targets, safe-area ownership,
  horizontal overflow, and action reachability after scrolling.
- The final browser pass verified the fixes surfaced during rendered testing:
  transient Sheet overlays no longer produce covered-action false positives;
  fixed Exam Focus controls retain pointer ownership and safe-area clearance;
  short-landscape auth and exam layouts remain reachable; long titles and
  identifiers wrap; learning-video file selection exposes one accessible
  product action; and save-state fixtures no longer queue behind an unintended
  empty-draft request.
- Operator learning-video metadata inspection requires a local `blob:` media
  URL. `nginx/operator.conf` therefore widens only the operator
  `media-src` directive to include `blob:`; candidate CSP and all
  script/style/connect/object/frame directives remain unchanged. Exact
  deployment assertions passed `19/19` in
  `backend/app/tests/test_deployment_config.py`.
- The frontend Docker context still excludes executable E2E suites while
  allowing only the declarative route-state inventory shared by router tests
  and rendered coverage. No package or lockfile change was introduced.

The implementation did not change backend business code, route destinations,
API request or response contracts, authentication, snapshot/scoring/save/
submit behavior, import/report semantics, or dependencies. Browser artifacts
under `.runtime/e2e/browser-output/` remain disposable engineering evidence;
they are not formal Mac/Windows host acceptance, Safari/iOS/Android acceptance,
real-device UAT, or a production promotion decision.

## Admin Navigation Hierarchy Verification (2026-08-17)

The shared admin navigation now hides single-destination group labels visually
while retaining their `aria-labelledby` semantics. Multi-destination labels use
a caption-and-rule treatment, destination rows keep 48px targets with distinct
hover/active/focus states, and desktop/mobile share the same four-block rhythm.
The `/admin/exams` destination is labelled `考试编排`; its route, active pattern,
order, group ID, and permission boundary are unchanged.

Observed final engineering gates:

- `npm run format:check`, `npm run lint`, `npm run build`, and
  `npm run check:offline` passed; Vitest passed `92/92` files and `581/581`
  tests, including `26/26` focused layout tests.
- `sh ops/e2e/run-browser-gate.sh` passed `244/244` Playwright cases and
  removed its disposable containers, network, and data volumes afterward.
- OpenSpec strict validation passed `14/14`; `git diff --check` passed.
- The daily Compose stack was rebuilt with `up -d --build` without removing
  persistent volumes. Candidate health, operator readiness, migration head,
  and candidate/admin route separation remained correct.
- Rendered desktop and mobile checks confirmed label hierarchy, 24px block
  separation, 8px label-to-links spacing, 4px adjacent-link spacing, active
  navigation, menu close behavior, zero horizontal overflow, and no related
  console errors.

This pass did not change backend code, API or route contracts, authentication,
exam behavior, dependencies, migrations, or OpenSpec artifacts. The rendered
checks are local Chromium engineering evidence, not formal real-device or
designated-host acceptance.

## Repository Security Remediation Verification (2026-08-31)

The active OpenSpec change `remediate-repository-security-findings` implements
the code and local-contract remediation mapped to the 15 findings from scan
`f7b16a71-afca-4d54-8f5d-23915b46d02d`, based on clean commit
`665a5bf6a2d42e67c0f10f687108957fab2ffa37`. It remains active at `29/32`
tasks: remote clean-HEAD evidence, designated-host drills, and a fresh complete
Codex Security scan are intentionally not represented as complete.

Observed final local engineering gates:

- Backend format, Ruff, and `ty` passed. The ordinary suite passed `718` tests
  with `13` expected PostgreSQL-only skips. The disposable PostgreSQL 16 gate
  upgraded the full Alembic chain through `202608300001` and passed all `731`
  tests with no skips, then removed its scoped test project.
- Frontend format, lint, production build, and offline-asset checks passed;
  Vitest passed `86/86` files and `547/547` tests, and the built runtime had
  `0` external references.
- The disposable browser gate passed `7/7` Playwright flows through the split
  candidate/operator gateways and removed its containers, networks, and
  volumes. Legacy-contract, Compose render, macOS zsh syntax, strict OpenSpec
  (`14/14`), and `git diff --check` also passed.
- A content-equivalent temporary clean Git revision passed the disposable
  100-client capacity gate with `100/100` submissions, `0` errors,
  start/save/submit p95 of `919/882/746 ms`, database connection peak `17/40`,
  and a valid report checksum. Its containers, networks, volumes, and temporary
  repository were removed without changing this checkout or its Git history.
- A post-patch bypass review found and closed three local gaps before the final
  rerun: SQLAlchemy URL query overrides now fail before credential/DDL guards;
  practice retention uses SQL aggregation, window selection, bounded preview
  paging, and selected-account revalidation; LaunchAgents execute only through
  an external owner-only trusted runtime that verifies current state and both
  release signatures before dispatching release code.
- No package/lockfile or runtime dependency changed. The completed hardening
  change and the unchecked Windows tasks `12.4`/`12.5` are untouched.

Still required before calling the 15 finding identities closed: a clean new
HEAD with every remote CI job and real pip-audit/npm audit/Trivy evidence; the
designated Mac's offline key custody, current/previous release signing,
tamper/rollback tests, approved live gateway routing, credential/token/OTP
rotation, and real practice archive/paired-backup/delete drill; then a fresh
complete repository Codex Security scan with no deferred coverage.

## Release Candidate Verification (2026-09-04 / 2026-09-05)

The follow-up security implementation tasks `5.16`–`5.24` and release-path
tasks `5.25`–`5.27` are implemented. The first formal writer now has a
trusted-checkout `Prepare` → staging acceptance → `Activate` path and a
fresh-root regression. Staging configuration is generated explicitly from
protected formal configuration, requires real SMTP, and rejects incomplete
or overridden inputs before Docker starts. These are repository engineering
results; designated-host activation remains unperformed.

- Backend format, Ruff, and `ty` passed. The September 5 ordinary suite passed `786`
  tests with `13` PostgreSQL-only skips. The disposable PostgreSQL 16 gate
  applied migrations through `202608300001`, passed `799` tests with no
  skips, and cleaned its containers, network, and volume.
- Frontend format, lint, build, and offline checks passed; Vitest passed
  `86` files and `551` tests, with `0` external runtime references.
- The browser gate passed `7` Playwright flows (`6` desktop, `1` mobile).
  The September 5 rerun used the exact patched release images without
  rebuilding, passed in `16.0 s`, and cleaned its disposable containers,
  networks, and volumes. This does not replace real Safari, Android, or
  iOS acceptance.
- A disposable clean snapshot `d1bad8f07bb2b51058b33a1d114256da14f0172a`
  passed the unmodified 100-client capacity gate: `100/100` submissions,
  `0` errors, start/save/submit P95 `1106/987/801 ms`, maximum database
  connections `17/40`, and worker heartbeat age `7.584 s`. The preceding
  failure exposed a shared-IP quota collision; authenticated candidate
  operations now use per-account quotas, while public login/OTP retain
  IP plus identifier quotas. Thresholds were not raised.
- The September 5 capacity rerun used the exact patched `5afaed31` release
  images without rebuilding and passed `100/100` submissions with `0`
  errors. Start/save/submit P95 was `825/828/667 ms`, database connections
  peaked at `17/40`, and worker heartbeat age was `6.453 s`. The checksummed
  report retains all seven running service image identities; its temporary
  containers, networks, and volumes were cleaned.
- Compose rendering, legacy-contract checks, macOS shell syntax, both
  LaunchAgent plists, strict OpenSpec (`14/14`), and `git diff --check`
  passed. The temporary capacity checkout is no longer present after the
  interrupted session; these measured results are retained here.
- Security scan `1fddc506-f106-4142-a78a-72bed5c50cdd` was interrupted
  before threat-model completion. Its working directory and workers were
  lost; it produced no report and is not passing security evidence.

- The native release build exposed stale cached OS upgrade layers and
  `10` HIGH scanner blockers. `Build-ReleaseImages.zsh` now uses
  `--no-cache`; the verified candidate contains OpenSSL `3.5.8-r0`, SQLite
  `3.53.4-r0`, and Expat `2.8.4-r0`. The real identity-bound Trivy,
  pip-audit, and npm audit gate passed for clean temporary snapshot
  `5afaed31bfdffe8466b1e317e6191712b4fb7755`, with `0` blocking findings,
  `0` binding errors, and `7` retained non-blocking findings (`5` MEDIUM,
  `2` LOW; pip tooling and postcss-selector-parser). No severity threshold
  or vulnerability disposition was relaxed. Candidate `0.1.0-rc.2` was
  sealed with its exact raw scanner evidence; production signing is still
  required. Failed scanner reports remain separate from the passing run.
- An isolated copy passed `Sign-ReleaseBundle` and strict `Test-ReleaseBundle`
  using a disposable RSA-3072 test key; both detached signatures also passed
  direct OpenSSL verification. A second copy with a changed `README.md`
  failed strict verification with `release checksum failed: README.md`.
  The original candidate remained unchanged and unsigned. This verifies
  local signing/tamper mechanics, not production key custody or host rollout.

The source-security review then identified formal/staging signing-key reuse,
a concurrent limiter race, unassigned-exam lifecycle disclosure, and bounded
XML entity expansion. Tasks `5.29`–`5.32` now implement and test the shared
guards without new dependencies. The staging check also rejects quoted
signing keys, duplicate assignments, alternate dotenv syntax, and multiline
values before Docker. The latest ordinary backend suite passed `806` tests
with `13` PostgreSQL-only skips; disabling the XML guard makes all ten new
DOCTYPE regressions fail, while the enabled guard and normal imports pass.
The subsequent disposable PostgreSQL 16 rerun passed `819` tests with no
skips and cleaned its containers, network, and volume.
Candidate `0.1.0-rc.2` remains an intermediate artifact and must not be promoted.

The subsequent clean temporary snapshot
`6cff8f8c9a122dd8f2e93970328a0f55419c67f0` contains all four source fixes and
produced `0.1.0-rc.3`. Its native `linux/arm64` images passed the real release
security gate with `0` blockers, `0` binding errors and `7` retained
non-blocking findings (`5` MEDIUM, `2` LOW). The package was sealed and passed
`Test-ReleaseBundle --allow-signature-missing`; it is not production-signed.
The exact images passed all `7` browser flows in `16.6 s` and the 100-client
capacity gate: `100/100` submitted, `0` errors, start/save/submit P95
`940/794/620 ms`, maximum database connections `17/40`, worker heartbeat age
`6.250 s`. The first capacity invocation was rejected before measurement
because the temporary harness used a project name other than the required
`internal-exam-capacity`; changing only that harness input passed. Both the
rejection and passing checksummed reports are retained separately. All
disposable containers, networks and volumes were removed. Local artifacts
and a recoverable source Git bundle are under
`.runtime/release-candidates/2026-09-05/rc3/`; none of these results replaces
the pending complete source scan, designated-host acceptance or remote CI.

The original source scan `fd7a5bd3-92ce-43fc-8b03-a59a9a983856` completed
all `630/630` files at snapshot
`5505e19c588ed75d603774154240d9484edc7704`, with `4` LOW findings and no
deferred source coverage. The parent finished the files that unavailable
workers had not returned. Its sealed canonical report and JSON artifacts
are retained under
`.runtime/release-candidates/2026-09-05/source-scan-5505e19c/`.
That report describes the pre-fix snapshot; its findings must not be relabeled
as a clean rc.3 result.

Fresh rc.3 source scan `61aa4cff-e444-45ff-b9e2-4b12115063eb` has passed
preflight and saved its threat model and partial review coverage. Independent
review workers are unavailable because of the account usage limit. The parent
saved `38/630` fully reviewed current files; the other `592` files are not
counted. This is partial coverage, not a clean final scan, so task `6.6`
remains open. The user declined a usage reset; neither a reset nor a credit
purchase has been performed. A copy of the partial canonical JSON artifacts
is retained in `rc3/source-scan-incomplete/`. Tasks `6.4`
(remote CI/release evidence), `6.5` (designated-host
operational drills), and `6.6` (complete fresh security scan) remain open.
The workspace changes have not been committed or pushed.

## Known Gaps

- The local real-SMTP UAT is complete, but real Mac formal-host staging, promotion, host/Docker restart recovery, desktop/phone UAT, the formal-host SMTP rerun, and second-copy restore have not yet been executed on the designated host. These are blocking operator acceptance steps, not completed evidence.
- Future Windows Docker Desktop + WSL2 native AMD64 staging, paired-backup restore, Windows service recovery, desktop/phone UAT, and formal promotion have not been executed. Mac evidence cannot satisfy those Windows gates.
- Controlled-LAN `internal` mode intentionally uses HTTP on the shared office LAN. Candidate bearer tokens, questions, answers, and released results are not transport-encrypted and can be intercepted or modified by a device with network visibility. This is the explicitly accepted first-phase exception in `security-http-exception.md`; it has no calendar expiry but must be reassessed on the documented scope, network, incident, or policy triggers.
- The platform is one best-effort 24x7 Mac host with Docker/LaunchAgent container recovery, not high availability. A serious host, disk, Docker Desktop, power, or office-network failure may require pausing or rescheduling an exam.
- The local 100-client gate passed on the final rerun but showed host-load variance in the immediately preceding run. Formal Mac staging must produce its own passing host-bound evidence; future Windows staging must rerun the gate and cannot reuse the Mac artifact.
- SMTP retry is deliberately short and in-process, not a durable queue. A backend restart can interrupt delivery; operators must retain resend and final-failure monitoring procedures.
- Invitation delivery is deliberately explicit and recoverable: publication sends nothing automatically, initial send targets `not_sent`, failed-only resend targets `failed`, and final per-recipient state must be verified after the scheduling response.

## Recommended Next Work

The historical full signed-release recommendations below are superseded for the
2026-09-08 deployment by the scoped local-Compose path recorded at the end of this
document. They remain applicable only if that full operations path is resumed.

1. On the designated Mac host, execute native ARM64 staging, Mac status/preflight checks, split-route checks, real SMTP fail-closed tests, service/Docker recovery, paired backup, independent encrypted second-copy restore, browser UAT, and the 100-client gate from `official-exam-uat-checklist.md`.
2. Create the formal pre-upgrade paired backup, promote only the tested commit-tagged ARM64 images, run desktop and phone UAT, then close sessions and retain the checksummed Mac evidence bundle. Do not call this Windows acceptance.
3. Keep HTTP `internal` exposure within the accepted office-LAN boundary. If a reassessment trigger occurs, stop expanding use and establish trusted HTTPS/network isolation before proceeding.
4. For a later Windows move, stop the Mac writer, create a final paired backup and writer-generation evidence, restore on native Windows AMD64 staging, and complete every Windows-specific gate before cutover.

## 2026-09-08 Minimal local deployment

The operator selected this Mac and `192.168.2.225`, with real SMTP reused from
the existing local `.env`. Scope is a fixed source/image version, `internal`
configuration, and runtime acceptance. Release signing, backups, second copies,
and restore drills are explicitly excluded from this deployment. This selection
does not constitute successful completion of those historical gates.

The procedure is in `docs/minimal-macos-deployment.md`. It uses a separate
`internal-exam-minimal` Compose project and fresh volumes, with configuration
under `~/Library/Application Support/InternalExamMinimal`. Existing development
volumes are retained. Ordinary upgrades of existing databases retain the
maintenance gate; explicit empty-database initialization must reject an existing
schema before running any migration.

Current local verification:

- Backend format, Ruff, and ty passed. After the empty-database change, the final
  full suite passed all 822 tests with PostgreSQL enabled. The default test port
  55432 belongs to another project, so this run used a disposable database on
  5432. An initial run encountered missing tables; applying the full migration
  chain resolved that test setup error before the final successful run.
- A separate PostgreSQL database completed explicit empty initialization through
  `202608300001`; repeating initialization with existing tables was rejected.
- Frontend format, lint, build, and offline-reference checks passed; 551 tests
  passed and `external_runtime_references=0`.
- The isolated browser suite passed all 7 desktop/mobile scenarios. It used fake
  SMTP, and its disposable backup invocation was omitted for this run. It is not
  evidence of real mailbox delivery or a physical phone check.
- The host currently reports `192.168.2.225`; the generated `internal` settings
  and Compose configuration validate. Candidate ingress is configured for 8080,
  and operator ingress stays on loopback 8081.
- Real SMTP TLS connection and authentication passed without sending a message.
  Docker Desktop has login auto-start enabled and Resource Saver disabled; the
  current AC-power sleep setting is zero.

Real SMTP receipt, physical-device acceptance, and whole-Mac restart recovery
remain pending until observed. Container restart checks do not close the last
item. Host deployment results are retained separately in the protected deployment
directory's `evidence/` so the tested source snapshot can remain fixed.

Deployment completed on this Mac from commit
`47b4c17cd7fce30447786a33a63b357b1f4f875d`, using image tag
`minimal-47b4c17cd7fc` and the protected exported source directory. All six
services are running; PostgreSQL, backend, and auto-submit worker health checks
pass. The fresh formal database is at migration `202608300001`.

Live HTTP acceptance passed: candidate health and homepage, loopback readiness
and operator login, authenticated report export with four worksheets, anonymous
report denial, and seven candidate-ingress administration/operations/docs
denials. Restarting all six containers and repeating those checks passed;
persisted admin audit rows remained present. The exported report currently has
no exam data because this is a fresh formal database.

The protected `evidence/internal-exam-minimal-live.json` records the runtime
results and outstanding physical-device/mailbox/whole-host checks. No connected
computer-use browser was available for a live GUI inspection; the 7 successful
isolated browser scenarios remain separate evidence. No remote push was made.
