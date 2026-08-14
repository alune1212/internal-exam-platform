## Why

The frontend already has a strong Academic Editorial identity and distinct candidate, admin, and exam-focus shells, but its written design contract and live implementation have drifted: fonts have multiple sources of truth, the documented footer does not exist, repeated labels and nested cards weaken hierarchy, and responsive/motion/form-state rules are incomplete. A focused system unification is needed now so future page work extends one verifiable product language instead of adding another local visual pattern.

## What Changes

- Rewrite `frontend/DESIGN.md` as the canonical frontend design contract, covering source-of-truth ownership, tokens, page families, surface hierarchy, interaction states, content voice, responsive behavior, accessibility, motion, verification, and change governance.
- Establish one governed source model: `src/index.css :root` for runtime visual values and one typed build-time map for structural breakpoints; reconcile Tailwind aliases, JavaScript media-query consumers, and the TypeScript token references around the existing offline-safe system font stack.
- Preserve and formalize three task-flow families—calm candidate journeys, dense admin workbenches, and specialized exam/practice focus workspaces—plus a chrome-free Auth Canvas exception. Authentication and application shells will remain footer-free unless a page has a semantic local footer.
- Make page context labels optional, keep headings upright, reduce decorative bilingual/italic metadata, and reserve question numbering and status labels for genuine operational meaning.
- Define a single surface-containment model and remove card-in-card presentation from affected admin and result surfaces while preserving data density and business behavior.
- Consolidate repeated form controls and field states through shared local primitives, including select controls, focus, active, disabled, loading, error, and success behavior.
- Group admin navigation by operational domain and add exam-context navigation for workspace, editing, roster/invitations, and result/review destinations without changing route authorization or backend contracts.
- Define reduced-motion behavior and deterministic responsive acceptance at 320, 375, 414, 430, and 768 CSS pixels, mobile landscape, representative desktop widths, and 200 percent zoom; expand rendered browser evidence for auth, candidate, admin, and focus workflows.
- Synchronize implementation evidence with `frontend/DESIGN.md` and `docs/handoff.md` after verification.

### Non-goals

- No backend API, database schema, authentication, authorization, exam snapshot, scoring, invitation, import, or report-contract changes.
- No replacement design library, framework migration, route rewrite, or full rebuild of the existing Academic Editorial frontend.
- No LMS expansion, complex RBAC, queue infrastructure, durable offline exam support, or anti-cheat/monitoring suite.
- No claim of formal Mac or Windows acceptance from disposable browser checks; formal host evidence remains separate.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `frontend-page-experience`: Strengthen the required design-system contract, interface-family composition, surface containment, shared control states, admin navigation structure, motion behavior, and multi-viewport verification.

## Impact

- Frontend documentation: `frontend/DESIGN.md`, `docs/handoff.md`.
- Frontend foundations: `frontend/src/index.css`, `frontend/tailwind.config.ts`, `frontend/src/lib/design-tokens.ts`, the new typed breakpoint map, `use-media-query.ts`, and copy/token tests; the change retains system font fallbacks and introduces no font asset.
- Shared UI: page, editorial, layout, admin, form, and exam components under `frontend/src/components/` and `frontend/src/features/exam/`.
- Representative candidate/admin pages and their focused unit, component, responsive, accessibility, offline-asset, and Playwright checks.
- Existing routes and API calls remain compatible; no new runtime service, package, external font request, or bundled font asset is introduced by this change.
