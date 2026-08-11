## Context

The container topology, split candidate/operator ingress, application readiness, paired backup implementation, security gates, and Windows PowerShell adapter already exist. The current Mac is Apple Silicon with Docker Desktop installed, but formal operations are Windows-only, the local Docker daemon is not configured for login startup, and the development environment is not a safe formal deployment root. The current signed-in macOS login is the designated host account; creating a second dedicated OS account is not a prerequisite. See `proposal.md` for the target change.

The deployment remains one Mac host for at most 50 concurrent candidates, with a 100-client release gate and a 24x7 best-effort service boundary. It is not highly available, does not promise unattended operator response, and serious host, disk, power, Docker, or office-network failure may pause or reschedule an exam. It continues to use shared-office-LAN HTTP as an explicit exception.

## Goals / Non-Goals

**Goals:**

- Make the current Mac a reproducible formal Docker Desktop host without installing application runtimes on the host.
- Share release identity, data transfer, operational evidence, Compose topology, and application-specific operations across macOS and Windows.
- Keep host adapters thin and retain the completed Windows PowerShell work for future migration.
- Prevent development/formal volume confusion and concurrent Mac/Windows formal writers.
- Produce host-specific evidence before claiming readiness.

**Non-Goals:**

- A platform-management framework, private registry, Kubernetes, remote orchestration, automatic promotion, active-active replication, failover, TLS, or a new monitoring service.
- Copying Docker Desktop disks or named-volume internals between architectures.
- Replacing existing snapshot, scoring, authentication, retention, backup, or incident semantics.

## Decisions

### 1. Add a Mac change while retaining the Windows acceptance track

There are three active change directories. `harden-internal-deployment-readiness` is a completed baseline but is intentionally not auto-archived in this round; its generic readiness spec is historical and must not override the host-specific contracts in this change or the Windows change. `support-macos-formal-host-portability` owns the current selected Mac formal target, the shared dataset/writer/cutover contract, and current-host evidence. The existing `stabilize-windows-internal-exam-platform` change owns the implemented application hardening and future Windows adapter; its final Windows tasks are future native AMD64 Mac-to-Windows cutover acceptance and cannot be completed with Mac evidence. Archive the changes separately: leave harden active for this round, archive this Mac change only after real Mac acceptance is complete, and archive the Windows change only after real Windows staging/cutover/UAT/evidence pass. This retains implemented PowerShell assets and avoids falsely archiving Windows readiness or overwriting another change's capability ownership.

Alternative: rewrite and rename the 95/97 Windows change. Rejected because it would obscure which platform produced final evidence and make the future Windows acceptance history ambiguous.

### 2. Keep application operations in containers and implement thin host adapters

Backup, restore validation, SMTP checks, operational locks, audit recording, and lifecycle logic continue to run from the pinned backend image. `ops/macos/` uses `/bin/zsh` only to validate the host, protect files, select a release, invoke Docker Compose, and manage LaunchAgents. `ops/windows/` keeps the equivalent PowerShell responsibilities.

Alternative: port every PowerShell operation line-for-line to zsh. Rejected because duplicated application logic would drift and would require two independent security reviews.

### 3. Use one designated-account Mac root outside the working tree

The default Mac root is `${HOME}/Library/Application Support/InternalExam`, with `configuration`, `releases`, `backups`, `evidence`, `diagnostics`, and `state`. The account that is currently signed in and runs the formal host is recorded as `designatedHostAccount`; no new dedicated OS account is created or required. Scripts quote every path. Directories use owner-only permissions and formal environment files use mode `0600`. The release bundle never contains mutable data or secrets.

Development, staging, and formal projects use explicit names. Formal host-bound lifecycle/evidence/backup directories must be absolute. This prevents a repository rename or a different current directory from silently selecting new Compose volumes.

Alternative: run formal Compose from the development checkout and `.env`. Rejected because bind-mounted Nginx files and project-name-derived volumes could change with ordinary development work.

