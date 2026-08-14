import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const frontendRoot = process.cwd().endsWith("/frontend")
  ? process.cwd()
  : resolve(process.cwd(), "frontend");
const indexSource = readFileSync(resolve(frontendRoot, "src/index.css"), "utf8");
const reducedMotionStart = indexSource.indexOf("@media (prefers-reduced-motion: reduce)");
const reducedMotionSource = indexSource.slice(reducedMotionStart);

describe("motion and reduced-motion CSS contract", () => {
  it("keeps motion values named in the root token source", () => {
    expect(indexSource).toMatch(
      /--motion-duration-(?:instant|fast|normal|slow|shimmer|pulse):\s*[^;]+;/,
    );
    expect(indexSource).toContain("--motion-ease-linear:");
    expect(indexSource).toContain("--motion-ease-standard:");
    expect(indexSource).toContain("--focus-ring-width:");
    expect(indexSource).toContain("--focus-ring-color:");
    expect(indexSource).toContain("--focus-ring-offset:");

    const rootEnd = indexSource.indexOf("\n  }\n\n  * {", indexSource.indexOf(":root"));
    const nonRootSource = rootEnd >= 0 ? indexSource.slice(rootEnd) : indexSource;
    expect(nonRootSource).not.toMatch(
      /(?:animation(?:-duration|-delay|-timing-function)?|transition(?:-duration|-delay|-timing-function)?)\s*:\s*[^;{}]*(?:\d+(?:\.\d+)?m?s|(?:^|[\s,(])ease(?:-in(?:-out)?|-out)?\b|cubic-bezier\()/i,
    );
  });

  it("keeps headings upright and safely wrappable", () => {
    const headingBlock = indexSource.match(/h1,\s*h2,\s*h3\s*{([\s\S]*?)\n\s*}/)?.[1] ?? "";
    expect(headingBlock).toContain("font-style: normal;");
    expect(headingBlock).toContain("min-width: 0;");
    expect(headingBlock).toContain("overflow-wrap: anywhere;");
    expect(headingBlock).toContain("word-break: break-word;");
  });

  it("clips only page-edge paint after layout overflow is measured independently", () => {
    const containmentBlock = indexSource.match(/html,\s*body\s*{([\s\S]*?)\n\s*}/)?.[1] ?? "";
    expect(containmentBlock).toContain("overflow-x: clip;");
    expect(containmentBlock).not.toContain("overflow-x: hidden;");
  });

  it("uses the canonical focus ring with no transition delay", () => {
    const focusBlock = indexSource.match(/:focus-visible\s*{([\s\S]*?)\n\s*}/)?.[1] ?? "";
    expect(focusBlock).toContain("outline: var(--focus-ring-width) solid var(--focus-ring-color);");
    expect(focusBlock).toContain("outline-offset: var(--focus-ring-offset);");
    expect(focusBlock).toContain("transition: none !important;");
  });

  it("staticizes nonessential motion while preserving loading and critical state cues", () => {
    expect(reducedMotionStart).toBeGreaterThanOrEqual(0);
    expect(reducedMotionSource).toContain("transition-duration: var(--motion-duration-instant)");
    expect(reducedMotionSource).toContain("transition-delay: var(--motion-duration-instant)");
    expect(reducedMotionSource).toContain("[data-stagger] > *");
    expect(reducedMotionSource).toContain(".animate-shimmer");
    expect(reducedMotionSource).toContain(".animate-pulse");
    expect(reducedMotionSource).toContain(".animate-spin");
    expect(reducedMotionSource).toContain(".duration-pulse");
    expect(reducedMotionSource).toContain('[class*="animate-in"]');
    expect(reducedMotionSource).toContain('[class*="animate-out"]');
    expect(reducedMotionSource).toContain('[class*="zoom-in"]');
    expect(reducedMotionSource).toContain('[class*="zoom-out"]');
    expect(reducedMotionSource).toContain('[class*="slide-in-from"]');
    expect(reducedMotionSource).toContain('[class*="slide-out-to"]');
    expect(reducedMotionSource).toContain("animation: none !important;");
    expect(reducedMotionSource).toContain("transform: none !important;");
    expect(reducedMotionSource).toContain("background-position: 50% 0;");
    expect(reducedMotionSource).toContain("transition: none !important;");
  });
});
