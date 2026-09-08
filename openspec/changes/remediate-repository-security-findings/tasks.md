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
- [x] 3.2 In one transaction lock the candidate, enforce a 32-character answer bound and the existing 60-per-60-second authenticated-account limiter, reject hot histories at 5000 with 409, and update immutable detail plus aggregate; verify concurrency, limit, rollback, and aggregate tests.
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
- [x] 5.7 Remove local OOXML producer metadata from the tracked question-bank fixture, validate exams before bounded/atomic invitation-limiter allocation, and constrain exam-retention backup IDs to the configured root; verify metadata, concurrency, eviction, traversal, and symlink regressions.
- [x] 5.8 Replace public learning-media aliases with five-minute candidate/video-bound playback credentials that recheck active/published state and contained storage; verify Range playback, tamper/expiry, lifecycle revocation, legacy-path denial, and removal of gateway media mounts.
- [x] 5.9 Remove Docker CLI and the host Docker socket from PR-controlled browser E2E, restrict the job to read-only contents, and disable checkout credential persistence; verify deployment contracts and the browser gate.
- [x] 5.10 Bind macOS sealing and verification to an exact retained raw scanner-evidence set whose canonical digest is recomputed by trusted evaluator code; verify fabricated reports, missing/extra/tampered inputs, and valid evaluator output.
- [x] 5.11 Bound candidate exam answer-save payloads by answer count, answer length, question identity, duplicate IDs, and revision range before any mutation; verify malformed, oversized, duplicate, and unknown-question requests leave attempts unchanged.
- [x] 5.12 Reject XLSX worksheets with sparse or inflated logical dimensions before row iteration, while retaining the existing ZIP and row bounds; verify wide-dimension input returns 413 without invoking iteration or creating an import batch.
- [x] 5.13 Paginate active practice-catalog reads with a maximum page size and apply the existing candidate token rate limit; verify stable offsets, bounded SQL loading, and rate-limit responses.
- [x] 5.14 Make every pull-request workflow checkout read-only by disabling credential persistence and constraining the workflow token to `contents: read`; verify all checkout steps satisfy the contract.
- [x] 5.15 Release the acquired backup freeze after any ordinary post-acquisition failure, preserve the original exception, and keep successful backup/evidence semantics unchanged; verify a generic failure cannot strand the lock.
- [x] 5.16 `[64dd55a5/public-rate-limit-rejection-keyspace-growth]` Enforce the public-token limiter key cap before rejected requests allocate state; verify unique rejected identifiers never grow retained buckets beyond the configured maximum.
- [x] 5.17 `[64dd55a5/candidate-write-lock-wait-before-rate-limit]` Apply the existing candidate limiter before advisory or row locks on every candidate mutation and avoid row locks for read-only attempt retrieval; verify exhausted quotas return before lock acquisition.
- [x] 5.18 `[64dd55a5/learning-progress-unbounded-watched-intervals]` Cap normalized watched intervals, reject over-cap progress before mutation, and rate-limit candidate progress updates; verify unchanged rows on overflow and 429 responses on repeated requests.
- [x] 5.19 `[64dd55a5/candidate-learning-catalog-unbounded-read]` Add stable candidate learning-catalog pagination with `limit <= 100`, bounded offset, and the existing candidate limiter; verify only one bounded page is loaded and the frontend can load more.
- [x] 5.20 `[64dd55a5/practice-wrong-offset-unbounded]` Bound wrong-practice offsets at the route and service boundaries and apply the candidate limiter before SQL pagination; verify oversized offsets and repeated requests fail before the query.
- [x] 5.21 `[64dd55a5/retention-operation-unbounded-id-selection]` Cap exam and practice-retention target-ID lists at one shared maximum and repeat the guard in direct service normalization; verify over-limit selections fail before sorting, queries, or archive construction.
- [x] 5.22 `[64dd55a5/background-invitation-write-freeze-bypass]` Reacquire the shared backup/writer guard in each background invitation delivery session; verify freeze conflicts roll back delivery state while retaining the claim for retry.
- [x] 5.23 `[64dd55a5/legacy-backup-command-without-freeze]` Remove or block the unfrozen legacy paired-backup command and require all paired backups to use the guarded `run_paired_backup`/`container-backup` path; verify no dump or media archive starts without the write freeze.
- [x] 5.24 `[64dd55a5/macos-bundled-lifecycle-spoofable-trust-marker]` Eliminate environment-only trust markers from bundled macOS lifecycle entrypoints and verify the external owner-controlled runtime and exact release before sourcing bundle code; verify forged markers fail before any bundled script executes.
- [x] 5.25 Restore one trusted-checkout generation-1 formal-writer `Prepare`/`Activate` path that remains pending until exact staging, backup, restore, preflight, browser, privileged-host, release, and writer-fence evidence is bound; verify incomplete or interrupted activation stays fail closed and resumable.
- [x] 5.26 Generate `staging.env` explicitly from protected formal configuration, force disposable loopback/network values plus real SMTP and no fixed OTP, and reject empty, incomplete, linked, or shell-overridden staging inputs before Docker.
- [x] 5.27 Add a runnable fresh-root regression that proves preparation remains private, missing activation evidence fails, and a complete generation-1 activation produces the terminal/lineage state required by the public-start guard.

