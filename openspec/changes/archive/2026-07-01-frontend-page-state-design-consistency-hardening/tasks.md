## 1. Required Query State Hardening

- [x] 1.1 Inventory candidate and admin pages with required queries and classify each initial state as loading, error, empty, or ready.
- [x] 1.2 Update candidate exam list, practice, exam-taking, and exam-result pages so initial query failures render explicit error states instead of empty data or indefinite loading.
- [x] 1.3 Update shared admin report/table flows so report query failures render error states and successful empty results remain visually distinct.
- [x] 1.4 Update admin dashboard query handling so failed metric/activity queries are not collapsed into zero values or empty activity.
- [x] 1.5 Update exam-candidate management so list loading/error states are explicit and import/remove/retake controls do not appear as ready before exam state is known.
- [x] 1.6 Update exam edit so the form and save action are blocked until the target exam record loads, and missing/error records render page states.

## 2. Design-System and Accessibility Consistency

- [x] 2.1 Fix candidate result heading hierarchy so the page has one page-level H1 and nested result content uses lower-level headings.
- [x] 2.2 Add accessible selected-state semantics to segmented filters in candidate result and admin attendance/report controls.
- [x] 2.3 Replace or complete the exam status dropdown semantics so label association, keyboard operation, focus handling, and selected state are valid.
- [x] 2.4 Align repeated form and feedback surfaces with local primitives, including question edit textarea usage and report export feedback.
- [x] 2.5 Review table/mobile card radius and Sheet radius overrides against `frontend/DESIGN.md`, adjusting only confirmed inconsistencies.

## 3. Focused Test Coverage

- [x] 3.1 Add or update candidate page tests for loading, error, empty, and ready states in affected pages.
- [x] 3.2 Add or update admin report/dashboard/exam-candidate/exam-edit tests for explicit error states and blocked actions while required data is unresolved.
- [x] 3.3 Add or update tests for heading hierarchy, segmented selected-state semantics, and dropdown accessibility behavior.

## 4. Verification

- [x] 4.1 Run `cd frontend && npm test -- --run`.
- [x] 4.2 Run `cd frontend && npx tsc --noEmit`.
- [x] 4.3 Run `cd frontend && npm run lint`.
- [x] 4.4 Run `cd frontend && npm run format:check`.
- [x] 4.5 Run `cd frontend && npm run build`.
- [x] 4.6 Start the frontend or Compose entrypoint and capture mobile/desktop browser screenshots for candidate focus-mode bottom controls and admin report action wrapping.
