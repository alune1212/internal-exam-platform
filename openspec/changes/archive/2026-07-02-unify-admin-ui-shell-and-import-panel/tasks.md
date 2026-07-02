## 1. Brand Mark Consistency

- [x] 1.1 Add or update an editorial brand mark component that matches the existing `frontend/public/favicon.svg` glyph and supports light/dark token-based variants.
- [x] 1.2 Update `Wordmark` to compose the shared brand mark while preserving size, label, subtitle, and `variant`/`tone` props.
- [x] 1.3 Update footer and admin navigation wordmark usage only as needed after the `Wordmark` change.
- [x] 1.4 Update `Wordmark` tests to verify the brand text, subtitle, size variants, and shared glyph rendering.

## 2. Admin Side Rail Layout

- [x] 2.1 Change the desktop `AdminSideRail` layout so the rail is viewport-stable and long main content does not push logout to the document bottom.
- [x] 2.2 Preserve existing active route highlighting, desktop nav order, dark-surface contrast, and mobile sheet behavior.
- [x] 2.3 Update `AdminSideRail` tests to cover the viewport-stable desktop rail class contract and existing mobile menu/logout access.

## 3. Import Panel UI

- [x] 3.1 Add a focused shared admin import panel component for template actions, file selection, selected filename display, disabled upload state, pending spinner state, and upload action layout.
- [x] 3.2 Migrate `QuestionImportPage` to the shared import panel while preserving template download, `importQuestions`, query invalidation, notices, upload label, and failure-report behavior.
- [x] 3.3 Migrate `CandidateImportPage` and the routed `ExamCandidatesPage` import surface to the shared import panel while preserving exam-scoped upload, query invalidation, notices, upload label, disabled state, and failure-report behavior.
- [x] 3.4 Update question and candidate import page tests to keep using the labeled file input, selected-file upload path, and failure-report assertions.

## 4. Verification

- [x] 4.1 Run `cd frontend && npm run format:check`.
- [x] 4.2 Run `cd frontend && npm test -- --run`.
- [x] 4.3 Run `cd frontend && npm run lint`.
- [x] 4.4 Run `cd frontend && npm run build`.
- [x] 4.5 Browser-check the `8080` admin entrypoint for `/admin/dashboard`, `/admin/questions`, `/admin/questions/import`, and an exam candidate import route on desktop and mobile widths, verifying logo consistency, logout placement, file picker styling, no horizontal overflow, and no console errors.
