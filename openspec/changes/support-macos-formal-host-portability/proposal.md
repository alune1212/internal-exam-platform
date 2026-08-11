## Why

The platform is now intended to run formally on the current Apple Silicon Mac instead of waiting for a dedicated Windows host, while retaining a safe future path to Docker Desktop + WSL2. The current signed-in macOS login is the designated formal-host account; this change does not require creating another OS account. The container runtime is already largely portable, but formal host operations, release evidence, backup orchestration, browser support, and acceptance criteria were Windows-specific and still need explicit macOS contracts before macOS readiness can be claimed.

## What Changes

- Make macOS Docker Desktop + Docker Compose the current first-phase formal single-host target, with a 24x7 best-effort (not highly available or unattended) service boundary, a protected host layout, thin zsh operations, LaunchAgent recovery, host preflight, fixed-LAN exposure, diagnostics, staging, promotion, backup, restore, rollback, and session closure. Serious host, disk, power, Docker, or office-network failure may pause or reschedule an exam.
- Introduce a platform-neutral release and data-transfer contract: the same Git commit and checksummed release inputs produce architecture-specific images, while PostgreSQL/media migration uses verified paired backups and an independent encrypted second storage on a distinct physical device or host rather than raw Docker volumes or Docker Desktop VM disks.
- Preserve the existing Windows PowerShell adapter as a future Docker Desktop + WSL2 migration target; require native Windows staging and UAT before Windows can become the active formal writer.
- Add a cutover fence for one formal dataset: every manifest carries an immutable `datasetId`, source/target `hostId`, monotonic `writerGeneration`, release identity, backup identity/checksums, and source-stopped evidence. Executable `prepare-cutover` and `accept-cutover` operations must stop the entire source formal project before a target can accept writes.
- Define the first macOS formal writer as an explicit generation-1 two-stage commissioning flow: `Prepare --empty-dataset` reserves an installed release, fresh dataset/host identity and private volumes; schemaVersion-2 staging and private maintenance browser smoke are accepted before `Activate` owns the exact writer fence, creates the final paired backup/second copy, runs isolated restore and target-maintenance preflight, persists crash-resume barriers, releases the fence, writes terminal evidence, and only then starts the public project. Missing real external evidence remains blocked.
- Require an explicit Compose project identity and immutable release directory for development, staging, and formal instances so the current development working tree cannot silently mutate or replace formal data.
- Make the formal Mac bootstrap LaunchAgent mandatory for an accepted host. Its real-host load/status acceptance must prove `launchctl bootstrap`/`print` (the modern `launchctl` load/status path), bounded retry after Docker failure, and an execution lock that prevents duplicate Compose recovery.
- Add macOS host checks for Docker readiness and login startup, explicitly disabled Docker Desktop Resource Saver, AC power and sleep policy, FileVault/firewall evidence, fixed private IP, exact CORS, approved LAN CIDR/pf (or managed equivalent) rules, explicit port negative tests, disk reserve, configuration permissions, split ingress, real SMTP, backup state, release checksums, and service health.
- Add current macOS Chrome and Safari to the supported desktop-browser contract with the same minimum-version, embedded-browser, offline-asset, responsive, and accessibility gates as the existing client set.
- Add CI/static coverage for macOS scripts and LaunchAgent templates, architecture-aware release manifests, and host-neutral contracts without introducing a private registry or new runtime service.
- Keep the accepted shared-office-LAN HTTP exception, four-hour sessions, loopback-only administration, SMTP fail-closed behavior, paired backups, independent encrypted second-copy protection, manual exam approval, single-host 24x7 best-effort availability, and pause/reschedule failure boundary unchanged. Formal pre-exam, post-exam, pre-upgrade, and cutover backup/second-copy gates fail closed when the second copy is unavailable or unverified; daily opportunistic backup may record skipped/degraded status without claiming formal backup success.

Non-goals:

- No HTTPS/domain/CA project, network segmentation, automatic failover, multi-host active-active operation, Kubernetes, Redis, queues, microservices, complex RBAC, LMS expansion, or full proctoring.
- No automatic host login, unattended release promotion, automatic destructive restore, raw Docker volume copying, simultaneous Mac and Windows formal writers, or mandatory creation of a new macOS OS account.
- No private image registry in the first phase; each target architecture builds and validates images from the same checksummed release inputs.

## Capabilities

### New Capabilities

- `macos-deployment-operations`: Defines the current macOS Docker Desktop formal host, protected layout, zsh/LaunchAgent operations, preflight, staging, release recovery, diagnostics, and best-effort startup boundary.
- `formal-host-portability`: Defines architecture-aware releases, platform-neutral evidence and paired-backup transfer, exactly-one-active-writer migration, and future Windows cutover/rollback rules.

### Modified Capabilities

- `internal-deployment-readiness`: Makes readiness evidence specific to the selected formal host and adds macOS staging, recovery, network, backup/restore, SMTP, capacity, and client UAT gates without reusing evidence from another platform.
- `frontend-page-experience`: Adds supported current macOS Chrome and Safari desktop clients and preserves the existing embedded/legacy browser block and offline-runtime requirements.

## OpenSpec ownership and archive order

There are three active change directories in this checkout. `harden-internal-deployment-readiness` is a completed baseline (all tasks are checked) but is intentionally not auto-archived in this round; its generic readiness spec must not override the host-specific contracts below. `support-macos-formal-host-portability` owns the current selected macOS formal-host contract, the shared dataset/writer/cutover protocol, and the evidence that can later make macOS ready as the active first-phase host. `stabilize-windows-internal-exam-platform` owns the implemented application hardening and future Windows adapter; its remaining 12.4/12.5 tasks are native AMD64 Mac-to-Windows cutover acceptance and remain pending while Mac is the selected source. Archive these changes separately and preserve capability ownership: leave `harden-internal-deployment-readiness` active for this round, archive `support-macos-formal-host-portability` only after real Mac acceptance, and archive `stabilize-windows-internal-exam-platform` only after real Windows staging, cutover, UAT, and evidence. No change may be archived from cross-platform, local-only, or another host's evidence.

## Impact

- New `ops/macos/` scripts and mandatory formal LaunchAgent templates; existing `ops/windows/` remains supported and tested.
- Shared operational commands under `backend/app/ops/`, architecture-aware release evidence, Compose project/host-directory contracts, environment examples, and CI checks.
- Browser detection/tests for macOS Chrome and Safari.
- README and host, operations, UAT, backup/recovery, HTTP-exception, exam-day, and handoff documentation.
- The existing `stabilize-windows-internal-exam-platform` change remains the future real-Windows acceptance track; its final Windows staging/promotion tasks are not satisfied by macOS evidence.
