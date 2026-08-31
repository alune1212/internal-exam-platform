## 1. Formal Configuration, Tokens, and Browser Sessions

- [x] 1.1 Enforce formal backend/worker database credentials, effective operator credentials, exact 14400-second admin/candidate TTLs, and a canonical unpadded 43-character Base64url 32-byte `TOKEN_SECRET`; verify focused configuration tests reject blank, sample, malformed, padded, and wrong-length values.
- [x] 1.2 Generate formal token secrets with `secrets.token_bytes(32)` plus unpadded URL-safe Base64 and write them only to the owner-only external formal env; verify `Close-ExamSessions.zsh` syntax and its fixture output shape without printing a live secret.
- [x] 1.3 Harden the shared token parser to accept only bounded ASCII decimal timestamps and positive 32-bit candidate IDs, mapping conversion failures to invalid-token 401 responses; verify Unicode, signed, oversized, and stale token tests.
- [x] 1.4 Remove admin, attempt-session, and attempt-draft recovery from `localStorage`, purge only this application's legacy keys at startup/logout/401, and retain current `sessionStorage`; verify frontend storage tests preserve unrelated keys.

## 2. Destructive Migration and Test Database Isolation

- [x] 2.1 Make the historical account migration fail before DDL for missing/blank/unknown environments, force formal gates regardless of false flags, and require both explicit development disposable flags plus a controlled PostgreSQL target; verify migration guard tests and keep restore-only recovery semantics.
- [x] 2.2 Add one shared PostgreSQL test-database guard requiring the disposable marker, `postgresql+psycopg`, loopback host, user `exam`, exact database `internal_exam_test`, and a matching explicit port before any connection or destructive SQL; verify both PostgreSQL suites reject every mismatch without exposing credentials.
- [x] 2.3 Update local and CI PostgreSQL test entrypoints to inject the disposable marker and explicit ports 55432 and 5432 respectively; verify rendered commands and focused tests use the shared guard.

## 3. Practice History Resource Governance

- [x] 3.1 Add `practice_answer_aggregate` with unique candidate/question rows, all-time counters, latest-answer metadata, constraints, and composite indexes; backfill and validate it in an additive Alembic migration without deleting details, then verify migration/model tests.
- [x] 3.2 In one transaction lock the candidate, enforce a 32-character answer bound and the existing 60-per-60-second account/IP limiter, reject hot histories at 5000 with 409, and update immutable detail plus aggregate; verify concurrency, limit, rollback, and aggregate tests.
- [x] 3.3 Replace in-memory wrong-question aggregation with SQL aggregate pagination and bounded recent-history queries using `limit`, `offset`, and `history_limit`, while preserving the list envelope and adding `history_total`/`history_truncated`; verify response and query-bound tests.
- [x] 3.4 Implement synchronous admin practice-retention preview and deterministic selection for records older than 365 days plus capped accounts reduced to 4000; verify preview fingerprints and selected IDs are stable.
- [x] 3.5 Implement checksummed practice ZIP archives containing raw JSON, formula-safe XLSX, and an internal manifest; verify exact members, digests, raw-value preservation, and spreadsheet escaping.
- [x] 3.6 Implement fail-closed practice deletion that revalidates the preview fingerprint, row contents, archive checksum, candidate locks, and a newer paired backup before deleting only archived IDs while retaining aggregates; verify tamper, concurrency, missing-backup, and successful-delete tests.
- [x] 3.7 Add the three admin practice-retention routes and frontend wrong-question load-more/capacity messaging through existing API modules and design primitives; verify backend route and frontend interaction tests.

## 4. Excel Input and Retention Archives

