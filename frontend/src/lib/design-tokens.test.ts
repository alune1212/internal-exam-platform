import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

import { BREAKPOINTS, breakpointQueries, breakpointScreens } from "./breakpoints";
import { designTokens } from "./design-tokens";

const frontendRoot = process.cwd().endsWith("/frontend")
  ? process.cwd()
  : resolve(process.cwd(), "frontend");
const cssSource = readFileSync(resolve(frontendRoot, "src/index.css"), "utf8");
const tailwindSource = readFileSync(resolve(frontendRoot, "tailwind.config.ts"), "utf8");
const mediaQuerySource = readFileSync(resolve(frontendRoot, "src/lib/use-media-query.ts"), "utf8");
const breakpointSource = readFileSync(resolve(frontendRoot, "src/lib/breakpoints.ts"), "utf8");

const cssTokenNames = new Set(
  [...cssSource.matchAll(/--([a-z0-9-]+)\s*:/g)].map((match) => match[1]),
);

function cssTokenName(reference: string): string {
  const match = reference.match(/^var\(--([a-z0-9-]+)\)$/);
  if (!match) {
    throw new Error(`Expected a CSS variable reference, received ${reference}`);
  }
  return match[1];
}

function cssColor(tokenName: string): string {
  const match = cssSource.match(new RegExp(`--${tokenName}\\s*:\\s*(#[0-9a-fA-F]{3,8})`));
  if (!match) throw new Error(`Expected hex color token --${tokenName}`);
  return match[1];
}

function channelToLinear(channel: number): number {
  const normalized = channel / 255;
  return normalized <= 0.03928 ? normalized / 12.92 : ((normalized + 0.055) / 1.055) ** 2.4;
}

function relativeLuminance(hex: string): number {
  const normalized = hex.slice(1);
  const channels =
    normalized.length === 3
      ? normalized.split("").map((channel) => Number.parseInt(`${channel}${channel}`, 16))
      : normalized.match(/../g)?.map((channel) => Number.parseInt(channel, 16));
  if (!channels || channels.length < 3) throw new Error(`Invalid color ${hex}`);
  const [red, green, blue] = channels;
  return (
    0.2126 * channelToLinear(red) + 0.7152 * channelToLinear(green) + 0.0722 * channelToLinear(blue)
  );
}

function contrastRatio(foreground: string, background: string): number {
  const foregroundLuminance = relativeLuminance(foreground);
  const backgroundLuminance = relativeLuminance(background);
  const lighter = Math.max(foregroundLuminance, backgroundLuminance);
  const darker = Math.min(foregroundLuminance, backgroundLuminance);
  return (lighter + 0.05) / (darker + 0.05);
}

