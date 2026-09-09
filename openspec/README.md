# OpenSpec notes

## Current deployment scope

As of 2026-09-08, the current deployment status and observed acceptance are
recorded in [`docs/handoff.md`](../docs/handoff.md). The scoped runtime procedure
is [`docs/minimal-macos-deployment.md`](../docs/minimal-macos-deployment.md).
This file records the scope and OpenSpec lifecycle; it does not duplicate the
live evidence ledger.

Detached release signatures, paired backups, independent second-copy storage,
restore drills, full staging/promotion, and Windows migration were deliberately
excluded. They remain requirements of the full operations path where stated;
their absence must not be reported as a failed current deployment or as a
passed full-release gate.

## Change and archive status

- `openspec/specs/` is the current normative specification set.
- `openspec/changes/` contains active implementation and follow-up change records.
- `openspec/changes/archive/` preserves the original facts and wording of completed or superseded changes. Archive files are historical evidence and are not rewritten to match the current minimal deployment.
- Remaining unchecked tasks in active changes stay unchecked. Current minimal Mac evidence does not complete future Windows cutover, full signed-release operations, remote CI, or complete security-scan tasks.

The v1.0.0 source-release scope and historical records are separated:

- [`simplify-v1-source-release`](changes/archive/2026-09-09-simplify-v1-source-release/) records the completed v1.0.0 source release. It retires signed-package, Windows and cross-host entrypoints while preserving shared data-protection, security, migration and isolated E2E checks. Its main requirements are synchronized, and its task record links the tested release commit separately from the unchanged production host.
- [`harden-internal-deployment-readiness`](changes/archive/2026-09-09-harden-internal-deployment-readiness/) is archived as a completed historical implementation. Its original records remain intact; this adds no full-path production acceptance.
- `remediate-repository-security-findings` retains security hardening requirements for the full signed-release and backup-enabled path. Detached signatures, paired backup/restore, second-copy evidence, remote CI, and the complete final scan remain unverified; this scope decision does not mark those tasks complete.
- [`stabilize-windows-internal-exam-platform`](changes/archive/2026-09-09-stabilize-windows-internal-exam-platform/) is archived as a superseded operations path. Its two pending native Windows acceptance tasks remain unchecked. Windows is not a supported v1.0.0 release path.

The two historical changes were archived without reapplying their old deltas over later main specifications. Shared Python safety tools and their tests remain maintained; returning to a retired deployment path requires a new scope decision and validation.

Older operational wording can be located through Git history when needed. The
current deployment status belongs in the live handoff and minimal-deployment
documents; OpenSpec records the scope decision and the requirements that remain
conditional on the full operations path.
