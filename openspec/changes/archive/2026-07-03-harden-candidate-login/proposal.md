## Why

Candidate login currently relies on static roster facts: name, phone suffix, and optional employee number. That is acceptable for a lightweight internal scaffold, but strict rollout needs the login flow to verify control of a roster-bound contact channel before issuing a candidate token.

## What Changes

- Replace direct candidate token issuance from name/phone-suffix matching with a two-step email OTP login flow for all exams.
- Use the existing candidate `email` field as the required delivery address for strict candidate login.
- Add a short-lived, single-use login challenge persistence model for email OTP issuance, verification, retry limits, resend behavior, and auditability.
- Keep existing candidate authorization boundaries after login: candidate-facing exam, attempt, practice, and learning APIs remain gated by `X-Candidate-Token` unless a separate session-storage change is approved.
- Update candidate-facing login UI from one-step credential entry to identity lookup plus OTP verification.
- Update candidate and exam-candidate import validation so strict-login rosters cannot silently omit the email needed for login.

## Non-goals

- Do not add SMS OTP, paid SMS provider integration, or voice verification in this change.
- Do not add enterprise SSO/OIDC/SAML, passkeys, MFA enrollment, or a full account-management system.
- Do not add complex RBAC, multi-tenant authorization, LMS features, anti-cheat monitoring, queues, Redis, Celery, or new document import formats.
- Do not change exam snapshot, fixed-paper, scoring, retake, reporting, learning, or practice semantics except where candidate login affects access.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `candidate-access`: Candidate login changes from direct static-field token issuance to mandatory email OTP challenge verification before issuing a candidate token.
- `admin-imports`: Candidate roster imports must validate the email required for strict candidate login and report row-level failures when it is missing or invalid.

## Impact

- Backend API: candidate login endpoints change from one-step login to challenge request and OTP verification; existing candidate-token-gated APIs continue to consume the issued candidate identity.
- Backend persistence: add an Alembic migration and SQLAlchemy model for candidate login challenges.
- Backend services/schemas: add challenge creation, OTP generation/hash/verification, resend/attempt limits, expiration, and email delivery adapter boundaries under existing service/schema patterns.
- Frontend API/UI: update `frontend/src/api/` auth calls and the candidate login page to support the two-step OTP workflow with cooldown, loading, error, and retry states.
- Imports/docs/tests: update candidate import expectations, API docs, database docs, UAT guidance, and focused backend/frontend tests for the new login contract.
