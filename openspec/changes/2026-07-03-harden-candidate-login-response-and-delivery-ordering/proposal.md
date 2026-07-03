## Why

The candidate OTP login flow hardened in `2026-07-03-harden-candidate-login` still has two residual issues that an automated security review flagged at MEDIUM:

1. `request_candidate_login_challenge` issues a network/SMTP call **inside** the open DB transaction, after `db.flush()` but before `db.commit()`. SMTP latency holds the DB connection, and SMTP failure means the caller's request is rejected with `EmailDeliveryError` (503) even though the candidate row was valid.
2. The same flow exposes a **user-enumeration oracle**: 404 (`CandidateLoginError`), 409 (`CandidateLoginAmbiguousError`), and 200/`EmailDeliveryError` distinguish "no match" from "match + SMTP failure" both in status code and in wall-clock timing.

A correct response to either signal lets an attacker confirm whether a name/email/employee number exists in the candidate roster. That matters even for an internal tool because the roster itself is the high-value target.

This change closes both signals without changing the public API contract or the auth/token semantics introduced by the previous OTP change.

## What Changes

- Reorder `request_candidate_login_challenge` so the challenge row is **persisted and committed first**, then the email is enqueued/sent through FastAPI `BackgroundTasks` (or a future task queue) **after** `db.commit()`. SMTP/network failure must not roll back the challenge, and must not propagate a 503 to the caller when the candidate row was valid.
- Return a **uniform success response** for every challenge request: any lookup outcome (no match, ambiguous match, inactive candidate, missing email, etc.) that previously surfaced a 4xx error or a 503 must now return the same 200 with a challenge id and a short fixed TTL, and must not actually send an email. Genuine unknown-identity attempts are logged at WARN with rate-limited context for audit.
- Add an explicit "unverified identity" log category that operators can monitor without exposing it in the public response.
- Update candidate login page copy to keep the UX coherent: when the response is uniform, the page shows the same OTP-entry step and only diverges if the candidate actually receives (or does not receive) the email.
- Extend backend tests to cover uniform responses for unknown identity, ambiguous identity, inactive candidate, missing email, and SMTP failure after commit.
- Extend frontend tests for the new "no immediate error" login-page behavior.

## Non-goals

- Do not change the candidate token contract, the `X-Candidate-Token` header, or session storage.
- Do not introduce Redis, Celery, or any queue/worker in this change. The first implementation must stay on FastAPI `BackgroundTasks` (in-process).
- Do not change the import-time email validation, the candidate model, the existing rate limiter, the OTP length, the TTL/attempt-limit defaults, or the email delivery modes (`memory` / `smtp`).
- Do not implement CAPTCHA, SSO, or any second factor.
- Do not add a separate "did this candidate really receive the OTP" telemetry pipeline; success remains observable only through the `CandidateLoginChallenge` rows that have a non-null `consumed_at`.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `candidate-access`: The challenge-request endpoint must return uniform responses and must commit the challenge row before triggering email delivery, so lookup and delivery outcomes are not observable to the caller.

## Impact

- Backend service: `request_candidate_login_challenge` in `backend/app/services/candidate_service.py` is the primary change. The route in `backend/app/api/candidates.py` learns to enqueue delivery through FastAPI `BackgroundTasks`.
- Backend tests: `test_candidate_flow_api.py` and any auth-api test that asserts 4xx for unknown/ambiguous/inactive/missing-email cases need to be rewritten to assert 200 with the same envelope, plus negative tests that still reject at the verify step.
- Frontend: `frontend/src/pages/LoginPage.tsx`, `frontend/src/lib/pageCopy.ts`, and any test under `frontend/src/pages/*test*` need to drop the "未找到匹配的考试人员" / "姓名匹配到多名考试人员，请填写员工号" error states from the identity step and let the OTP step explain what to do.
- Operations: a new WARN log line `"candidate_login.unknown_identity"` (or similar) is added for monitoring; no dashboard wiring is required.
- Docs: `docs/api-design.md` and `docs/handoff.md` need to record the uniform-response contract; the `docs/official-exam-uat-checklist.md` needs to add a UAT line for the new behavior.
