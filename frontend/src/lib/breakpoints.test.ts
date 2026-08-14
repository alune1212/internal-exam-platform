import { describe, expect, it } from "vitest";

import { BREAKPOINTS, breakpointQueries, breakpointScreens, minWidthQuery } from "./breakpoints";

describe("structural breakpoints", () => {
  it("keeps the supported screen map ordered and typed", () => {
    expect(Object.keys(BREAKPOINTS)).toEqual(["sm", "md", "lg", "xl", "2xl"]);
    expect(BREAKPOINTS.sm).toBeLessThan(BREAKPOINTS.md);
    expect(BREAKPOINTS.md).toBeLessThan(BREAKPOINTS.lg);
    expect(BREAKPOINTS.lg).toBeLessThan(BREAKPOINTS.xl);
    expect(BREAKPOINTS.xl).toBeLessThan(BREAKPOINTS["2xl"]);
  });

  it("derives Tailwind screens and media queries from the same widths", () => {
    for (const name of Object.keys(BREAKPOINTS) as Array<keyof typeof BREAKPOINTS>) {
      expect(breakpointScreens[name]).toBe(`${BREAKPOINTS[name]}px`);
      expect(breakpointQueries[name]).toBe(`(min-width: ${BREAKPOINTS[name]}px)`);
      expect(minWidthQuery(name)).toBe(breakpointQueries[name]);
    }
  });
});
