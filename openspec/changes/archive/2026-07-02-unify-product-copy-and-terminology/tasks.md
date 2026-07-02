## 1. Shared Copy Contract

- [x] 1.1 Audit visible public, candidate, and admin copy for repeated role, roster, question-bank, report, status, import, save, and submit terminology.
- [x] 1.2 Expand `frontend/src/lib/pageCopy.ts` or a nearby typed helper with canonical Chinese-English glossary entries, page labels, report field labels, import labels, and display mappings for exam status, availability status, attempt status, question type, and question status.
- [x] 1.3 Add focused unit coverage for the shared copy/status helpers so Chinese and English labels stay synchronized.

## 2. Public And Candidate Pages

- [x] 2.1 Update public login and candidate layout/navigation copy to use canonical exam-taker terminology and a truthful return-to-list label instead of mixed role or exit wording.
- [x] 2.2 Update exam list and exam start copy to use consistent availability, current-user, rule, and start-state wording.
- [x] 2.3 Update exam-taking components and pages to consistently distinguish saving answers, submitting the exam, submission failure, and auto-submit messaging.
- [x] 2.4 Update practice, result, review, not-logged-in, empty, and error states to use the same page labels and role terminology.

## 3. Admin Pages And Reports

- [x] 3.1 Update admin navigation, dashboard, exam list, and exam edit copy to use canonical question-bank, exam, roster, participant, and status terminology.
- [x] 3.2 Update question list/import surfaces to replace raw question type/status labels and align question-bank import wording.
- [x] 3.3 Update exam roster/import surfaces, including any retained `CandidateImportPage`, to use canonical participant and roster terminology.
- [x] 3.4 Update score, accuracy, absent/attendance, and shared report table labels so desktop headers and mobile labels use synchronized Chinese-English field names.
- [x] 3.5 Update loading, empty, disabled, notice, and error copy on related admin pages to use the same canonical object/action names.

## 4. Tests And Verification

- [x] 4.1 Update affected frontend page/component tests that assert headings, buttons, table headers, status pills, empty states, and error states.
- [x] 4.2 Run frontend checks: `npm run format:check`, `npm test -- --run`, `npm run lint`, and `npm run build` from `frontend/`.
- [x] 4.3 Run `openspec validate --changes unify-product-copy-and-terminology`.
- [x] 4.4 Browser-smoke `/login`, `/exams`, `/admin/dashboard`, `/admin/questions`, and `/admin/reports/scores` through the local 8080 entrypoint and confirm no visible raw enum/code labels or inconsistent Chinese-English terminology remain on the checked surfaces.

## 5. Backend Export Copy

- [x] 5.1 Audit backend-generated report workbooks, import templates, failure-report workbooks, download filenames, and export-specific docs for stale terminology.
- [x] 5.2 Align report export sheet names, headers, and attendance status labels with the shared report terminology.
- [x] 5.3 Align import template sheet names, candidate-template filename, failure-report filename, failure-report detail headers, and failure-report import type labels with the shared import terminology.
- [x] 5.4 Preserve backend API, database, stored JSON keys, upload template field keys, report query behavior, and scoring/import business rules.
- [x] 5.5 Update affected backend tests and project docs that assert or describe backend-generated export copy.
- [x] 5.6 Run targeted backend tests, backend format/lint/type checks, and `openspec validate --changes unify-product-copy-and-terminology`.