### 4. Keep native per-architecture builds from the same release inputs

The first phase does not add a registry. A release bundle records one Git commit and checksums. Mac builds ARM64 images; a future typical Windows host builds AMD64 Linux images from the same inputs. Each build produces a platform/architecture image manifest, scans, staging evidence, and UAT. Base-image pinning must use a multi-platform index digest or explicit per-architecture digests.

Alternative: export locally built Mac images to Windows. Rejected because ARM64 image archives are not normally runnable on AMD64 and emulation is not an acceptance target. A multi-arch registry remains a later optimization if host count grows.

### 5. Treat paired backup and a cutover manifest as the only cross-host data format

The existing PostgreSQL custom dump, media archive, manifest, checksums, and last-written `SUCCESS` remain the migration unit. Each formal backup must also be synchronized to an independent encrypted second storage on a distinct physical device or host. Target restore first runs in disposable resources and validates migration head, table counts, media count, and a readable sample. `Docker.raw`, raw named volumes, unverified archives, and backups without a verifiable second copy are rejected for formal pre/post-exam, pre-upgrade, and cutover use.

Each formal dataset has an immutable `datasetId`. Each formal host/project has a `hostId`, and each accepted writer has a monotonically increasing `writerGeneration` (initial writer `1`; each accepted cutover is exactly the previous generation plus one). `prepare-cutover` writes a checksummed cutover manifest containing the dataset, source and target hosts, generation transition, release/image identity, final backup identifiers/checksums, quiescence evidence, and timestamps. It must stop the entire source formal Compose project (gateway, frontend, backend, worker, and database), not only the candidate gateway, and record proof that no source service remains running. `accept-cutover` verifies the manifest, isolated target restore, target preflight, and the stopped source before exposing the target candidate gateway and recording the next writer generation. A stale host or generation cannot be reopened as a writer.

Rollback has two distinct contracts. A same-host version rollback selects the previous release and the verified pre-upgrade paired backup; if restoring that backup discards writes made after it was taken, the operator must provide an explicit typed data-loss confirmation and the evidence must record the expected loss. A cross-host rollback first creates and verifies the latest paired backup and independent encrypted second copy on the target that accepted writes, then stops the entire target project and restores that newest target backup to the source or another approved host; stale source data must never simply restart. If the target accepted no writes, it is stopped as a whole and the unchanged source may reopen only after preflight. Formal pre-exam, post-exam, pre-upgrade, and cutover backup/second-copy failures fail closed; daily opportunistic backup may report skipped/degraded status without being treated as formal evidence.

### 6. Make the formal LaunchAgent mandatory after designated-account login

Docker Desktop remains a per-user application and starts only after the designated host account signs in. The selected formal host MUST have Docker Desktop Resource Saver disabled and MUST install and enable a project-owned bootstrap LaunchAgent for that account. It waits for Docker readiness, validates the selected release state, and issues an idempotent `compose up -d --no-build`. Its bounded retry/backoff, real `launchctl bootstrap`/`print` load/status evidence, and an execution lock are part of real-host acceptance; a retry must not start duplicate Compose recovery. A separate periodic LaunchAgent may invoke the existing opportunistic backup command, which records skipped/degraded outcomes during exams or unchanged data.

The LaunchAgent never promotes, restores, deletes, rotates sessions, or approves an exam. A post-reboot formal preflight and human approval remain mandatory even when the LaunchAgent reports healthy.

### 7. Make macOS preflight evidence explicit

