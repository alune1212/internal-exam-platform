## Context

`2026-07-03-harden-candidate-login` introduced a two-step email OTP candidate login. The verify path was hardened in the follow-up `fix:` commit (atomic conditional UPDATE, bounded outbox), but the **request** path still leaks information through two independent signals:

1. **Network-on-the-transaction**: `send_candidate_login_otp` is invoked synchronously after `db.flush()` and before `db.commit()`. SMTP latency (or failure) holds the DB connection and produces a 503 the caller can observe.
2. **Response differential**: lookup failures (no row, ambiguous, inactive, missing email) raise `CandidateLoginError` (404) or `CandidateLoginAmbiguousError` (409). Together with the SMTP-failure 503, that gives an attacker at least four distinguishable outcomes from a single challenge request.

The fix has to remove both signals without changing the public token contract, without adding infrastructure, and without dropping the existing per-challenge attempt limit and resend cooldown.

## Goals / Non-Goals

**Goals:**

- Commit the `CandidateLoginChallenge` row before any network call, so the request is durable on first acceptance.
- Move the email send to a post-commit hook (FastAPI `BackgroundTasks` in this change) so a slow or failing SMTP server does not roll back the challenge or surface a 503 to the caller.
- Return a uniform 200 envelope (`CandidateLoginChallengeResponse`) for every challenge request, regardless of whether the candidate was found, ambiguous, inactive, missing an email, or hit an SMTP failure.
- Audit unknown-identity attempts through structured logs (rate-limited WARN) so operators can detect enumeration without exposing the result to the caller.
- Keep all existing guarantees: short OTP TTL, single-use consumption, resend cooldown, per-challenge attempt limit, IP+identifier rate limit, and the `X-Candidate-Token` contract on successful verify.

**Non-Goals:**

- No Redis, Celery, SQS, or any external queue. `BackgroundTasks` (in-process) is sufficient for the first hardening pass.
- No session-storage migration, no cookie/CSRF work, no SSO, no CAPTCHA, no MFA.
- No changes to the candidate model, the import-time email validation, the existing rate limiter, the OTP length, or the email delivery modes.
- No telemetry pipeline beyond a structured WARN log line.

## Decisions

### Decision: Persist challenge before any network call

`request_candidate_login_challenge` runs as:

1. Resolve candidate row (or detect "no row / ambiguous / inactive / missing email" — all of these are funneled into a single branch from this point on).
2. Generate OTP and build a `CandidateLoginChallenge` row.
3. `db.add(...)`, `db.commit()` so the row is durable.
4. Schedule the email send through FastAPI `BackgroundTasks` (which runs after the response is sent).
5. Return the uniform `CandidateLoginChallengeResponse` with the persisted `challenge_id` and `expires_at`.

If the background email send fails, the challenge row is still valid and the candidate can still verify (or, more commonly, request a new challenge). The caller never sees the SMTP outcome.

Alternatives considered:

- **Synchronous send after commit, but catch and log all errors inside the route** — the route is already thin; pushing the try/except there mixes HTTP and delivery concerns.
- **Outbox table polled by a worker** — most operationally robust, but violates the no-queue boundary.
- **Defer the entire change** — the previous hardening stops the replay/lost-update but leaves the enumeration oracle open.

Rationale: `BackgroundTasks` is built into the existing FastAPI stack, runs after the response, and keeps the SMTP error out of the request lifecycle.

### Decision: Uniform 200 response for every challenge request

The route always returns 200 with `CandidateLoginChallengeResponse`. The following lookup outcomes are normalized to the same response:

- No matching candidate
- More than one matching candidate (ambiguous)
- Inactive candidate
- Active candidate with no email on file

For the "no matching row" and "ambiguous" branches, the service still generates an `otp` and a real `CandidateLoginChallenge` row, but the row is created against a **sentinel candidate id** (e.g., a designated dummy candidate whose `email` is null and which is excluded from any scope) so the OTP can never be used to log in. The send step is skipped for those rows; the response envelope is identical. This keeps the row count and DB shape the same as for real candidates, so an attacker cannot infer success by timing or by the number of rows touched.

Active-but-missing-email candidates fall into the same "uniform response, no real send" path; the row is persisted with a sentinel candidate id and never consumed. A future change can give operations a way to backfill the email.

Alternatives considered:

- **Return 200 with a `delivered: true|false` flag** — exposes the same signal in the response body. Rejected.
- **Use a fake email send path that "succeeds" without writing a row** — leaks "did the row get created?" through timing/row count.
- **Return 404/409 for "no row / ambiguous" and 200 for everything else** — keeps the original signal. Rejected.

Rationale: uniform shape, uniform timing, real DB row, and no real email send is the standard mitigation for OTP enumeration.

### Decision: Audit unknown-identity attempts through structured logs

