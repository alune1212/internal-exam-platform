import { readFileSync, readdirSync } from "node:fs";
import { dirname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { productGlossary } from "./pageCopy";
import {
  findDecorativeBilingualLabels,
  formatPresentationPolicyViolations,
  inspectPresentationSource,
  inspectPresentationSources,
  isEnglishLabelAllowed,
  presentationPolicyAllowlist,
  type PresentationSource,
} from "./presentationPolicy";

const sourceRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");

function collectProductionSources(directory: string): PresentationSource[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const absolutePath = resolve(directory, entry.name);
    if (entry.isDirectory()) return collectProductionSources(absolutePath);
    if (
      !entry.isFile() ||
      !/\.(?:ts|tsx|css)$/.test(entry.name) ||
      /\.test\.(?:ts|tsx)$/.test(entry.name) ||
      entry.name.endsWith(".d.ts") ||
      entry.name.includes("__tests__")
    ) {
      return [];
    }
    return [
      {
        relativePath: relative(sourceRoot, absolutePath).replace(/\\/g, "/"),
        source: readFileSync(absolutePath, "utf8"),
      },
    ];
  });
}

const productionSources = collectProductionSources(sourceRoot);

describe("presentation source policy", () => {
  it("passes the current production source with explicit migration debt only", () => {
    const violations = inspectPresentationSources(productionSources);
    expect(
      violations,
      violations.length ? formatPresentationPolicyViolations(violations) : undefined,
    ).toEqual([]);
  });

  it.each([
    ["raw colors", '<div className="text-[#ff00aa]" />', "raw-color"],
    [
      "font assets",
      '@font-face { font-family: "New Font"; src: url("font.woff2"); }',
      "font-asset",
    ],
    ["arbitrary type", '<p className="tracking-[0.22em]" />', "arbitrary-typography"],
    ["independent frame", '<div className="max-w-5xl" />', "independent-frame"],
    [
      "duplicate surface",
      '<section className="rounded-lg border bg-canvas p-4"><div className="rounded-md border bg-canvas p-4" /></section>',
      "duplicate-surface",
    ],
    [
      "unsupported motion",
      `<div className="${["duration-", "[450ms]"].join("")}" />`,
      "unsupported-motion",
    ],
    ["workbench stagger", '<PageShell density="workbench" stagger />', "workbench-stagger"],
    ["decorative bilingual label", "<span>STATUS · 状态</span>", "decorative-bilingual"],
  ])("rejects representative prohibited %s fixtures", (_label, source, rule) => {
    const violations = inspectPresentationSource({
      relativePath: "fixtures/presentation-policy-prohibited.tsx",
      source,
    });
    expect(violations.map((violation) => violation.rule)).toContain(rule);
  });

  it("keeps explicit exceptions narrow and reasoned", () => {
    expect(presentationPolicyAllowlist.canonicalOwners).toEqual({
      css: "index.css",
      identityPalette: "lib/pastelPalette.ts",
      breakpoints: "lib/breakpoints.ts",
    });
    expect(presentationPolicyAllowlist.arbitraryTypographyExceptions).toEqual([]);
    expect(presentationPolicyAllowlist.pageWidthExceptions).toHaveLength(8);
    expect(presentationPolicyAllowlist.rawColorClassExceptions.length).toBeGreaterThan(0);
    expect(presentationPolicyAllowlist.completeSurfaceExceptions).toHaveLength(1);
    expect(presentationPolicyAllowlist.bilingualExceptions.size).toBe(0);
    expect(presentationPolicyAllowlist.workbenchStaggerExceptions.size).toBe(0);
    expect(
      [
        ...presentationPolicyAllowlist.pageWidthExceptions,
        ...presentationPolicyAllowlist.rawColorClassExceptions,
        ...presentationPolicyAllowlist.completeSurfaceExceptions,
      ].every((entry) => entry.reason.length > 0 && entry.patterns.length > 0),
    ).toBe(true);
  });

  it("keeps local exceptions pattern-bound instead of path-wide", () => {
    const widthViolations = inspectPresentationSource({
      relativePath: "components/page/PageHeader.tsx",
      source: '<p className="max-w-3xl" /><div className="max-w-5xl" />',
    });
    expect(widthViolations.filter((violation) => violation.rule === "independent-frame")).toEqual([
      expect.objectContaining({ match: "max-w-5xl" }),
    ]);

    const surfaceViolations = inspectPresentationSource({
      relativePath: "pages/PracticePage.tsx",
      source: `
        <div className="rounded-pill border border-footer bg-footer p-2 shadow-elevate" />
        <div className="rounded-lg border border-hairline bg-canvas p-4 shadow-card" />
      `,
    });
    expect(surfaceViolations.filter((violation) => violation.rule === "duplicate-surface")).toEqual(
      [expect.objectContaining({ match: expect.stringContaining("rounded-lg") })],
    );
  });

  it("allows state/data variants and verified safe-area/grid exceptions", () => {
    const source = inspectPresentationSource({
      relativePath: "components/focus/AllowedState.tsx",
      source: `
        <div
          className="aria-[invalid=true]:border-error data-[state=success]:border-success w-[calc(100%-env(safe-area-inset-left))] grid-cols-[1fr_auto]"
        />
      `,
    });
    expect(source).toEqual([]);
  });

  it("enforces the canonical English allowlist and catches decorative bilingual labels", () => {
    expect(isEnglishLabelAllowed("Internal Exam Platform")).toBe(true);
    expect(isEnglishLabelAllowed("Excel")).toBe(true);
    expect(isEnglishLabelAllowed("ID")).toBe(true);
    expect(isEnglishLabelAllowed("DASHBOARD")).toBe(false);
    expect(findDecorativeBilingualLabels("DASHBOARD · 仪表盘")).toEqual(["DASHBOARD · 仪表盘"]);
    expect(findDecorativeBilingualLabels("Internal Exam Platform")).toEqual([]);
  });

  it("keeps the critical Chinese glossary distinctions available to policy consumers", () => {
    expect(productGlossary).toMatchObject({
      user: "用户",
      examTaker: "应考人员",
      saveAnswer: "保存答案",
      submitExam: "交卷",
      stayInExam: "留在考试",
      leaveExam: "离开考试",
    });
  });
});
