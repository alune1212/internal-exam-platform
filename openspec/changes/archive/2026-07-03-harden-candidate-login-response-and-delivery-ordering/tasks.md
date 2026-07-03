## 1. Service Refactor — Commit Before Delivery

- [ ] 1.1 Refactor `request_candidate_login_challenge` in `backend/app/services/candidate_service.py` to build and `db.commit()` the `CandidateLoginChallenge` row before any network call.
- [ ] 1.2 Funnel all non-real-candidate lookup outcomes (no match, ambiguous, inactive, missing email) into a single branch that persists a `CandidateLoginChallenge` against a sentinel candidate id and skips the email send.
- [ ] 1.3 Stop raising `CandidateLoginError` (404) and `CandidateLoginAmbiguousError` (409) from the challenge request path. The request path must always return the same `CandidateLoginChallengeResponse` envelope.
- [ ] 1.4 Emit a single structured WARN log line `event=candidate_login.unknown_identity` with hashed identity and request IP hash, rate-limited through the existing public token limiter.

## 2. Route Wiring — Background Delivery

- [ ] 2.1 Update the candidate login route in `backend/app/api/candidates.py` to accept `BackgroundTasks` and enqueue `send_candidate_login_otp` after the service returns.
- [ ] 2.2 Ensure the background task swallows and logs SMTP errors so a delivery failure does not surface to the caller or roll back the persisted challenge row.
- [ ] 2.3 Keep the route file thin — no business logic in the route, no try/except for SMTP.

## 3. Sentinel Candidate Setup

- [ ] 3.1 Add a small migration or fixture that ensures a sentinel candidate row exists with a stable id (or a small pool of ids) and `email IS NULL` / `status = 'inactive'`, never scoped to any exam.
- [ ] 3.2 Make the sentinel id accessible to the service via a config field (e.g., `CANDIDATE_LOGIN_SENTINEL_CANDIDATE_IDS=1`) with a safe development default.
- [ ] 3.3 Document the sentinel row in the database design doc so operators do not delete it.

## 4. Backend Test Rewrite

- [ ] 4.1 Update existing tests in `test_candidate_flow_api.py` that asserted 404/409 from the challenge request to assert 200 with the uniform envelope.
- [ ] 4.2 Add tests asserting the verify step still rejects OTPs that point at the sentinel candidate id.
- [ ] 4.3 Add tests asserting the `CandidateLoginChallenge` row count is the same whether or not a real candidate was found (proving observation equality from the DB side).
- [ ] 4.4 Add tests asserting an SMTP failure during background delivery does not roll back the challenge row and does not produce a 5xx response.
- [ ] 4.5 Add tests asserting the public token rate limiter still caps challenge requests and the WARN log line is emitted with hashed identity.

## 5. Frontend Copy and State Machine

- [ ] 5.1 Update `frontend/src/pages/LoginPage.tsx` to remove the identity-step error branches (no more 404/409 cards) and always transition to the OTP step on 200.
- [ ] 5.2 Update `frontend/src/lib/pageCopy.ts` to add the OTP-step explainer copy (delivery delay, spam folder, resend cooldown, admin contact) without leaking "this email is not in our roster".
- [ ] 5.3 Update `frontend/src/pages/P0Pages.test.tsx` and `frontend/src/pages/LearningPages.test.tsx` to assert the new identity-step → OTP-step transition on a 200 response and the absence of the old error branches.
- [ ] 5.4 Update `frontend/src/components/layout/__tests__/CandidateLayout.test.tsx` if the layout renders any of the removed error strings.

## 6. Documentation and Operational Guidance

- [ ] 6.1 Update `docs/api-design.md` to describe the uniform-response contract and the post-commit delivery ordering.
- [ ] 6.2 Update `docs/database-design.md` to document the sentinel candidate row(s) and the `event=candidate_login.unknown_identity` audit signal.
- [ ] 6.3 Update `docs/handoff.md` to record the change as a candidate-login follow-up hardening and link back to the original `2026-07-03-harden-candidate-login` archive.
- [ ] 6.4 Update `docs/official-exam-uat-checklist.md` to add a UAT line for the new "OTP step appears even when the candidate identity does not match" behavior.
- [ ] 6.5 Update `README.md` to drop any mention of 404/409 from the candidate login flow description.

## 7. Verification

- [ ] 7.1 Backend: `cd backend && uv run ruff format . --check && uv run ruff check . && uv run ty check && uv run pytest`.
- [ ] 7.2 Frontend: `cd frontend && npm run format:check && npm test -- --run && npm run lint && npm run build`.
- [ ] 7.3 Smoke test through `http://localhost:8080/login`:
  - Unknown identity → OTP step appears, no email is sent, WARN log line is emitted.
  - Ambiguous identity (multiple candidates) → OTP step appears, no email is sent, WARN log line is emitted.
  - Inactive candidate → OTP step appears, no email is sent, WARN log line is emitted.
  - Valid candidate → OTP step appears, email is delivered, verify still issues a candidate token.
  - Rate limiter still blocks excessive requests with the same response shape.
- [ ] 7.4 Confirm no regression in exam, attempt, practice, or learning flows that consume `X-Candidate-Token`.

## 8. Archive

- [ ] 8.1 Move the change directory from `openspec/changes/2026-07-03-harden-candidate-login-response-and-delivery-ordering/` to `openspec/changes/archive/2026-07-03-harden-candidate-login-response-and-delivery-ordering/` after all tasks are complete and verification passes.
