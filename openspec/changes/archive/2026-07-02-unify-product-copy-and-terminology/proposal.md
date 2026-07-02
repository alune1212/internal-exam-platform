## Why

Candidate, admin, and public-facing pages currently mix Chinese terms, English eyebrow labels, raw backend enum values, and page-specific wording for the same concepts. This makes the product feel inconsistent and increases regression risk when pages are updated independently.

This change establishes one synchronized Chinese-English copy and terminology contract for visible frontend text and administrator-facing export artifacts, so UI labels, status names, critical actions, report workbooks, templates, failure reports, and tests describe the same product concepts across all ends.

## What Changes

- Define canonical Chinese-English terminology for user roles, exam scope, question types, exam states, attempt states, report fields, and import actions.
- Replace visible raw enum/code labels such as `active`, `draft`, `single`, `multiple`, `judge`, and `not_started` with synchronized display copy where they appear in the UI.
- Align candidate-facing critical actions and feedback around clear terms for saving answers, returning to exam lists, and submitting exams.
- Align admin-facing import, candidate-list, report, table-header, empty-state, loading-state, and error-state copy across related pages.
- Align backend-generated Excel sheet names, column headers, template names, failure-report names, and report status labels with the same glossary used by the frontend.
- Keep English eyebrow labels and compact table labels synchronized with their Chinese meaning instead of treating them as decorative text.
- Add or update focused frontend and backend tests that lock high-risk copy mappings and visible export labels.
- Non-goals: no backend API/schema changes, no database or persistence changes, no new localization framework, no runtime language switcher, no LMS/complex RBAC/anti-cheat expansion, and no business-rule changes.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `frontend-page-experience`: add synchronized Chinese-English copy and terminology requirements for candidate, admin, and public frontend pages.
- `admin-reporting`: align administrator-facing Excel export sheet names, headers, and status labels with the shared terminology.
- `admin-imports`: align administrator-facing import template and failure-report export labels with the shared terminology while preserving API field contracts.

## Impact

- Frontend copy constants and display helpers under `frontend/src/lib/` may be expanded or reorganized.
- Candidate pages and layout components under `frontend/src/pages/` and `frontend/src/components/layout/` will need visible text updates.
- Admin pages, report tables, import panels, and layout navigation under `frontend/src/pages/admin/` and `frontend/src/components/` will need visible text updates.
- Frontend tests that assert page headings, buttons, table headers, status pills, and error/empty states will need updates.
- Backend APIs, database migrations, Pydantic schemas, and business rules are not expected to change; backend-generated export labels and download filenames may change.