When the request resolves to "no row / ambiguous / inactive / missing email", the service emits a single structured WARN log line with:

- `event=candidate_login.unknown_identity`
- `request_ip_hash` (matches the field on `CandidateLoginChallenge.request_ip_hash`)
- The submitted identity (name + email SHA-256 hash, employee number hash) — never plaintext
- A monotonically increasing counter so an attacker cannot use the log volume as a side channel beyond what the rate limiter already exposes

Logs are rate-limited through the existing public token rate limiter; the log line itself is suppressed if the limiter has already rejected the request.

Alternatives considered:

- **Telemetry table** — over-engineered for the first pass and creates a new persistence surface.
- **Send a silent email to a security mailbox** — extra delivery surface, easy to ignore.

Rationale: structured WARN with a documented event name is enough to enable detection; more sophisticated observability can be added in a later change.

### Decision: Update login-page copy and state machine

`LoginPage` previously branched on 404/409 to show an error card. After this change, the identity step always transitions to the OTP step on a 200, regardless of what the backend actually did. The OTP step needs new copy that helps the candidate diagnose "I never got the email":

- A short explainer that emails can take 1–2 minutes, can land in spam, and that they can request a new code after the cooldown.
- The existing resend cooldown is reused.
- If the candidate types an obviously-wrong email, the explainer points to the admin contact without saying "this email doesn't exist" (which would recreate the enumeration oracle on the client).

The frontend does not introduce any new error states tied to the lookup outcome.

### Decision: Backend test rewrite

Tests in `test_candidate_flow_api.py` that previously asserted 404/409 from the challenge request now assert 200 with the uniform envelope. New negative tests assert that:

- The verify step still rejects OTPs that point at the sentinel candidate id.
- The rate limiter still caps challenge requests.
- The `CandidateLoginChallenge` row count is the same whether or not a real candidate was found (proving the timing/observation equality from the DB side).
- An SMTP failure during background delivery does not roll back the challenge row.

## Risks / Trade-offs

- **Lost legitimate error messages** — Candidates typing the wrong email or employee number will not see an immediate "no such candidate" message. They have to wait for an email that will not arrive, then either retry or contact the admin. **Mitigation**: short, prominent explainer on the OTP step; admin contact on the login page; ops alerting on `candidate_login.unknown_identity` volume spikes.
- **In-process BackgroundTasks not durable** — If the worker process crashes between commit and background send, the candidate gets a challenge id but no email, and must use the resend flow. **Mitigation**: the resend flow is already part of the contract; an outbox table is a future change if durability becomes a problem.
- **Sentinel-candidate row contention** — All unknown-identity requests funnel into a single sentinel id, which becomes a hot row. **Mitigation**: keep the sentinel candidate id's row simple (no FK to scope tables), and consider a sharded sentinel pool if write contention shows up in production.
- **Frontend regression risk** — The login page copy and state machine change is user-visible. **Mitigation**: cover the new behavior in `P0Pages.test.tsx` and `LearningPages.test.tsx`-style integration tests; keep the old "未找到匹配的考试人员" string out of the page copy.
- **Log volume** — A noisy enumeration attempt could spam WARN logs. **Mitigation**: rate-limit the log line at the same threshold as the public token rate limiter.

## Migration Plan

1. Add the structured `candidate_login.unknown_identity` log line and a sentinel candidate row (idempotent migration / fixture).
2. Refactor `request_candidate_login_challenge` to commit before delivery, normalize responses, and skip delivery for non-real-candidate rows.
3. Wire `BackgroundTasks` into the route handler in `backend/app/api/candidates.py`.
4. Rewrite the affected backend tests to assert the new contract; add the new negative tests.
5. Update `LoginPage.tsx` and `pageCopy.ts` to drop the identity-step error branches and add the OTP-step explainer.
6. Update `docs/api-design.md`, `docs/handoff.md`, and `docs/official-exam-uat-checklist.md`.
7. Run the full verification suite (backend ruff/ty/pytest, frontend prettier/eslint/build/test) before archive.

Rollback strategy:

- The DB change is additive (one new row in `candidate` for the sentinel); rollback drops it.
- The service refactor is self-contained; reverting the service to the previous behavior restores the 404/409 responses, but leaves the previous OTP contract in place.
- The frontend change is a copy/state machine revert; reverting that brings back the original error branches.

## Open Questions

- Should the sentinel candidate id be a single row or a small pool to avoid hot-row contention under enumeration attacks?
- Do we want to expose a "did this candidate really get an email" status in the admin UI, or keep the audit signal logs-only?
- How long should the OTP-step explainer stay visible — until resend, until success, or until the candidate navigates away?
- Should the rate limiter cap be reduced for the unknown-identity branch specifically, given the additional log spam risk?
