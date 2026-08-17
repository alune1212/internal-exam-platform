import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

function luminance(hex: string) {
  const channels = hex
    .slice(1)
    .match(/.{2}/g)!
    .map((value) => Number.parseInt(value, 16) / 255)
    .map((value) => (value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4));
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

function contrast(first: string, second: string) {
  const [lighter, darker] = [luminance(first), luminance(second)].sort((a, b) => b - a);
  return (lighter + 0.05) / (darker + 0.05);
}

describe("representative accessibility contract", () => {
  it("keeps primary body and status colors readable on their common surfaces", () => {
    expect(contrast("#374151", "#ffffff")).toBeGreaterThanOrEqual(4.5);
    expect(contrast("#166534", "#ffffff")).toBeGreaterThanOrEqual(4.5);
    expect(contrast("#b91c1c", "#ffffff")).toBeGreaterThanOrEqual(4.5);
  });

  it("allows responsive zoom and reserves space for mobile fixed controls", () => {
    const index = readFileSync(resolve(process.cwd(), "index.html"), "utf8");
    const practice = readFileSync(resolve(process.cwd(), "src/pages/PracticePage.tsx"), "utf8");
    expect(index).toMatch(
      /name="viewport"\s+content="width=device-width, initial-scale=1\.0, viewport-fit=cover"/,
    );
    expect(index).not.toMatch(/maximum-scale|user-scalable\s*=\s*no/i);
    expect(practice).toContain("pb-[calc(6rem+env(safe-area-inset-bottom))]");
    expect(practice).toContain("fixed inset-x-0 bottom-0");
    expect(practice).toContain("pb-[max(var(--space-inline),env(safe-area-inset-bottom))]");
  });
});
