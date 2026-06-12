import { describe, expect, it } from "vitest";

import { designTokens } from "./design-tokens";

const EXPECTED_KEYS = [
  "canvas",
  "canvasWarm",
  "surfaceCard",
  "surfaceElev",
  "ink",
  "inkSoft",
  "body",
  "muted",
  "hairline",
  "hairlineSoft",
  "footer",
  "footerSoft",
  "success",
  "warning",
  "error",
  "radiusPill",
  "radiusLg",
  "radiusMd",
  "radiusSm",
  "shadowCard",
  "shadowPop",
  "shadowElevate",
  "fontDisplay",
  "fontBody",
  "fontMono",
] as const;

describe("designTokens", () => {
  it("exports every expected key exactly once", () => {
    const actualKeys = Object.keys(designTokens).sort();
    const expectedKeys = [...EXPECTED_KEYS].sort();
    expect(actualKeys).toEqual(expectedKeys);
  });

  it("exports only string values", () => {
    for (const [key, value] of Object.entries(designTokens)) {
      expect(typeof value, `token "${key}"`).toBe("string");
      expect(value.length, `token "${key}"`).toBeGreaterThan(0);
    }
  });

  it("color tokens use hex notation (no HSL, no rgb)", () => {
    const hexTokens: Array<keyof typeof designTokens> = [
      "canvas",
      "canvasWarm",
      "surfaceCard",
      "surfaceElev",
      "ink",
      "inkSoft",
      "body",
      "muted",
      "hairline",
      "hairlineSoft",
      "footer",
      "footerSoft",
      "success",
      "warning",
      "error",
    ];
    for (const key of hexTokens) {
      expect(designTokens[key]).toMatch(/^#[0-9a-fA-F]{3,8}$/);
    }
  });

  it("radius tokens end in px or unitless", () => {
    const radiusTokens: Array<keyof typeof designTokens> = [
      "radiusPill",
      "radiusLg",
      "radiusMd",
      "radiusSm",
    ];
    for (const key of radiusTokens) {
      expect(designTokens[key]).toMatch(/^(\d+(\.\d+)?(px|rem|em)|9999px)$/);
    }
  });

  it("font tokens are CSS font-family stacks starting with a quoted family", () => {
    const fontTokens: Array<keyof typeof designTokens> = ["fontDisplay", "fontBody", "fontMono"];
    for (const key of fontTokens) {
      expect(designTokens[key]).toMatch(/^"[^"]+"/);
    }
  });
});
