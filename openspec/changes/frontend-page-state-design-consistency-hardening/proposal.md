## Why

The frontend already follows the Academic Editorial design system at the token and layout level, but a multi-agent review found that several candidate and admin pages still handle loading, empty, error, and form states inconsistently. This change hardens the page-state contract so failed queries are not mistaken for empty data and both portals continue to share the same frontend design primitives.

## What Changes

- Add a frontend page experience capability covering candidate/admin page state handling, design-system consistency, and interaction accessibility.
- Standardize query loading, empty, and error branches around shared `PageState`, `PageSection`, `Alert`, and table primitives where appropriate.
- Prevent admin edit and exam-candidate management pages from rendering actionable default or stale controls before their required query data is ready.
- Correct heading hierarchy, segmented control semantics, and local form primitive drift found in the review.
- Preserve existing backend APIs, data contracts, exam delivery behavior, and Academic Editorial visual direction.
- Non-goals: no LMS features, no anti-cheat/monitoring expansion, no new role model, no backend schema changes, no dependency additions, and no redesign beyond aligning existing pages with `frontend/DESIGN.md`.

## Capabilities

### New Capabilities
- `frontend-page-experience`: Covers React page-state behavior, candidate/admin UI consistency, design-system primitive usage, and key accessibility expectations for frontend pages.

### Modified Capabilities
- None.

## Impact

- Affected frontend areas:
  - Candidate pages: exam list, practice, exam taking, exam result.
  - Admin pages: dashboard, exam list/report pages, exam edit, exam candidates, question list dialog, report export controls.
  - Shared components: `ReportPage`, `SimpleDataTable`, `ReportExportButton`, page primitives, and relevant form/status controls.
- No public API, database, auth token, snapshot, import, scoring, Docker, or deployment behavior changes are intended.
- Verification should include focused frontend tests, type/lint/build checks, and browser screenshots for mobile focus-mode and report-action wrapping.
