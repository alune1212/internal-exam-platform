## 1. Regression Tests

- [x] 1.1 Add exam-service coverage showing direct active exam creation either performs publish-equivalent validation/freezing or is rejected without persisting an active exam missing `exam_question_pool`.
- [x] 1.2 Add exam-service coverage that direct active creation cannot bypass candidate-scope and question-capacity publish requirements.
- [x] 1.3 Add report-service coverage for a submitted attempt followed by an in-progress retake, asserting the candidate appears in `in_progress` and not in `submitted` for the same exam.
- [x] 1.4 Add report-service coverage that a latest submitted or auto-submitted attempt remains classified as `submitted` and candidates with no attempts remain `not_started`.

## 2. Exam Activation Logic

- [x] 2.1 Extract or reuse a service helper that applies activation checks consistently for create and update paths.
- [x] 2.2 Update `create_exam()` so any persisted active exam satisfies candidate scope, question capacity, and frozen question pool requirements before commit.
- [x] 2.3 Preserve existing `draft -> active`, archived, fixed-paper, empty-rule, and frozen-pool semantics.

## 3. Attendance Classification Logic

- [x] 3.1 Add a query/helper for latest attempt state per `(exam_id, candidate_id)` in the requested attendance scope.
- [x] 3.2 Update `get_absent_candidates()` so `not_started`, `in_progress`, and `submitted` membership is mutually exclusive for each candidate within an exam.
- [x] 3.3 Preserve existing exam filter behavior, global report behavior where compatible, candidate eligibility filters, ordering, workbook sheet structure, and Excel escaping.

## 4. Verification

- [x] 4.1 Run `uv run pytest app/tests/test_exam_service.py app/tests/test_report_service.py -q`.
- [x] 4.2 Run any affected API tests if service behavior changes at the HTTP layer.
- [x] 4.3 Run `openspec validate "fix-exam-creation-and-retake-attendance" --type change --strict`.
- [x] 4.4 Review `git diff` for unrelated edits and confirm no frontend or schema changes were introduced unless required by implementation.