describe("design token ownership", () => {
  it("keeps every exported token as an exact CSS variable reference", () => {
    const values = Object.values(designTokens);
    expect(new Set(Object.keys(designTokens)).size).toBe(Object.keys(designTokens).length);

    for (const value of values) {
      const tokenName = cssTokenName(value);
      expect(cssTokenNames, `missing CSS token --${tokenName}`).toContain(tokenName);
    }
  });

  it("retains the complete existing palette, radius, shadow, and font contracts", () => {
    const expectedTokens = [
      "canvas",
      "canvas-warm",
      "surface-card",
      "surface-elev",
      "ink",
      "ink-soft",
      "body",
      "muted",
      "hairline",
      "hairline-soft",
      "footer",
      "footer-soft",
      "success",
      "warning",
      "error",
      "ink-red",
      "ink-blue",
      "success-on-dark",
      "error-on-dark",
      "radius-pill",
      "radius-lg",
      "radius-md",
      "radius-sm",
      "shadow-card",
      "shadow-pop",
      "shadow-elevate",
      "overlay",
      "font-display",
      "font-body",
      "font-mono",
    ];

    for (const tokenName of expectedTokens) {
      expect(cssTokenNames, `missing governed token --${tokenName}`).toContain(tokenName);
    }

    expect(cssSource).toContain('"Iowan Old Style"');
    expect(cssSource).toContain('"Palatino Linotype"');
    expect(cssSource).toContain('"Songti SC"');
    expect(cssSource).toContain('"PingFang SC"');
    expect(cssSource).toContain('"Microsoft YaHei"');
    expect(cssSource).toContain('"Cascadia Mono"');
    expect(cssSource).not.toMatch(/Source Serif 4|Source Serif Pro|\bInter\b|JetBrains Mono/);
  });

  it("exposes semantic typography, spacing, focus, motion, and layer tokens", () => {
    const requiredTokenNames = [
      "text-display-2xl",
      "text-display-xl",
      "text-display-lg",
      "text-display-md",
      "text-display-sm",
      "text-body-lg",
      "text-body",
      "text-body-sm",
      "text-caption",
      "leading-display-2xl",
      "leading-display-xl",
      "leading-display-lg",
      "leading-display-md",
      "leading-display-sm",
      "leading-body-lg",
      "leading-body",
      "leading-body-sm",
      "leading-caption",
      "space-page-inline",
      "space-page-inline-lg",
      "space-page-block",
      "space-section",
      "space-section-lg",
      "space-panel",
      "space-field",
      "space-field-compact",
      "space-control-x",
      "space-control-y",
      "space-control-gap",
      "focus-ring-width",
      "focus-ring-color",
      "focus-ring-offset",
      "focus-ring-radius",
      "motion-duration-fast",
      "motion-duration-normal",
      "motion-duration-slow",
      "motion-duration-shimmer",
      "motion-duration-pulse",
      "motion-ease-linear",
      "motion-ease-standard",
      "z-content",
      "z-sticky",
      "z-overlay",
      "z-modal",
      "z-toast",
    ];

    for (const tokenName of requiredTokenNames) {
      expect(cssTokenNames, `missing semantic token --${tokenName}`).toContain(tokenName);
    }
    expect(tailwindSource).toContain('"var(--text-display-2xl)"');
    expect(tailwindSource).toContain('"var(--leading-display-2xl)"');
    expect(tailwindSource).toContain('"page-inline": "var(--space-page-inline)"');
    expect(tailwindSource).toContain('"var(--motion-duration-shimmer)"');
    expect(tailwindSource).toContain('content: "var(--z-content)"');
  });

  it("keeps breakpoint consumers on the single typed map", () => {
    expect(breakpointScreens.md).toBe(`${BREAKPOINTS.md}px`);
    expect(breakpointQueries.lg).toBe(`(min-width: ${BREAKPOINTS.lg}px)`);
    expect(tailwindSource).toContain('import { breakpointScreens } from "./src/lib/breakpoints";');
    expect(tailwindSource).toContain("screens: breakpointScreens");
    expect(mediaQuerySource).toContain("breakpointQueries");
    expect(mediaQuerySource).toContain("minWidthQuery");
    expect(mediaQuerySource).not.toMatch(/768px|1024px/);
    expect(breakpointSource).toContain("as const");
  });

  it("keeps key text/status pairs at readable contrast", () => {
    expect(contrastRatio(cssColor("ink"), cssColor("canvas"))).toBeGreaterThanOrEqual(7);
    expect(contrastRatio(cssColor("body"), cssColor("canvas"))).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(cssColor("success"), cssColor("canvas"))).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(cssColor("error"), cssColor("canvas"))).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(cssColor("canvas"), cssColor("footer"))).toBeGreaterThanOrEqual(15);
  });

  it("keeps decorative assets and fonts offline-safe", () => {
    const governedSource = `${cssSource}\n${tailwindSource}\n${mediaQuerySource}`;
    expect(governedSource).not.toMatch(/url\(\s*["']?https?:\/\//i);
    expect(governedSource).not.toMatch(/@import\s+url\(/i);
    expect(cssSource).toContain("[data-admin-login-pattern]");
    expect(cssSource).toContain("--texture-admin-login-dot");
    expect(cssSource).toContain("--texture-admin-login-dot-size");
    expect(cssSource).toContain("--texture-admin-login-size");
  });
});