- [x] 4.1 Preflight XLSX ZIP central directories before `openpyxl` with fixed member, expanded-size, total-size, ratio, encryption, duplicate/path, zero-compressed, and core-part rules; verify 413 limit failures and 422 corrupt/forged failures create no `ImportBatch` and never call `openpyxl`.
- [x] 4.2 Upgrade exam retention payloads, manifests, and workbooks to schema v2 with frozen roster scope/candidate identity fields and a `冻结名单` sheet; verify archive content and counts against current scopes.
- [x] 4.3 Validate exact ZIP members, inner/outer manifests, file digests, schema version, roster count, and current scope fields before deletion; verify schema v1 remains readable but cannot authorize deletion and v2 tampering fails closed.
- [x] 4.4 Reuse `escape_excel_cell` for every dynamic retention workbook string while leaving JSON raw; verify formula-prefix regression cases across titles, roster fields, stems, and answers.

## 5. Scan Gate, Release Authenticity, and Proxy Boundary

- [x] 5.1 Normalize scanner severities to the closed `CRITICAL/HIGH/MEDIUM/LOW` set, map npm `moderate` to `MEDIUM`, retain missing pip-audit severity as `HIGH`, and fail closed in parsing and evaluation; verify empty, unknown, and non-string severity tests.
- [x] 5.2 Add a trusted-checkout macOS signer using offline RSA-3072 SHA-256 PKCS#1 v1.5 detached signatures for final manifest and checksum bytes, with SPKI SHA-256 metadata and non-recursive sidecars; verify signer syntax and deterministic fixture checks.
- [x] 5.3 Make Test/Install/Start/Promote/Rollback verify both signatures against the external owner-only public key and fingerprint before payload checks, and prevent Install from executing an untrusted bundled verifier; verify payload, manifest, checksum, signature, key, and fingerprint tamper tests.
- [x] 5.4 Update the release workflow to `New -> Build -> Scan -> Seal -> Sign -> Test -> Install`, require verifiable current/previous releases, and document external re-signing/key-custody blockers; verify macOS script contract tests without creating a production key.
- [x] 5.5 Overwrite incoming `X-Forwarded-For` with `$remote_addr`, add the dedicated static gateway network while isolating database/worker, and set Uvicorn's proxy allowlist to the two exact gateway IPs; verify Compose/Nginx contract tests and absence of a host backend port.
- [x] 5.6 Fail formal/staging preflight for missing, overlapping, unapproved, or rendered-mismatched gateway networks and keep E2E on a distinct subnet; verify negative preflight cases and forged-XFF rate-limit/audit tests.

## 6. Automated Verification and Operational Acceptance

- [x] 6.1 Run backend format, lint, type, unit, migration, and disposable PostgreSQL gates; record only commands that complete successfully on the implementation HEAD.
- [x] 6.2 Run frontend format, unit, lint, build, and offline gates; record only commands that complete successfully on the implementation HEAD.
- [x] 6.3 Run legacy-contract, strict OpenSpec, Compose render, macOS shell syntax, browser E2E, and capacity gates; distinguish automated passes from unavailable external infrastructure.
- [ ] 6.4 On the same clean HEAD confirm every remote CI job and release security gate using real pip-audit, npm audit, and Trivy evidence; leave this task open until remote evidence exists.
- [ ] 6.5 Complete Mac release signature/tamper/rollback, forged-XFF gateway, credential/token rotation, and practice archive/backup/delete operational drills; leave this task open for any missing external or maintenance-window evidence.
- [ ] 6.6 Run a fresh complete repository Codex Security standard scan with no deferred coverage and close all 15 original finding identities; track any new finding separately and leave this task open until the scan exists.

## 7. Rollback and Scope Invariants

- [x] 7.1 Verify release rollback retains the rotated token secret, additive aggregate table, restore-only account migration, schema-v2-only deletion credential, and mandatory signed-release boundary in code and runbooks.
- [x] 7.2 Verify the diff adds no Redis, Celery, microservices, queue, complex RBAC, LMS, HTTPS redesign, or new runtime dependency, and does not change completed hardening tasks or Windows 12.4/12.5 status.
