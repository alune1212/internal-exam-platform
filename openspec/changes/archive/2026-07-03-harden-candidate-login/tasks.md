## 1. Persistence and Configuration

- [x] 1.1 Add a SQLAlchemy `CandidateLoginChallenge` model with candidate association, OTP verifier, expiration, consumption, attempt count, delivery channel, request IP hash, and timestamps.
- [x] 1.2 Add an Alembic migration for `candidate_login_challenge` with indexes for candidate lookup, expiration cleanup, and unconsumed challenge checks.
- [x] 1.3 Add minimal email/OTP settings for strict candidate login, including OTP TTL, attempt limit, resend cooldown, delivery mode, and SMTP configuration.
- [x] 1.4 Enforce production-safe email delivery configuration so production strict login cannot run with plaintext OTP logging or missing SMTP settings.

## 2. Backend Candidate Login Flow

- [x] 2.1 Replace the one-step `CandidateLoginRequest` path with schemas for OTP challenge request and OTP verification response while preserving the final candidate token payload shape.
- [x] 2.2 Implement candidate lookup by normalized `name + email + optional employee_no`, rejecting inactive, missing-email, ambiguous, or mismatched identities without issuing a token.
- [x] 2.3 Implement OTP generation, hashing/verifier comparison, short expiration, single-use consumption, previous-challenge invalidation on resend, and per-challenge attempt limits.
- [x] 2.4 Add an email delivery adapter boundary with deterministic fake/test delivery and SMTP delivery without putting SMTP details inside route handlers.
- [x] 2.5 Apply existing public token rate limiting to OTP request and verification endpoints using IP and normalized candidate identifiers.
- [x] 2.6 Keep candidate-facing exam, attempt, practice, and learning APIs consuming the existing `X-Candidate-Token` contract after OTP verification.
- [x] 2.7 Add backend tests for successful OTP request/verify, no-token challenge response, wrong OTP, expired OTP, consumed OTP reuse, resend invalidation, attempt exhaustion, inactive candidate, ambiguous identity, and rate limiting.

## 3. Import and Roster Email Validation

- [x] 3.1 Require valid email values for new candidate import rows and return row-level failure reasons for missing or invalid email.
- [x] 3.2 Require exam-candidate imports to ensure every scoped candidate has a usable email before adding `exam_candidate_scope`.
- [x] 3.3 Backfill an existing candidate's missing email from a valid exam-candidate import row, but reject rows that conflict with an existing candidate email.
- [x] 3.4 Update import tests for missing email, invalid email, successful new candidate email persistence, existing-candidate email backfill, and conflicting email rejection.

## 4. Frontend Login Experience

- [x] 4.1 Update `frontend/src/api/auth.ts` to call the OTP challenge request and OTP verification endpoints without hand-rolled fetch logic in pages.
- [x] 4.2 Update the candidate login page to collect name, email, and optional employee number before showing the OTP verification step.
- [x] 4.3 Add OTP entry, resend cooldown, loading, neutral error, expired/retry, and successful-login states using existing UI primitives and page copy patterns.
- [x] 4.4 Preserve existing candidate session handling after successful verification and keep unauthorized-session clearing behavior intact.
- [x] 4.5 Add frontend tests for initial identity form, OTP request transition, verification success, verification failure, resend cooldown, and no pre-login candidate API calls.

## 5. Documentation and Operational Guidance

- [x] 5.1 Update API docs to describe the two-step candidate login endpoints and the unchanged `X-Candidate-Token` usage after verification.
- [x] 5.2 Update database docs for `candidate_login_challenge` and strict-login email prerequisites on candidate records.
- [x] 5.3 Update import template/docs/UAT guidance to state that candidate email is required for strict login and that SMS/SSO are out of scope for this change.
- [x] 5.4 Update handoff notes with the strict login contract, email delivery configuration, and any remaining session-storage risk.

## 6. Verification

- [x] 6.1 Run backend formatting, lint, type, migration, and test checks: `cd backend && uv run ruff format . --check && uv run ruff check . && uv run ty check && uv run alembic upgrade head && uv run pytest`.
- [x] 6.2 Run frontend checks: `cd frontend && npm run format:check && npm test -- --run && npm run lint && npm run build`.
- [x] 6.3 Run Docker config/build smoke for strict-login settings: `docker-compose --env-file .env config` and, when environment permits, `docker-compose up -d --build`.
- [x] 6.4 Smoke test through `http://localhost:8080/login`: request OTP for a rostered candidate, verify OTP, confirm `/exams` loads with the candidate token, and confirm direct old phone-suffix login no longer issues a token.
