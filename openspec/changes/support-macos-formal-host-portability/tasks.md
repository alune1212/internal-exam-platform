## 1. Cross-Platform Release And Data Contracts

- [x] 1.1 Extend release metadata and evidence with host OS, CPU architecture, Git commit, application version, migration head, and architecture-specific image references without exposing secrets.
- [x] 1.2 Require explicit development, staging, and formal Compose project identities and reject unsafe or ambiguous formal project names in host operations and tests.
- [x] 1.3 Require absolute formal lifecycle, backup, evidence, and second-copy host paths outside the development working tree, with the second copy on a distinct physical device or host and protected by encryption, while preserving development defaults.
- [x] 1.4 Add tests and documentation proving raw Docker Desktop disks, named-volume internals, incomplete archives, and artifacts without `SUCCESS` are not accepted migration inputs.
- [x] 1.5 Preserve the Windows PowerShell adapter and mark its remaining real-host tasks as future Windows acceptance rather than macOS evidence.
- [x] 1.6 Define and test the shared `datasetId`/`hostId`/`writerGeneration` contract and checksummed cutover manifest, including executable `prepare-cutover` and `accept-cutover` preconditions and consumed/stale-manifest rejection.

## 2. macOS Host Layout And Core Commands

- [x] 2.1 Add shared strict zsh helpers for path resolution, command execution, redaction, SHA-256 evidence, dotenv reads/atomic updates, release-state reads, and Docker Compose invocation.
- [x] 2.2 Add macOS host initialization that creates the protected configuration, releases, backups, evidence, diagnostics, and state layout with owner-only permissions.
- [x] 2.3 Add release bundle validation, installation, architecture-aware image build, and current/previous release state management for macOS.
- [x] 2.4 Add idempotent macOS start, stop, and status commands that use the selected immutable release, explicit formal project name, and `--no-build` recovery.
- [x] 2.5 Add disposable macOS staging up/down, evidence capture, separate loopback ports, project-name protection, and safe cleanup without touching formal volumes.
- [x] 2.6 Add guarded macOS formal promotion and same-host version rollback using the previous release plus pre-upgrade paired backup, with explicit typed confirmation of post-backup data loss before restore.
- [x] 2.7 Add macOS `prepare-cutover`, `accept-cutover`, and cross-host rollback commands that stop/prove the entire source or target formal project, fence writer generations, and require the target's latest backup before restoring after target writes.

## 3. macOS Operational Commands

- [x] 3.1 Add macOS paired-backup and encrypted second-copy orchestration that invokes the versioned backend one-shot commands, requires a distinct physical device or host for the second copy, and retains only verified artifacts; formal pre/post-exam, pre-upgrade, and cutover flows fail closed when the second copy is unavailable or unverified.
- [x] 3.2 Add macOS disposable second-copy restore-drill orchestration with migration, count, media, and cleanup evidence.
- [x] 3.3 Add macOS backup-operator enable/disable and guarded close-session commands with exact confirmation, atomic configuration replacement, backend recreation, and audit evidence.
- [x] 3.4 Add bounded macOS diagnostic export with redacted operations state, release metadata, Compose status, bounded logs, archive checksum, and no secret values.
- [x] 3.5 Add macOS formal preflight covering release and image identity, architecture, Docker/Compose, explicitly disabled Resource Saver, configuration permissions, fixed bind/CORS, service/worker health, migration, disk, SMTP, paired backup, independent encrypted second-copy evidence, and browser evidence.
- [x] 3.6 Add explicit host-evidence checks for Docker login startup, Resource Saver disabled state, AC/sleep policy, time synchronization, FileVault, firewall, approved LAN CIDR, effective `pf`/managed-equivalent rule export (for `pf`, `pfctl -s info` and `pfctl -sr`), and the candidate-only port matrix, failing closed when required evidence is absent.
- [x] 3.7 Add cutover evidence checks for `datasetId`, source/target `hostId`, `writerGeneration`, final paired-backup checksums, and whole-project source-stop proof before target exposure.

## 4. Startup Scheduling And Host Safety

- [x] 4.1 Add a LaunchAgent bootstrap template that waits for Docker Desktop and idempotently restores only the selected formal release without building, promoting, or approving an exam.
- [x] 4.2 Add a LaunchAgent opportunity-backup template that invokes the existing skip-aware backup flow without interrupting in-progress exams.
- [x] 4.3 Add install/uninstall commands for the mandatory formal bootstrap LaunchAgent under the current signed-in designated host account, with validated labels, paths, permissions, and bounded log destinations; a new OS account is not required.
- [x] 4.4 Add zsh syntax, temporary-layout, checksum/redaction, project-boundary, and `plutil` tests for macOS commands and LaunchAgent templates.
- [ ] 4.5 Perform real-Mac LaunchAgent load/status acceptance: `launchctl bootstrap`/`print`, Docker-unavailable bounded retry, successful retry after Docker readiness, and concurrent-invocation lock/no-duplicate Compose evidence.

