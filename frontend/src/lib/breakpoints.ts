/**
 * Structural viewport thresholds shared by Tailwind and runtime media-query
 * consumers. Keep width literals in this map; CSS custom properties cannot be
 * evaluated inside a media query during Tailwind compilation.
 */
export const BREAKPOINTS = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  "2xl": 1536,
} as const;

export type BreakpointName = keyof typeof BREAKPOINTS;

export const breakpointScreens = {
  sm: `${BREAKPOINTS.sm}px`,
  md: `${BREAKPOINTS.md}px`,
  lg: `${BREAKPOINTS.lg}px`,
  xl: `${BREAKPOINTS.xl}px`,
  "2xl": `${BREAKPOINTS["2xl"]}px`,
} as const;

export const breakpointQueries = {
  sm: `(min-width: ${breakpointScreens.sm})`,
  md: `(min-width: ${breakpointScreens.md})`,
  lg: `(min-width: ${breakpointScreens.lg})`,
  xl: `(min-width: ${breakpointScreens.xl})`,
  "2xl": `(min-width: ${breakpointScreens["2xl"]})`,
} as const;

/** Return the canonical min-width query for a structural breakpoint. */
export function minWidthQuery(name: BreakpointName): string {
  return breakpointQueries[name];
}
