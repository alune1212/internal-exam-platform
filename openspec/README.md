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

Older operational wording can be located through Git history when needed. The
current deployment status belongs in the live handoff and minimal-deployment
documents; OpenSpec records the scope decision and the requirements that remain
conditional on the full operations path.