## 5. Candidate macOS Browser Support

- [x] 5.1 Extend browser detection types and rules to support current macOS Chrome using the existing Chromium minimum and current macOS Safari using a documented minimum.
- [x] 5.2 Preserve blocking behavior for embedded, unrecognized, and obsolete browsers and update the visible supported-browser explanation.
- [x] 5.3 Add focused frontend tests for supported/obsolete macOS Chrome and Safari plus unchanged Windows, Android, iOS, and embedded behavior.

## 6. Compose, CI, And Automated Gates

- [x] 6.1 Add deployment tests for explicit project identities, macOS absolute formal directories, split ingress, secret isolation, bounded logging, and architecture-aware release evidence.
- [x] 6.2 Add CI checks for `zsh -n`, LaunchAgent `plutil` validation, macOS operations contract tests, and preservation of PowerShell syntax coverage.
- [x] 6.3 Verify every pinned final-image base reference supports the selected macOS ARM64 build or has an explicit architecture-specific disposition without weakening vulnerability gates.
- [x] 6.4 Run backend format, lint, type checks, targeted/full PostgreSQL tests, and operational security/redaction tests.
- [x] 6.5 Run frontend format, unit/component tests, lint, production build, accessibility, and offline-runtime checks.
- [x] 6.6 Run OpenSpec strict validation, Compose render/exposure checks, shell/plist checks, final-image scans, browser E2E, and the 100-client capacity gate where the local Docker daemon is available.
- [ ] 6.7 Run real second-device and unapproved-CIDR negative network gates proving only approved-CIDR candidate `8080` is reachable, while `8081`, `5432`, `5173`, backend `8000`, worker, admin/docs/OpenAPI, and direct services remain unreachable.

## 7. Documentation And Operator Guidance

- [x] 7.1 Add a macOS formal-host guide covering the current signed-in designated host account (without requiring a new OS account), Docker Desktop login startup/resources, explicitly disabled Resource Saver, mandatory formal LaunchAgent, FileVault, firewall/`pf`, approved CIDR, fixed IP, AC/sleep, time, UPS, updates, and manual post-reboot approval.
- [x] 7.2 Add a macOS operations runbook for versioned install, staging, promotion, status, preflight, backup, second copy, restore drill, diagnostics, rollback, and session closure.
- [x] 7.3 Update README, requirements, HTTP exception, exam-day guide, capacity guidance, UAT checklist, and handoff so macOS is the current formal host and Windows remains a future migration target.
- [x] 7.4 Document the portable backup-only Mac-to-Windows cutover, native ARM64/AMD64 image builds, fixed-IP/CORS transition, `datasetId`/`hostId`/`writerGeneration` manifest, whole-source-project stop, exactly-one-writer rule, same-host data-loss confirmation, and cross-host rollback before/after target writes.
- [x] 7.5 Document that macOS acceptance evidence does not satisfy future Windows host acceptance and that the existing Windows 12.4/12.5 tasks remain pending until a real Windows migration.

## 8. Real macOS Staging And Formal Acceptance

- [ ] 8.1 Configure the current Mac for Docker login startup, explicitly disabled Resource Saver, protected host paths, fixed private IP, firewall/approved LAN, FileVault, AC/no-sleep, time synchronization, and formal secrets without committing sensitive values; record the 24x7 best-effort/non-HA boundary and independent encrypted second-copy location.
- [ ] 8.2 Build and start the disposable native ARM64 macOS staging project, migrate to head, and prove route separation, approved-CIDR/pf port negatives, Docker/service restart recovery, real SMTP, daily opportunity backup degraded/skipped handling, formal pre/post backup with independent encrypted second-copy restore, diagnostics, security, browser E2E, capacity, and checksummed evidence.
- [ ] 8.3 Install/enable and real-test the mandatory formal LaunchAgent, create and verify the formal pre-promotion paired backup and independent encrypted second copy (failing closed if unavailable), run `prepare-cutover` with whole-project source shutdown evidence, promote only tested images via `accept-cutover`, run desktop and phone UAT, perform a host-restart retry/lock check, close sessions, and retain the final evidence bundle.
- [x] 8.4 Perform an adversarial review of secret/PII redaction, project and volume isolation, raw-data migration rejection, single-writer cutover, rollback feasibility, HTTP exception accuracy, and Mac/Windows evidence separation.
