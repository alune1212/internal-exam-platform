## Why

The admin UI currently has several visible consistency gaps: the in-page brand mark differs from the browser tab icon, the desktop logout action can drift to the bottom of long pages, and import pages expose the browser-default file picker beside product-styled buttons. These issues make the finished Academic Editorial redesign feel uneven in ordinary admin workflows.

## What Changes

- Align the admin header, desktop side rail, mobile admin header, and footer wordmark around the same brand glyph used by the browser tab icon.
- Stabilize the desktop admin side rail so navigation and logout occupy a viewport-based rail instead of being stretched by long page content.
- Replace the browser-default file input presentation on admin import pages with an accessible product-styled file picker using existing button, field, panel, icon, focus, and typography primitives.
- Reuse a small shared import panel pattern across question import and exam-candidate import pages while preserving their existing API calls, validation behavior, notices, and failure-report downloads.
- Keep mobile admin navigation usable without horizontal overflow or hidden logout access.
- Keep the deployed `8080` admin entrypoint console-clean after the UI change, including the existing configured web font hosts allowed by the frontend CSP.
- Non-goals: no backend import changes, no Word parsing, no queue-based import flow, no new dependency, no RBAC change, and no broader LMS or anti-cheat scope.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `frontend-page-experience`: Clarify brand consistency, viewport-stable admin navigation, and accessible product-styled file picking as part of shared design-system page composition and responsive behavior.

## Impact

- Affected frontend code:
  - `frontend/src/components/editorial/Wordmark.tsx`
  - `frontend/src/components/layout/AdminSideRail.tsx`
  - `frontend/src/components/layout/Footer.tsx`
  - `frontend/src/pages/admin/QuestionImportPage.tsx`
  - `frontend/src/pages/admin/CandidateImportPage.tsx`
  - `frontend/src/pages/admin/ExamCandidatesPage.tsx`
  - likely one small shared import UI component under `frontend/src/components/admin/`
- Affected tests:
  - Wordmark/editorial component tests
  - Admin side rail layout tests
  - Question and candidate import page tests
  - Deployment config test for the frontend CSP font hosts
- Affected systems:
  - Frontend UI components and pages.
  - Nginx frontend CSP header only. No API, database schema, backend service behavior, Docker topology, or dependency changes are expected.
