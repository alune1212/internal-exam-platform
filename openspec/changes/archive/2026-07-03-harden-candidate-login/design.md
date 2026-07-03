## Context

Candidate login currently authenticates an active roster record with static facts: `name`, `phone_suffix`, and optional `employee_no`. After a match, the backend issues the existing signed candidate token and candidate-facing exam, attempt, practice, and learning APIs continue to authorize through `X-Candidate-Token`.

Strict rollout requires a stronger first authentication step without expanding the first-phase project into SMS, SSO, passkeys, complex account management, or anti-cheat. The existing `candidate.email` field gives the project a practical roster-bound contact channel that can be verified through a short-lived OTP challenge.

The change touches backend API shape, persistence, email delivery, import validation, frontend login UX, docs, and tests. It does not alter exam paper generation, attempt snapshots, scoring, reports, learning progress, retakes, or candidate-token-gated authorization after login.

## Goals / Non-Goals

**Goals:**

- Require email OTP verification before issuing any candidate token.
- Use `name + email + optional employee_no` as the strict-login candidate lookup inputs.
- Persist login challenges so OTPs are short-lived, single-use, retry-limited, resend-safe, and auditable.
- Require usable roster email data for candidates who can be imported into strict-login exams.
- Keep route files thin, put business logic in services, and use Pydantic schemas for all request/response shapes.
- Preserve the existing `X-Candidate-Token` contract for candidate-facing APIs unless a later change migrates session storage.

**Non-Goals:**

- No SMS, voice OTP, paid messaging provider, OIDC/SAML SSO, passkeys, MFA enrollment, or password accounts.
- No Redis, Celery, queues, distributed challenge storage, complex RBAC, or multi-tenant authorization.
- No full session-storage migration to cookies in this change; only document and isolate the current token issuance boundary.
- No change to exam delivery, scoring, reports, practice answer privacy, video learning semantics, or admin authentication.

## Decisions

### Decision: Use email OTP instead of magic link for the first strict flow

The candidate enters identity fields, receives an email OTP, and enters the code on the login page. A successful verification consumes the challenge and returns the existing candidate token response shape.

Alternatives considered:

- Magic link: lower friction, but often opens on a different device/browser than the exam page and complicates local/Nginx URL handling.
- SMS OTP: familiar, but requires a paid or enterprise SMS service, template approval, operational monitoring, and has known SIM/PSTN risks.
- Enterprise SSO: best long-term employee identity source, but outside the current lightweight scope and dependent on an organization IdP.

Rationale: OTP keeps the browser workflow explicit and works with the current SPA login surface while avoiding SMS procurement.

### Decision: Lookup candidates by `name + email + optional employee_no`

The strict challenge request matches active candidates by normalized name and roster email. If `employee_no` is supplied, it must also match. `phone_suffix` is no longer sufficient for strict login.

Alternatives considered:

- Keep `phone_suffix` as a first factor: simple but still relies on low-entropy static data.
- Lookup by employee number only: stronger uniqueness, but the project still supports candidates without employee numbers.
- Lookup by stored email only: convenient, but easier to mistarget shared or stale email records without name confirmation.

Rationale: `name + email` supports existing no-employee-number candidates, while `employee_no` remains the disambiguation field already used by the platform.

### Decision: Add `candidate_login_challenge` persistence

The table stores challenge metadata and a hash of the OTP, not the plaintext OTP. Suggested fields:

- `id`
- `candidate_id`
- `delivery_channel`
- `otp_hash`
- `expires_at`
- `consumed_at`
- `attempt_count`
- `request_ip_hash`
- `created_at`
- `updated_at`

The service creates one active challenge per candidate login request. Resend creates a new OTP and invalidates any previous unconsumed challenge for the same candidate. Verification rejects expired, consumed, or attempt-exhausted challenges before issuing a token.

Alternatives considered:

- Stateless signed OTP token: less schema work, but weaker auditability and harder resend/attempt controls.
- In-memory challenge storage: simple, but breaks across backend restarts and multiple processes.
- Redis-backed challenges: operationally strong, but violates the current no-Redis boundary.

Rationale: PostgreSQL-backed challenges match the project persistence model and keep strict-login controls inspectable.

### Decision: Reuse lightweight public rate limiting plus per-challenge attempt limits

