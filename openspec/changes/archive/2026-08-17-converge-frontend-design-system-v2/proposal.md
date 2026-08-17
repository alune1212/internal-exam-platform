## Why

The frontend now has a documented Academic Editorial foundation, but its live consumers still drift in page width, surface ownership, typography, status language, action placement, and interaction detail. A second-stage convergence is needed now to turn that foundation into one consistently applied exam-platform experience instead of continuing page-by-page visual correction.

## What Changes

- **BREAKING (visual contract only)** Redesign the presentation of navigation, typography hierarchy, ordinary page skeletons, and exam-result composition while retaining the warm-paper palette, restrained Academic Editorial tone, system-font stacks, current routes, and current navigation destinations.
- Make Chinese the primary interface language and rewrite visible headings, labels, actions, status feedback, and supporting copy into one task-oriented voice without changing business meaning or exposing raw API codes; remove decorative English and routine all-caps eyebrow labels except for governed product or operational terms.
- Give page width, surfaces, fields, status feedback, data presentation, and action placement one shared owner. Ordinary pages will use governed page-frame, surface, form-field, status, action-group, report-toolbar, and responsive data-table contracts instead of locally recomposing their visual rules.
- Preserve four intentional composition families: calm Candidate pages, compact Admin workbenches, focused and touch-friendly Exam Focus workflows, and minimal chrome-free Auth canvases. The families share tokens and primitives but do not share identical chrome or density.
- Recompose Exam Focus so active exam and practice workspaces expose only task-relevant controls, with semantic radio behavior, guarded exit focus management, at least 44-by-44 CSS-pixel touch targets for focus actions, reachable save/navigation/submit actions, safe-area support, and responsive dialog/sheet behavior.
- Migrate representative Auth, Candidate, Exam Focus, and Admin routes first, then migrate the remaining route inventory only after the shared contracts pass rendered acceptance.
- Add enforceable drift policy and rendered acceptance for governed tokens, arbitrary typography, containment, control states, long content, keyboard paths, reduced motion, mobile landscape, 200-percent zoom, and the 320/375/414/430/768/desktop viewport matrix.
- Synchronize the resulting contract and observed verification evidence in `frontend/DESIGN.md` and `docs/handoff.md`.

### Non-goals

- No route path, navigation destination, backend API, database schema, authentication, authorization, exam snapshot, scoring, answer-save, submit, retake, invitation, import, or report-contract change.
- No new frontend framework, replacement component library, runtime service, external font request, bundled font asset, or external design dependency.
- No LMS expansion, complex RBAC, queue infrastructure, durable offline exam mode, anti-cheat/monitoring suite, or broader product workflow redesign.
- No claim that disposable Chromium evidence is formal Mac, Windows, Safari, iOS, or Android acceptance.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `frontend-page-experience`: Strengthen the existing design-system, Chinese-first content, page-family, containment, control-state, Exam Focus, responsive, and rendered-evidence requirements so the canonical system is applied consistently across all current routes.

## Impact

- Frontend contract and evidence: `frontend/DESIGN.md`, `docs/handoff.md`, shared copy contracts, and visual-policy tests.
- Frontend foundations: `frontend/src/index.css`, `frontend/tailwind.config.ts`, `frontend/src/lib/design-tokens.ts`, existing breakpoint ownership, and shared page/layout/UI/editorial/exam primitives.
- Representative routes: candidate and admin authentication, exam list, active exam, result review, admin dashboard, question form, and report surfaces, followed by the remaining current route inventory.
- Tests: focused unit/component coverage plus deterministic Playwright route-state and multi-viewport acceptance. Screenshot baselines and presentation assertions will change intentionally; route, API, authorization, and business-behavior assertions remain compatibility gates.
- No backend, persistence, deployment, package, public port, or external asset change is required.
