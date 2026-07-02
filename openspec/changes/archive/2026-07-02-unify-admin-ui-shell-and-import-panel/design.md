## Context

The Academic Editorial redesign is already implemented through tokens, page primitives, editorial components, and admin/candidate layouts. The remaining issues are concentrated in ordinary admin surfaces:

- `Wordmark` renders a circular Chinese monogram while the browser tab icon uses a different glyph.
- `AdminSideRail` is a normal flex item; long admin pages can stretch it, pushing logout to the page bottom instead of the viewport bottom.
- Question and candidate import pages use the browser-default `input type="file"` presentation beside product-styled buttons.
- The deployed Nginx CSP blocks the already configured Google Fonts stylesheet/font hosts, which creates console noise during real `8080` admin QA.

This change is frontend-experience focused and should preserve all import API behavior, auth behavior, page routing, and backend validation semantics. The only deployment config adjustment is the minimal CSP font-host allowance needed for the existing frontend font setup.

## Goals / Non-Goals

**Goals:**

- Use one brand glyph source across favicon, admin navigation, mobile admin header, and footer wordmarks.
- Keep desktop admin navigation and logout visually stable within the viewport on short and long pages.
- Make import file selection look and behave like the rest of the design system while staying keyboard-accessible and screen-reader usable.
- Reduce duplication between question import and candidate import panels without introducing a broad upload framework.
- Verify the updated experience across desktop and mobile admin routes.
- Keep the `8080` admin entrypoint free of console errors caused by the existing font configuration.

**Non-Goals:**

- No backend endpoint, schema, import parser, upload limit, or failure-report change.
- No Word parsing, queue-based import processing, or new file formats.
- No new design library, icon package, routing model, or dependency.
- No broader security header relaxation beyond the existing stylesheet/font host requirement.
- No redesign of the entire admin information architecture.

## Decisions

### Use a reusable brand mark inside `Wordmark`

Create a small brand mark representation that matches the existing `favicon.svg` glyph and let `Wordmark` compose it. The mark should support light and dark surfaces through existing token classes rather than inline colors.

Alternative considered: replace `favicon.svg` with the existing circular `知` mark. That would make the page and tab consistent, but it contradicts the browser comment asking the page logo to match the tab and would keep the stronger glyph unused in the product chrome.

### Stabilize the desktop side rail at the viewport level

Make the desktop admin side rail behave as a viewport rail, with the nav stack and logout area laid out inside a `h-dvh`/sticky container. The logout action should remain reachable near the bottom of the viewport while long page content scrolls independently in the main document.

Alternative considered: keep the current flex layout and add spacing around logout. That would improve one screenshot but would not fix the root cause on long tables or report pages.

### Build a focused shared import panel

Add a small `ImportPanel` component under the admin component boundary. It should compose `PageSection`, `Field`, `FieldLabel`, `Button`, `Spinner`, and lucide icons. It should hide the native file input visually, trigger it from a styled button, expose selected filename text, and leave the actual `File` state and mutation behavior in the page.

Alternative considered: extend the generic `Input` primitive for all `type="file"` controls. That spreads import-specific layout assumptions into a low-level input component and risks changing unrelated file inputs later.

### Keep implementation page-local where business behavior differs

Question import keeps template download and the "上传并校验" action. Candidate import keeps exam-scoped upload and its existing submit label. The shared panel owns presentation only; page code owns API calls, query invalidation, notices, and failure-report rendering.

Alternative considered: merge import pages into a generic import workflow. That would be larger than the current UI consistency problem and would blur existing route-specific responsibilities.

### Allow only the existing frontend font hosts in CSP

Browser QA for the deployed `8080` entrypoint should be console-clean. Because the frontend already references Google Fonts, the Nginx CSP should explicitly allow `https://fonts.googleapis.com` in `style-src` and `https://fonts.gstatic.com` in `font-src`, without changing script, connect, frame, or form restrictions.

## Risks / Trade-offs

- Brand glyph rendered in React could diverge from `favicon.svg` over time -> Keep the glyph path simple and colocated in the brand component; update tests around mark rendering.
- Sticky viewport rail can create nested scroll or height issues on small desktop heights -> Prefer a single rail container with predictable overflow and verify long-page routes such as question list.
- Hidden file input can lose accessibility if implemented as a div-only control -> Use a real input with a proper label/button trigger, preserve focus behavior, and keep upload tests based on the labeled file input.
- Shared import panel can become too generic -> Limit props to the two current import pages and avoid backend/import abstractions.
- CSP changes can accidentally widen the page security posture -> Limit the allowance to the stylesheet/font origins already required by the frontend and cover it with a deployment config test.

## Migration Plan

1. Add or update the brand mark component and adapt `Wordmark` without changing public route structure.
2. Update desktop `AdminSideRail` layout while preserving mobile sheet behavior.
3. Add the shared import panel and migrate question/candidate import pages to it.
4. Update focused component/page tests.
5. Run frontend format, tests, lint, build, deployment config tests for the CSP header, and browser-check `/admin/dashboard`, `/admin/questions`, `/admin/questions/import`, and an exam candidate import route through the `8080` entrypoint if available.

Rollback is straightforward: revert the frontend component/page changes and the Nginx CSP font-host adjustment. No data migration or API rollback is involved.

## Open Questions

- Should the footer use the exact dark-surface inverse of the favicon glyph, or keep a softer monochrome mark to match footer contrast? Default implementation should use the same glyph with dark-surface token colors unless visual QA shows contrast issues.
