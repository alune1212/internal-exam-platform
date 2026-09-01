## Context

See `proposal.md` and the seven delta specs. The current single-backend controlled-LAN platform already has formal runtime profiles, immutable practice details, guarded exam retention, paired backups, macOS release sealing, and two Nginx gateways. The security findings arise where those existing controls are incomplete or applied after unsafe parsing/expansion. The implementation must reuse those boundaries and keep routes thin.

The final implementation review also covered five narrower paths: unbounded candidate answer-save payloads, sparse or inflated XLSX worksheet dimensions, eager practice-catalog reads, credential persistence in non-browser pull-request jobs, and backup freezes stranded by ordinary post-acquisition failures.

## Goals / Non-Goals

**Goals:**

- Close all fifteen original scan paths and the separately identified implementation-review paths at their narrowest shared configuration, parser, service, archive, release, CI, media, or proxy boundary.
- Keep normal development, current exam semantics, candidate isolation, and first-phase operations compatible except for the explicitly selected secret rotation, persistent browser-state purge, bounded practice history, and signed-release gates.
- Leave runnable regression evidence for every negative path and a clean-HEAD full scan.

**Non-Goals:**

- New infrastructure, asynchronous archival, multi-instance rate limiting, a new admin UI for maintenance APIs, or changes to formal exam snapshots/scoring.
- Automatic selection of production/staging Docker subnets or custody of the offline release private key.

## Decisions

### 1. Centralize formal runtime and token validation

`Settings.validate_runtime_profile()` remains the single startup boundary. Database validation moves before the worker return for both formal roles; effective operator, exact four-hour TTL, and canonical 32-byte Base64url token-secret checks apply to formal backends only. Canonical decoding uses the Python standard library and never reports secret material. Development retains its existing placeholders; worker least privilege remains unchanged.

The shared token verifier accepts only bounded ASCII timestamps, and candidate parsing also bounds the positive integer identifier. Invalid forms return the existing unauthenticated result. This is narrower and more complete than catching conversion exceptions in each dependency.

### 2. Make destructive development exceptions explicit

The historical account migration reads the raw environment before DDL. Formal values always require the existing evidence gate. Development requires two explicit disposable acknowledgements plus a constrained PostgreSQL development/test URL. The revision identifier remains unchanged because a later revision cannot protect installations that have not crossed the destructive historical revision.

PostgreSQL migration/concurrency tests share one guard that requires an explicit disposable marker, exact database/user/driver, loopback host, and matching declared port before connection. CI and the disposable local script supply those values; arbitrary `_test` suffixes are insufficient.

### 3. Separate practice all-time state from hot immutable detail

Add one `practice_answer_aggregate` row per candidate/question. Candidate-row locking serializes the detail insert and aggregate update in one transaction; the aggregate stores all-time totals and the latest state selected by `(practiced_at, id)`. The detail table remains immutable but bounded to 5000 hot rows per account. New submissions are rejected at the ceiling rather than performing file I/O or deletion on a candidate request.

Wrong-question listing reads/paginates aggregate rows in SQL, loads only bounded recent detail for the returned question IDs, and returns total/truncated metadata in the existing list envelope. A new additive migration backfills and verifies aggregate rows without deleting detail.

Practice maintenance follows the existing synchronous retention shape through sibling admin operations endpoints. Preview selects details older than 365 days and, for capacity-blocked accounts, enough oldest rows to reach 4000. Archive writes exact JSON and formula-safe XLSX into a checksummed ZIP. Delete reacquires account locks, revalidates row content/fingerprint and a later paired backup, then deletes exact detail IDs while preserving aggregates.

### 4. Reject unsafe XLSX archives before expansion

One standard-library ZIP preflight runs inside the shared workbook parser before `openpyxl`. It validates exact safe names, no encryption/duplicates, required XLSX parts, at most 1000 members, 20 MiB per member, 50 MiB total expansion, and 100:1 compression. Structural errors use a stable 422 domain error; resource bounds use the existing 413 error. Both import entry points inherit the control.

### 5. Upgrade lifecycle archives without changing source JSON values

Exam archives become schema v2 and include every frozen scope identity in JSON and a `冻结名单` sheet. The loader verifies exact ZIP membership, matching inner/outer manifests, member hashes, schema, and current source identity before deletion. V1 artifacts remain readable but cannot authorize deletion.

All workbook row construction passes dynamic strings through the existing formula-escape helper; JSON remains byte-for-byte semantic source data. Practice retention reuses the same artifact and backup validation patterns in a separate service to avoid coupling exam deletion logic to practice selection.

### 6. Authenticate a single final release trust root

`Sign-ReleaseBundle.zsh` runs after Seal from a trusted checkout with an offline RSA-3072 private key. It adds fixed signature metadata to the final manifest, then signs the raw manifest and `SHA256SUMS` bytes with SHA-256, producing exactly two binary sidecars excluded from the payload hash list to avoid a cycle.

