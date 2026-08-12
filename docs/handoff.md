# Handoff

## Current State

The project has a runnable first-phase business loop, completed frontend redesign, and an implemented internal-deployment hardening layer. It has a backend, frontend, database migration, Docker Compose stack, operational backup tooling, and a Mac-first formal-host documentation set. The current formal target is Apple Silicon macOS + Docker Desktop; Windows Docker Desktop + WSL2 remains a future migration target.

Implemented foundations:

- FastAPI app with shallow `/api/health` liveness and dependency-aware `/api/ready` checks for PostgreSQL and learning media access.
- SQLAlchemy compatibility account rows, email-bound login challenges, frozen exam scopes, questions, options, exams, attempts, attempt question snapshots, answers, practice answers, and import batches.
- Alembic migrations through `202608110001_email_accounts_and_invited_exam_scopes.py`, including the compatibility backfill/writer-fence lineage and the email-account, frozen-roster, and invitation-state migration. The destructive legacy-field step remains gated by the account-migration preflight and restore-only rollback contract below.
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
- Learning media served through Nginx `/media/learning/` from the `learning_media` volume.
- Candidate OTP delivery supports mutually exclusive STARTTLS and implicit SSL transports, retries transient SMTP/network failures with short bounded backoff, stops on permanent failures, and logs challenge/attempt/error type without recipient or OTP data.
- Paired backup tooling creates a PostgreSQL custom dump and `learning_media` archive with manifest, SHA-256 checksums, and a last-written `SUCCESS`; restore verification only accepts disposable Compose project names and validates migration head, representative table counts, media count, and non-empty samples.
- Formal attempts use one active device credential, monotonic answer revisions, session-scoped offline drafts, fresh-OTP takeover, terminal voiding, one-time result-detail release, and audited preview-first bulk retakes without changing saved question/answer/score snapshots.
- Practice submissions are immutable and return immediate answer/analysis feedback; wrong-question review is account-scoped and derives mastery from the latest attempt.
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

`open-email-registration-with-invited-exams` is implemented and locally verified at `84/88` tasks. The four remaining tasks are deliberately external or archive gates (`12.4`, `12.5`, `12.6`, and `12.8`); local or fake-service evidence is not being relabeled as formal-host, real-SMTP, backup/restore, or archive completion.

- `openspec validate open-email-registration-with-invited-exams --strict --no-interactive` passed, and `openspec validate --all --strict --no-interactive` passed `12/12` specs and changes. `python3 scripts/check-legacy-contracts.py`, `git diff --check`, and `docker compose --env-file .env config --quiet` also passed.
- Backend format, Ruff lint, and `ty check` passed. The ordinary local suite passed `596` tests with `10` PostgreSQL-only tests skipped because `POSTGRES_TEST_DATABASE_URL` was unset. `bash scripts/test-backend-full.sh` then created a disposable PostgreSQL project, upgraded from the historical release chain through `202608110001`, ran those migration/concurrency cases, and passed all `606` tests before cleaning the project.
- Frontend Prettier, ESLint, TypeScript/Vite production build, and Vitest passed; Vitest reported `65` files and `359` tests, including bounded invitation polling and explicit final-status refresh after slow background delivery.
- `sh ops/e2e/run-browser-gate.sh` passed `3/3` Playwright flows through disposable Nginx/backend/PostgreSQL/fake-SMTP containers: open registration with invitation return and pre-open rejection, explicit invitation initial-send/failed-only resend, and inactive-account/deactivation session cleanup. Publication did not implicitly send invitation mail, and captured links carried no bearer credential.
- The implementation now uses email-only OTP, pending/active/inactive accounts, read-only account email, editable display name, frozen per-exam roster identity, scope-only formal authorization, explicit invitation delivery state, shared practice/formal question-bank semantics, and frozen-identity reporting. The legacy employee-number, phone-suffix, global-attendance, sentinel-login, and standalone candidate-import runtime contracts are guarded against reintroduction.
- Remaining acceptance work is the selected Mac formal-writer/private-LAN and negative-route evidence with post-migration invariants, controlled real-SMTP OTP plus invitation UAT, verified paired backup and independent encrypted second-copy restore rehearsal, and final implementation verification/archive. Windows evidence remains a future independent target and cannot reuse the Mac restore proof.

## Known Gaps

- Real Mac formal-host staging, promotion, host/Docker restart recovery, desktop/phone UAT, real SMTP, and second-copy restore have not yet been executed on the designated host. These are blocking operator acceptance steps, not completed evidence.
- Future Windows Docker Desktop + WSL2 native AMD64 staging, paired-backup restore, Windows service recovery, desktop/phone UAT, and formal promotion have not been executed. Mac evidence cannot satisfy those Windows gates.
- Controlled-LAN `internal` mode intentionally uses HTTP on the shared office LAN. Candidate bearer tokens, questions, answers, and released results are not transport-encrypted and can be intercepted or modified by a device with network visibility. This is the explicitly accepted first-phase exception in `security-http-exception.md`; it has no calendar expiry but must be reassessed on the documented scope, network, incident, or policy triggers.
- The platform is one best-effort 24x7 Mac host with Docker/LaunchAgent container recovery, not high availability. A serious host, disk, Docker Desktop, power, or office-network failure may require pausing or rescheduling an exam.
- The local 100-client gate passed on the final rerun but showed host-load variance in the immediately preceding run. Formal Mac staging must produce its own passing host-bound evidence; future Windows staging must rerun the gate and cannot reuse the Mac artifact.
- SMTP retry is deliberately short and in-process, not a durable queue. A backend restart can interrupt delivery; operators must retain resend and final-failure monitoring procedures.
- Invitation delivery is deliberately explicit and recoverable: publication sends nothing automatically, initial send targets `not_sent`, failed-only resend targets `failed`, and final per-recipient state must be verified after the scheduling response.

## Recommended Next Work

1. On the designated Mac host, execute native ARM64 staging, Mac status/preflight checks, split-route checks, real SMTP fail-closed tests, service/Docker recovery, paired backup, independent encrypted second-copy restore, browser UAT, and the 100-client gate from `official-exam-uat-checklist.md`.
2. Create the formal pre-upgrade paired backup, promote only the tested commit-tagged ARM64 images, run desktop and phone UAT, then close sessions and retain the checksummed Mac evidence bundle. Do not call this Windows acceptance.
3. Keep HTTP `internal` exposure within the accepted office-LAN boundary. If a reassessment trigger occurs, stop expanding use and establish trusted HTTPS/network isolation before proceeding.
4. For a later Windows move, stop the Mac writer, create a final paired backup and writer-generation evidence, restore on native Windows AMD64 staging, and complete every Windows-specific gate before cutover.
