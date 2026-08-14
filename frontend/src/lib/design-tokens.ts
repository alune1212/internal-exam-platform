/**
 * TypeScript access to the runtime tokens defined in `src/index.css :root`.
 *
 * The CSS root remains the literal authority. Every value here is deliberately
 * an exact `var(--token-name)` reference so inline styles and dynamic helpers
 * cannot become a second source of visual truth.
 */
export const designTokens = {
  // Surfaces
  canvas: "var(--canvas)",
  canvasWarm: "var(--canvas-warm)",
  surfaceCard: "var(--surface-card)",
  surfaceElev: "var(--surface-elev)",

  // Ink and status
  ink: "var(--ink)",
  inkSoft: "var(--ink-soft)",
  body: "var(--body)",
  muted: "var(--muted)",
  hairline: "var(--hairline)",
  hairlineSoft: "var(--hairline-soft)",
  footer: "var(--footer)",
  footerSoft: "var(--footer-soft)",
  success: "var(--success)",
  warning: "var(--warning)",
  error: "var(--error)",
  inkRed: "var(--ink-red)",
  inkBlue: "var(--ink-blue)",
  successOnDark: "var(--success-on-dark)",
  errorOnDark: "var(--error-on-dark)",
  overlay: "var(--overlay)",

  // Radius and elevation
  radiusPill: "var(--radius-pill)",
  radiusLg: "var(--radius-lg)",
  radiusMd: "var(--radius-md)",
  radiusSm: "var(--radius-sm)",
  shadowCard: "var(--shadow-card)",
  shadowPop: "var(--shadow-pop)",
  shadowElevate: "var(--shadow-elevate)",
  shadowSticky: "var(--shadow-sticky)",

  // Fonts
  fontDisplay: "var(--font-display)",
  fontBody: "var(--font-body)",
  fontMono: "var(--font-mono)",

  // Type scale, line heights, and tracking
  textDisplay2xl: "var(--text-display-2xl)",
  textDisplayXl: "var(--text-display-xl)",
  textDisplayLg: "var(--text-display-lg)",
  textDisplayMd: "var(--text-display-md)",
  textDisplaySm: "var(--text-display-sm)",
  textBodyLg: "var(--text-body-lg)",
  textBody: "var(--text-body)",
  textBodySm: "var(--text-body-sm)",
  textCaption: "var(--text-caption)",
  leadingDisplay2xl: "var(--leading-display-2xl)",
  leadingDisplayXl: "var(--leading-display-xl)",
  leadingDisplayLg: "var(--leading-display-lg)",
  leadingDisplayMd: "var(--leading-display-md)",
  leadingDisplaySm: "var(--leading-display-sm)",
  leadingBodyLg: "var(--leading-body-lg)",
  leadingBody: "var(--leading-body)",
  leadingBodySm: "var(--leading-body-sm)",
  leadingCaption: "var(--leading-caption)",
  trackingDisplayTight: "var(--tracking-display-tight)",
  trackingDisplay: "var(--tracking-display)",
  trackingCaption: "var(--tracking-caption)",

  // Semantic layout spacing
  spacePageInline: "var(--space-page-inline)",
  spacePageInlineLg: "var(--space-page-inline-lg)",
  spacePageBlock: "var(--space-page-block)",
  spaceSection: "var(--space-section)",
  spaceSectionLg: "var(--space-section-lg)",
  spacePanel: "var(--space-panel)",
  spaceField: "var(--space-field)",
  spaceFieldCompact: "var(--space-field-compact)",
  spaceControlX: "var(--space-control-x)",
  spaceControlY: "var(--space-control-y)",
  spaceControlGap: "var(--space-control-gap)",
  spaceInline: "var(--space-inline)",
  spaceStack: "var(--space-stack)",

  // Focus-visible treatment
  focusRingWidth: "var(--focus-ring-width)",
  focusRingColor: "var(--focus-ring-color)",
  focusRingOffset: "var(--focus-ring-offset)",
  focusRingRadius: "var(--focus-ring-radius)",

  // Motion
  motionDurationInstant: "var(--motion-duration-instant)",
  motionDurationFast: "var(--motion-duration-fast)",
  motionDurationNormal: "var(--motion-duration-normal)",
  motionDurationSlow: "var(--motion-duration-slow)",
  motionDurationShimmer: "var(--motion-duration-shimmer)",
  motionDurationPulse: "var(--motion-duration-pulse)",
  motionEaseLinear: "var(--motion-ease-linear)",
  motionEaseStandard: "var(--motion-ease-standard)",
  motionDistanceRise: "var(--motion-distance-rise)",
  motionStaggerStep: "var(--motion-stagger-step)",
  motionStaggerMax: "var(--motion-stagger-max)",

  // Layering
  zBackground: "var(--z-background)",
  zContent: "var(--z-content)",
  zSticky: "var(--z-sticky)",
  zOverlay: "var(--z-overlay)",
  zModal: "var(--z-modal)",
  zToast: "var(--z-toast)",

  // Named admin-login texture
  textureAdminLoginDot: "var(--texture-admin-login-dot)",
  textureAdminLoginDotSize: "var(--texture-admin-login-dot-size)",
  textureAdminLoginSize: "var(--texture-admin-login-size)",
} as const;

export type DesignTokenKey = keyof typeof designTokens;
export type DesignTokenValue = (typeof designTokens)[DesignTokenKey];