The formal host stores only an owner-controlled public key and SPKI SHA-256 fingerprint outside releases. Default verification requires both signatures and a three-way fingerprint match before checksum/payload validation. Build/Seal may use an explicit unsigned-content mode, but Install/Start/Promote/Rollback/Preflight never do and never execute the target bundle's verifier before external verification.

### 7. Trust only exact gateway peers

Nginx overwrites `X-Forwarded-For` with `$remote_addr`. A dedicated gateway network assigns static candidate/operator addresses; Uvicorn trusts exactly those two IPs, not a CIDR or wildcard. Development uses `172.30.0.0/24` with `.2/.3`; E2E uses a separate network. Formal/staging values are required and checked for RFC1918 membership, uniqueness, containment, and non-overlap by preflight. Backend remains unexposed.

### 8. Normalize scanner policy before evaluation

A single severity normalizer trims and canonicalizes the four accepted values and maps npm `moderate` to `MEDIUM`. Explicit invalid values raise `ScanInputError`; pip-audit absence retains the existing conservative `HIGH` fallback. `evaluate()` independently rejects noncanonical findings to prevent future validator bypass.

### 9. Close re-scan findings at existing boundaries

The tracked question-bank XLSX is rebuilt without producer-local OOXML metadata and gains a compact-ZIP/parsed-metadata regression check. The invitation burst guard remains in-process, but validates the exam before allocation, caps keys using the existing limit, and serializes its compound update with a standard-library lock. Exam-retention backup IDs reuse the existing strict backup-name rule and resolve beneath the configured root before validation.

Candidate learning detail responses mint five-minute HMAC playback credentials bound to candidate and video IDs. The playback endpoint rechecks active/published state and contained storage before `FileResponse`; both gateways deny the legacy static path and no longer mount the media volume.

The browser E2E container no longer receives Docker CLI or the host Docker socket because host-side orchestration already provides the required services. The pull-request job is read-only and does not persist checkout credentials. macOS sealing retains a fixed raw scanner-evidence set and invokes trusted evaluator code to recompute the canonical scanner digest before sealing and again from the signed bundle; a report plus self-authored sidecar is insufficient.

### 10. Bound remaining resource and cleanup paths

Exam answer saves validate payload shape and attempt membership before mutation. XLSX import rejects logical worksheet widths before row iteration. Practice catalog reads use stable, bounded pages and the existing candidate limiter. Every pull-request checkout disables credential persistence under a read-only workflow token. Backup finalization catches ordinary post-acquisition failures long enough to release the owned freeze, then re-raises the original error.

## Risks / Trade-offs

- [Strict token-secret validation prevents a new release from starting with the old secret] → Rotate to a compliant secret on the old compatible release during a write-frozen maintenance window, then install the strict signed release; keep the new secret across rollback.
- [Practice detail ceiling can temporarily block a frequent user] → Preview/archive/backup/delete to a 4000-row low-water mark before reopening practice; aggregates preserve all-time behavior.
- [Historical account revision source changes do not affect databases already at head] → Treat this as protection for pending/fresh upgrades and retain restore-only operational guidance for completed destructive migrations.
- [Signed release enforcement can strand an unsigned rollback version] → Revalidate and sign both current and previous before enabling strict install/start gates; do not add a long-lived bypass.
- [Static Docker subnets can conflict with local VPN/Docker networks] → Require operator-selected formal/staging values and block preflight on overlap rather than widening trust.
- [Offset pagination can shift while new practice rows arrive] → Stable `(last_practiced_at DESC, question_id DESC)` ordering and first-phase read-only page UX are accepted; cursor pagination is deferred until measured need.

## Migration Plan

1. Land additive schema, code, tests, OpenSpec, deployment contracts, and signing tools in development.
2. Provision the offline key, install the pinned public key/fingerprint, select non-overlapping formal/staging gateway networks, and sign trusted current/previous releases.
3. Create and validate a paired backup. If the historical account revision is still pending, run its complete maintenance gate.
4. On the old compatible release, rotate sample database/operator credentials if present and rotate to the new canonical token secret. Verify old sessions/OTP credentials fail and new login/OTP succeeds.
5. Install the newly signed release, apply the additive practice aggregate migration, and verify services/gateways.
6. Archive/backup/delete any practice detail already beyond the hot policy; regenerate any source-backed schema-v1 exam archive before future deletion.
7. Run full CI, real scanner evidence, macOS tamper tests, gateway spoof tests, UAT, and a new clean-HEAD repository scan.

Rollback uses only a previously verified signed release and retains the new token secret and additive aggregate table. Destructive account-migration rollback and restoration of archived practice detail use verified backups/archives rather than downgrade or silent data recreation.
