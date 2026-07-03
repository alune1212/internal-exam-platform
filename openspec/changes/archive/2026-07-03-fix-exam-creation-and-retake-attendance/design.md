## Context

The formal exam flow already treats `draft -> active` as the publish boundary: it validates the assigned candidate scope, validates fixed-paper capacity against the active question bank, and freezes the active question pool into `exam_question_pool`. The current create path accepts `status="active"` but only persists the row, which can produce an active exam with no frozen pool and no way to import candidates afterward.

The admin attendance report currently answers three independent questions: not started, in progress, and submitted. That works for one-attempt exams but breaks during retake: a candidate can have an earlier submitted attempt and a later in-progress retake, so separate submitted and in-progress queries can both include the same candidate.

The change is backend-local and should preserve existing API shapes. Frontend admin pages should receive corrected data without UI changes.

## Goals / Non-Goals

**Goals:**

- Ensure every active exam is created through the existing draft-to-active validation and question-pool freezing path.
- Prevent the admin create endpoint from producing active exams that cannot be started.
- Classify attendance status by latest attempt state for each candidate within the selected report scope.
- Preserve report filtering, workbook structure, Excel escaping, fixed-paper semantics, snapshot semantics, and retake grant semantics.
- Add regression tests for both defects.

**Non-Goals:**

- No database migration unless implementation reveals a hard persistence constraint gap.
- No new public API fields.
- No frontend redesign or report UX restructuring.
- No changes to scoring, answer saving, auto-submit worker scheduling, or retake grant creation rules.

## Decisions

1. Reject direct active creation before persistence.

   The current `ExamCreate` shape does not include exam-candidate scope, so a newly created active exam cannot satisfy the existing publish requirement that assigned candidates already exist. The admin create service should reject `status="active"` with a clear domain error before inserting an exam row. Callers must create a draft, import or assign candidates, and then publish through `update_exam()`.

   Alternative considered: treat direct active creation as publish-equivalent. That would preserve the accepted status value but cannot validate candidate scope without changing the request shape or adding a second implicit assignment path.

2. Keep publish validation centralized.

   Shared helper logic should enforce update-time activation checks: candidate scope must exist, question capacity must be sufficient, and the frozen pool must be written before commit. Create rejects direct activation, so persisted active exams still only come from the centralized publish path.

3. Compute attendance from latest attempt state per exam/candidate.

   For `exam_id`-filtered reports, each scoped active candidate should be classified as:
   - `not_started` when no attempt exists for that exam.
   - `in_progress` when the latest attempt for that exam is in progress.
   - `submitted` when the latest attempt for that exam is submitted or auto-submitted.

   For global reports, preserve the current global view but use the latest attempt per `(exam_id, candidate_id)` before membership tests so a submitted attempt and an in-progress retake for the same exam do not double-count the same candidate.

4. Keep ranking and score reports on latest submitted attempts.

   Score, question accuracy, wrong-question, and ranking reports intentionally use latest submitted attempts. This change only alters attendance classification, where current operational state matters.

## Risks / Trade-offs

- [Risk] Direct active create now fails instead of creating a broken active exam. -> Mitigation: return a clear domain error and keep the existing draft-to-active publish path unchanged.
- [Risk] Create path freezing can duplicate update-path logic. -> Mitigation: extract or reuse a small activation helper rather than reimplementing validation inline.
- [Risk] Global attendance semantics are less obvious than exam-filtered semantics. -> Mitigation: preserve global report behavior where possible while preventing duplicate membership for the same exam/candidate pair; cover the retake case with tests.
- [Risk] Query changes may affect report ordering. -> Mitigation: keep ordering by candidate name and retain existing distinct behavior where the global view can span multiple exams.

## Migration Plan

No schema migration is expected.

Implementation can deploy with a normal backend rollout:

1. Update service logic and tests.
2. Run backend focused tests and the existing report/export tests.
3. If Compose validation is requested, rebuild backend and run the 8080 health checks.

Rollback is code-only: revert the service changes and tests. Existing data with active exams missing frozen pools is not repaired by rollback; if such data exists, it should be handled by a separate data repair or by republishing through the corrected path.

## Open Questions

- Should a future admin create request accept candidate assignments inline so active creation can become publish-equivalent? Out of scope for this fix.
- Should global attendance eventually include exam identity in the response? That would make global multi-exam status unambiguous, but it is out of scope for this fix.