- [x] 5.28 Refresh OS security packages on every native release build by disabling stale Docker build-layer reuse; verify real scanner evidence and retain immutable per-candidate image identities.
- [x] 5.29 Generate a distinct random staging `TOKEN_SECRET` and reject missing formal keys or shared signing keys before Docker; verify generated-key secrecy, unambiguous dotenv syntax, and cross-environment rejection for candidate, admin, and playback tokens without changing the token protocol.
- [x] 5.30 Serialize the in-process public limiter's prune, quota check, append, and eviction with one standard-library lock; verify concurrent admission and key churn without raising quotas or changing persisted OTP enforcement.
- [x] 5.31 Check candidate exam scope before disclosing exam state on start; verify missing and unassigned IDs share a 404 while assigned lifecycle errors, inactive-account rejection, and read-only recovery remain intact.
- [x] 5.32 Reject XLSX DOCTYPE declarations with the standard-library parser after ZIP bounds and before openpyxl; cover UTF-16 and extensionless XML without rejecting legitimate binary media or adding a dependency.

## 6. Automated Verification and Operational Acceptance

- [x] 6.1 Run backend format, lint, type, unit, migration, and disposable PostgreSQL gates; record only commands that complete successfully on the implementation HEAD.
- [x] 6.2 Run frontend format, unit, lint, build, and offline gates; record only commands that complete successfully on the implementation HEAD.
- [x] 6.3 Run legacy-contract, strict OpenSpec, Compose render, macOS shell syntax, browser E2E, and capacity gates; distinguish automated passes from unavailable external infrastructure.
- [ ] 6.4 On the same clean HEAD confirm every remote CI job and release security gate using real pip-audit, npm audit, and Trivy evidence; leave this task open until remote evidence exists.
- [ ] 6.5 Complete Mac release signature/tamper/rollback, forged-XFF gateway, credential/token rotation, and practice archive/backup/delete operational drills; leave this task open for any missing external or maintenance-window evidence.
- [ ] 6.6 Run a fresh complete repository Codex Security standard scan with no deferred coverage, close all 15 original finding identities, and verify every separately tracked implementation-review finding is closed; leave this task open until the final clean scan exists.

## 7. Rollback and Scope Invariants

- [x] 7.1 Verify release rollback retains the rotated token secret, additive aggregate table, restore-only account migration, schema-v2-only deletion credential, and mandatory signed-release boundary in code and runbooks.
- [x] 7.2 Verify the diff adds no Redis, Celery, microservices, queue, complex RBAC, LMS, HTTPS redesign, or new runtime dependency, and does not change completed hardening tasks or Windows 12.4/12.5 status.
