## Why

Two confirmed exam lifecycle defects can leave administrators with incorrect operational state: an exam can be created directly as `active` without the publish-time frozen question pool, and a candidate with a submitted attempt plus an in-progress retake can appear in both attendance states. These are small but business-critical correctness issues in the formal exam flow and report truth layer.

## What Changes

- Reject direct active exam creation so published exams always pass the draft-to-active scope validation, question capacity validation, and frozen question pool creation path.
- Make attendance status reporting mutually exclusive for each candidate within each exam by using the latest attempt state when classifying not-started, in-progress, and submitted candidates.
- Preserve existing fixed-paper, snapshot, retake grant, report export, and Excel escaping semantics.
- Add focused regression coverage for direct active exam creation and retake attendance classification.

Non-goals:

- No new LMS, anti-cheat, queue, RBAC, or monitoring behavior.
- No database schema change unless implementation discovers an existing constraint gap that blocks the minimal fix.
- No broad report redesign or terminology cleanup.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `exam-delivery`: active exams must only exist with a valid frozen question pool created through the publish-equivalent path.
- `admin-reporting`: attendance status reports must classify each candidate by the latest relevant attempt state without duplicate status membership during retakes.

## Impact

- Backend services: `backend/app/services/exam_service.py`, `backend/app/services/report_service.py`.
- Backend tests: focused coverage in exam service/report service and any affected API tests.
- API behavior: admin exam creation/update and admin attendance report responses become stricter and more consistent.
- Frontend: no UI contract change expected; existing admin pages should consume corrected backend state.