Host checks include Docker startup configuration, explicitly disabled Resource Saver, architecture, AC power/sleep policy, time evidence, FileVault and firewall state, fixed LAN address, exact internal CORS, approved LAN CIDR, loaded `pf` or an approved managed-firewall equivalent, and a tested port matrix. The matrix must allow only candidate TCP `8080` from the approved CIDR to the fixed private IP; keep operator `8081`, PostgreSQL `5432`, and direct frontend `5173` loopback-only; leave backend `8000` and the worker unexposed; and reject candidate `8080` from an unapproved CIDR plus `8081`/`5432`/`5173`/`8000` and admin/docs/OpenAPI routes from a second device. Permissions, disk reserve, service health, migration, SMTP, browser evidence, release checksums, and a physically independent encrypted second-copy check are also required. Checks that require administrator access are documented and captured as explicit operator-supplied evidence rather than silently skipped.

The current host snapshot is diagnostic input, not acceptance evidence; final checks must be rerun after configuration.

### 8. Extend candidate desktop support to macOS

Browser detection adds current macOS Chrome and Safari with the existing Chromium minimum and a documented macOS Safari minimum. Embedded browsers remain blocked. Unit tests and real-client UAT cover both. This is a client compatibility change only and does not broaden the formal security boundary.

## Risks / Trade-offs

- **[Docker Desktop requires a logged-in user]** → Keep best-effort status explicit, use the current signed-in designated host account, install the mandatory bounded LaunchAgent, and require post-reboot operator preflight.
- **[The same Mac is also used for development]** → Use the designated account's protected root, immutable releases, explicit project names, absolute data roots, and prohibit development builds during exam windows; do not make creation of another OS account a hidden prerequisite.
- **[Application Firewall is not a full subnet firewall]** → Bind only the fixed private IP, require an approved CIDR in `pf` or a managed equivalent, keep operator/database/direct-frontend ports on loopback, and perform second-device plus unapproved-CIDR negative tests.
- **[ARM64 and AMD64 image digests differ]** → Store architecture in release evidence and require native staging/security evidence per target.
- **[LaunchAgent or Docker recovery could mask a degraded dependency]** → Restore containers only; readiness and manual exam approval remain separate.
- **[Two active hosts cause divergent data]** → Require source shutdown, final backup, target restore, and one-writer evidence; rollback after writes uses a new backup.
- **[Host scripts can leak secrets through command output]** → Pass environment files directly to Compose, redact diagnostics, test logs, and keep secret values out of evidence.

## Migration Plan

1. Preserve the current implementation as a clean, tested release baseline.
2. Add shared release metadata and formal/staging project-name checks without changing the running development stack.
3. Implement and statically test `ops/macos/` and LaunchAgent templates in temporary roots.
4. Update browser support, CI, environment examples, and documentation.
5. Configure the Mac manually for Docker login startup, resources, power, fixed IP, firewall, FileVault, time, and protected host paths.
6. Install and enable the mandatory LaunchAgent for the designated account, then capture real `launchctl bootstrap`/`print`, Docker-failure retry, and lock/no-duplicate evidence.
7. Build native ARM64 images and complete disposable Mac staging, security, E2E, capacity, SMTP, backup, second-copy restore, Docker restart, and host-restart recovery gates, including the approved-CIDR/`pf` port negative tests.
8. Create or verify a pre-promotion paired backup and its independent encrypted second copy, fail closed if either is unavailable or unverified, run `prepare-cutover` only when the source formal project can be stopped as a whole, promote the already tested images, run `accept-cutover`, complete desktop/phone UAT, and retain checksummed evidence.
9. Keep the Windows adapter and CI checks. For a later move, build native AMD64 images from the same release inputs, restore the final Mac backup in Windows staging, prepare and stop the entire Mac formal project, accept the Windows cutover with a new writer generation, rotate sessions, and run Windows-specific UAT.

Same-host version rollback uses the previous release plus the verified pre-upgrade paired backup and requires explicit confirmation of any post-backup data loss before restore. Cross-host rollback after target writes first makes and verifies the target's newest paired backup, stops the entire target project, and restores that backup to the source or another approved host; cross-host rollback before target writes may reopen the unchanged source only after target shutdown and preflight. Neither path relies on database downgrade or stale host data.
