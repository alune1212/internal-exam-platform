import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const sourceRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");

const motionSources = {
  timer: resolve(sourceRoot, "components/exam/Timer.tsx"),
  dialog: resolve(sourceRoot, "components/ui/dialog.tsx"),
  sheet: resolve(sourceRoot, "components/ui/sheet.tsx"),
};

describe("shared motion contract", () => {
  it("does not reintroduce raw duration, easing, layer, or inline animation values", () => {
    for (const path of Object.values(motionSources)) {
      const source = readFileSync(path, "utf8");
      expect(source).not.toMatch(/duration-\d+/);
      expect(source).not.toContain("ease-out");
      expect(source).not.toMatch(/z-\d+/);
      expect(source).not.toContain("animationDuration");
    }
  });

  it("keeps critical timer feedback textual, colored, and motion-safe", () => {
    const source = readFileSync(motionSources.timer, "utf8");
    expect(source).toContain("motion-safe:animate-pulse");
    expect(source).toContain("duration-pulse");
    expect(source).toContain("text-error");
    expect(source).toContain("剩余时间不足 5 分钟。");
  });

  it("assigns semantic overlay and modal layers to dialog and sheet surfaces", () => {
    for (const key of ["dialog", "sheet"] as const) {
      const source = readFileSync(motionSources[key], "utf8");
      expect(source).toContain("z-overlay");
      expect(source).toContain("z-modal");
      expect(source).toContain("duration-normal");
      expect(source).toContain("ease-standard");
    }
  });
});