The existing public token rate limiter should protect challenge request and verification endpoints by IP and normalized identifier. The challenge row also tracks verification attempts and locks out a challenge after a small fixed number of failures.

Alternatives considered:

- Account lockout on the candidate record: stronger against guessing, but can be abused to deny exam access.
- CAPTCHA: adds friction and external dependency without replacing OTP controls.

Rationale: request throttling plus per-challenge limits reduces OTP guessing while avoiding durable candidate lockouts.

### Decision: Introduce an email delivery adapter with safe environment behavior

The service boundary should support a test/fake adapter and an SMTP adapter. Development can use a local/dev mode that exposes delivery through controlled logs or tests, but production must not log OTP values and must require configured SMTP settings before strict login is usable.

Alternatives considered:

- Direct SMTP calls inside the candidate service: faster but couples auth logic to delivery mechanics.
- Third-party transactional email SDK: useful later, but an unnecessary dependency for the first strict implementation.

Rationale: an adapter keeps tests deterministic and leaves room for a future provider without changing login semantics.

### Decision: Validate roster email at import boundaries

New candidate imports must include a valid email. Exam-candidate imports must ensure every scoped candidate has a valid email. If an existing candidate lacks email, a valid email in the exam-candidate row may backfill it. If an existing candidate already has a different email, the row fails instead of silently changing the login destination.

Alternatives considered:

- Enforce `candidate.email NOT NULL` immediately: risky for existing data and local fixtures.
- Ignore email in import and fail only at login: easier but creates late exam-day failures.
- Always overwrite existing email during import: convenient but unsafe for identity delivery.

Rationale: import-time validation catches missing login prerequisites early while avoiding accidental email reassignment.

### Decision: Keep issued candidate tokens unchanged for this change

After OTP verification, the backend returns the same signed candidate token contract currently used by candidate APIs. Session storage remains a separate hardening topic.

Alternatives considered:

- Migrate immediately to `HttpOnly; Secure; SameSite` cookies: stronger token confidentiality, but requires CSRF handling and changes every candidate API call.
- Add refresh tokens: unnecessary for an exam workflow with bounded session TTL.

Rationale: separating login assurance from session transport keeps the change implementable and reduces regression risk across exam delivery.

## Risks / Trade-offs

- [Email delivery can fail or be delayed] -> Surface resend cooldown and clear retry states; keep delivery adapter testable; document SMTP setup and operational checks.
- [OTP brute force] -> Store only OTP hashes, set short TTL, single-use consumption, strict attempt limits, and request throttling by IP plus identifier.
- [User enumeration through login responses] -> Use neutral responses for challenge request outcomes and avoid returning full email addresses before verification.
- [Existing candidates may lack email] -> Validate future imports, add migration/UAT checks for missing emails, and fail strict login without issuing tokens when email is absent.
- [Shared or stale email addresses can misroute OTP] -> Match both name and email, require employee number when provided, reject conflicting import email updates, and expose roster cleanup failures early.
- [XSS can still read `sessionStorage` token] -> Keep this risk documented; do not expand the current change into cookie migration unless separately approved.
- [Exam-day friction increases] -> Use a two-step UI with resend cooldown, focused error copy, and tests for mobile/desktop login flow.

## Migration Plan

1. Add the challenge table with nullable-independent migration so existing candidates and attempts remain valid.
2. Add email delivery settings and a deterministic test adapter before wiring production SMTP.
3. Update candidate login API to expose challenge request and OTP verification; keep legacy direct-token behavior removed or disabled for strict login.
4. Update candidate and exam-candidate import validation to require usable email data for future rosters and to prevent conflicting email overwrites.
5. Update frontend login flow and copy to guide users through identity entry and OTP verification.
6. Update docs and UAT checklist so operators know strict login requires candidate emails and SMTP configuration.
7. Before production enablement, run a data check for active candidates without valid email and backfill or exclude them from exam scopes.

Rollback strategy:

- Database rollback can drop the challenge table if no strict-login traffic depends on it.
- Application rollback must restore the previous one-step login only if the security decision permits it; otherwise keep the old build unavailable and fix SMTP/data issues forward.

## Open Questions

- What SMTP service will production use, and what sender address should be approved?
- Should OTP length be fixed at 6 digits for usability, or configurable with a stronger default?
- Should challenge request responses expose a masked email after a successful lookup, or stay fully neutral to reduce enumeration risk?
