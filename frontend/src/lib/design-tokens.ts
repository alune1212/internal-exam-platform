/**
 * TypeScript mirror of the CSS custom properties defined in `src/index.css :root`.
 *
 * Use these constants when a component needs the raw token value at runtime
 * (e.g. inline styles, computed styles, dynamic CSS injection). For everyday
 * styling prefer the Tailwind utilities (`bg-canvas`, `text-ink`, etc.)
 * defined in `tailwind.config.ts`.
 *
 * Color tokens are hex (per design spec section 3.1 - no HSL).
 */

export const designTokens = {
  // Surfaces
  canvas: "#ffffff",
  canvasWarm: "#fafaf7",
  surfaceCard: "#f5f3ee",
  surfaceElev: "#ffffff",

  // Ink
  ink: "#111111",
  inkSoft: "#2a2a2a",
  body: "#374151",
  muted: "#6b7280",

  // Lines
  hairline: "#e5e7eb",
  hairlineSoft: "#f3f4f6",

  // Footer
  footer: "#0a0a0a",
  footerSoft: "#a1a1aa",

  // Status
  success: "#166534",
  warning: "#b45309",
  error: "#b91c1c",

  // Radius
  radiusPill: "9999px",
  radiusLg: "16px",
  radiusMd: "8px",
  radiusSm: "4px",

  // Shadows (full shadow strings - drop straight into `box-shadow`)
  shadowCard: "0 1px 2px rgba(17, 17, 17, 0.04), 0 4px 12px rgba(17, 17, 17, 0.04)",
  shadowPop: "0 8px 24px rgba(17, 17, 17, 0.08)",
  shadowElevate: "0 16px 40px rgba(17, 17, 17, 0.1)",

  // Fonts
  fontDisplay: '"Manrope", "Inter", system-ui, sans-serif',
  fontBody: '"Inter", system-ui, sans-serif',
  fontMono: '"JetBrains Mono", ui-monospace, monospace',
} as const;

export type DesignTokenKey = keyof typeof designTokens;
export type DesignTokenValue = (typeof designTokens)[DesignTokenKey];
