import { readFileSync, readdirSync } from "node:fs";
import { dirname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const sourceRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");

type SourceFile = { relativePath: string; source: string };

function collectProductionSources(directory: string): SourceFile[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const absolutePath = resolve(directory, entry.name);
    if (entry.isDirectory()) {
      return collectProductionSources(absolutePath);
    }
    if (
      !entry.isFile() ||
      !/\.(?:ts|tsx)$/.test(entry.name) ||
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
const sourceByPath = new Map(productionSources.map((file) => [file.relativePath, file.source]));

function sourceFor(relativePath: string): string {
  const source = sourceByPath.get(relativePath);
  if (!source) throw new Error(`Missing production source: ${relativePath}`);
  return source;
}

function headingLevels(source: string): number[] {
  return [...source.matchAll(/<h([1-6])\b/g)].map((match) => Number(match[1]));
}

function openingHeadingTags(source: string): string[] {
  return [...source.matchAll(/<h[23]\b[\s\S]*?>/g)].map((match) => match[0]);
}

const meaningfulContextCallsites = new Set([
  "pages/LoginPage.tsx",
  "pages/RegistrationPage.tsx",
  "pages/admin/AdminLoginPage.tsx",
  "pages/admin/AccountDirectoryPage.tsx",
  "pages/admin/CandidateImportPage.tsx",
  "pages/admin/ExamCandidatesPage.tsx",
  "pages/admin/ExamEditPage.tsx",
  "pages/admin/ExamWorkspacePage.tsx",
  "pages/admin/LearningVideoPage.tsx",
  "pages/admin/OperationsPage.tsx",
  "pages/admin/QuestionImportPage.tsx",
  "components/admin/ReportPage.tsx",
]);

const representativeHeadingSources = [
  "pages/ExamListPage.tsx",
  "pages/LearningListPage.tsx",
  "pages/admin/AdminDashboardPage.tsx",
  "pages/admin/OperationsPage.tsx",
  "pages/admin/ExamCandidatesPage.tsx",
  "pages/admin/ExamWorkspacePage.tsx",
  "components/exam/ExamFocusMode.tsx",
];

describe("visual hierarchy contract", () => {
  it("keeps ordinary page H1 ownership in PageHeader", () => {
    const h1Sources = productionSources
      .filter((file) => /<h1\b/.test(file.source))
      .map((file) => file.relativePath);

    expect(h1Sources).toEqual(["components/page/PageHeader.tsx"]);
    const pageHeaderSource = sourceFor("components/page/PageHeader.tsx");
    expect(pageHeaderSource).toMatch(/<h1\s+className=/);
    expect(pageHeaderSource).toMatch(/<h1[\s\S]*\bmin-w-0\b/);
    expect(pageHeaderSource).toMatch(/<h1[\s\S]*\bbreak-words\b/);
  });

  it("allows the specialized Exam Focus heading exception while keeping representative sections ordered", () => {
    const examFocusSource = sourceFor("components/exam/ExamFocusMode.tsx");
    expect(examFocusSource).toContain("<h2");
    expect(examFocusSource).toContain("<ChapterNumber");

    for (const relativePath of representativeHeadingSources.filter(
      (relativePath) => relativePath !== "components/exam/ExamFocusMode.tsx",
    )) {
      const levels = headingLevels(sourceFor(relativePath));
      expect(levels, `${relativePath} should contain a representative heading`).not.toHaveLength(0);
      expect(levels[0], `${relativePath} starts at an H2 section heading`).toBe(2);
      for (let index = 1; index < levels.length; index += 1) {
        expect(
          levels[index] - levels[index - 1],
          `${relativePath} jumps from H${levels[index - 1]} to H${levels[index]}`,
        ).toBeLessThanOrEqual(1);
      }
    }
  });

  it("keeps representative H2/H3 headings safely wrappable and upright", () => {
    for (const relativePath of representativeHeadingSources.filter(
      (relativePath) => relativePath !== "components/exam/ExamFocusMode.tsx",
    )) {
      for (const tag of openingHeadingTags(sourceFor(relativePath))) {
        expect(tag, `${relativePath} heading is missing min-w-0`).toContain("min-w-0");
        expect(tag, `${relativePath} heading is missing break-words`).toContain("break-words");
        expect(tag, `${relativePath} heading is italic`).not.toMatch(/\bitalic\b/);
      }
    }
  });

  it("keeps page context labels meaningful and explicitly allowlisted", () => {
    const contextCallsites = productionSources.flatMap(({ relativePath, source }) => {
      const matches = [...source.matchAll(/<PageHeader\b[\s\S]*?>/g)].filter((match) =>
        /\b(?:eyebrow|context)\s*=/.test(match[0]),
      );
      return matches.map(() => relativePath);
    });

    expect(new Set(contextCallsites)).toEqual(meaningfulContextCallsites);
    expect(contextCallsites).not.toContain("components/page/PageHeader.tsx");
  });

  it("does not ship production italic classes or ordinal page markers", () => {
    const proseItalicAllowlist: string[] = [];
    const italicSources = productionSources.flatMap(({ relativePath, source }) => {
      if (proseItalicAllowlist.includes(relativePath)) return [];
      return /(?:\bitalic\b|font-style\s*:\s*italic)/.test(source) ? [relativePath] : [];
    });
    expect(italicSources).toEqual([]);

    const chapterNumberSources = productionSources
      .filter(({ source }) => /(?:<ChapterNumber\b|from ["'][^"']*ChapterNumber)/.test(source))
      .map(({ relativePath }) => relativePath)
      .filter(
        (relativePath) =>
          relativePath !== "components/editorial/ChapterNumber.tsx" &&
          relativePath !== "components/editorial/index.ts",
      );
    expect(chapterNumberSources).toEqual(["components/exam/ExamFocusMode.tsx"]);
  });
});
