import { englishAllowlist } from "./pageCopy";

/**
 * Source-policy rules for the presentation contract.
 *
 * This module deliberately operates on source text rather than generated CSS.
 * The production-source test can therefore fail before a locally configured
 * Tailwind build happens to hide a drift.  The CSS root, typed breakpoint map,
 * and identity palette remain explicit owners; the small debt lists below are
 * temporary migration records and are intentionally path- and pattern-bound.
 */
export type PresentationPolicyRule =
  | "raw-color"
  | "font-asset"
  | "arbitrary-typography"
  | "independent-frame"
  | "duplicate-surface"
  | "unsupported-motion"
  | "workbench-stagger"
  | "decorative-bilingual";

export interface PresentationSource {
  relativePath: string;
  source: string;
}

export interface PresentationPolicyViolation {
  rule: PresentationPolicyRule;
  relativePath: string;
  line: number;
  match: string;
  message: string;
}

interface AllowlistEntry {
  path: string;
  patterns: readonly RegExp[];
  reason: string;
}

const canonicalCssOwner = "index.css";
const identityPaletteOwner = "lib/pastelPalette.ts";
const typedBreakpointOwner = "lib/breakpoints.ts";

/** No arbitrary type or tracking debt remains in production consumers. */
const arbitraryTypographyExceptions: readonly AllowlistEntry[] = [];

/** Verified local measures that do not claim ordinary page-frame ownership. */
const pageWidthExceptions: readonly AllowlistEntry[] = [
  {
    path: "components/editorial/EmptyState.tsx",
    patterns: [/max-w-md/],
    reason: "Empty-state prose measure is a local content constraint",
  },
  {
    path: "components/layout/UnsupportedBrowserNotice.tsx",
    patterns: [/max-w-xl/],
    reason: "Browser-support recovery notice uses a local readable measure",
  },
  {
    path: "components/page/PageHeader.tsx",
    patterns: [/max-w-3xl/],
    reason: "Header description measure is not a page-frame owner",
  },
  {
    path: "components/ui/dialog.tsx",
    patterns: [/max-w-lg/],
    reason: "Dialog viewport measure belongs to the overlay primitive",
  },
  {
    path: "components/ui/sheet.tsx",
    patterns: [/max-w-sm/],
    reason: "Sheet viewport measure belongs to the overlay primitive",
  },
  {
    path: "features/exam/ExamTakingWorkspace.tsx",
    patterns: [/max-w-md/],
    reason: "Focus navigator bottom control uses a local viewport measure",
  },
  {
    path: "pages/PracticePage.tsx",
    patterns: [/max-w-md/],
    reason: "Active-practice mobile control bar uses a local viewport measure",
  },
  {
    path: "pages/admin/QuestionListPage.tsx",
    patterns: [/sm:max-w-3xl/],
    reason: "Question editor overlay uses a wider local dialog measure",
  },
];

const rawColorClassExceptions: readonly AllowlistEntry[] = [
  {
    path: "components/editorial/ChapterNumber.tsx",
    patterns: [/bg-current/],
    reason: "Ordinal rule inherits the governed current text color",
  },
  {
    path: "components/layout/AdminSideRail.tsx",
    patterns: [/hover:bg-white\/10/],
    reason: "Dark admin rail hover affordance uses its deep-chrome light ink",
  },
  {
    path: "components/page/PageState.tsx",
    patterns: [/bg-transparent/],
    reason: "Inherited async state intentionally keeps its parent surface",
  },
  {
    path: "components/ui/button-variants.ts",
    patterns: [/bg-transparent/],
    reason: "Ghost/link actions intentionally expose the canvas behind them",
  },
  {
    path: "components/ui/control-base.ts",
    patterns: [/file:bg-transparent/],
    reason: "Native file button reset is a control-state exception",
  },
  {
    path: "components/ui/spinner.tsx",
    patterns: [/border-current/, /border-r-transparent/],
    reason: "Spinner uses currentColor and a transparent segment for its shape",
  },
  {
    path: "pages/LearningVideoPage.tsx",
    patterns: [/bg-black/],
    reason: "Video media surface uses deep chrome behind letterboxing",
  },
];

/** Components that intentionally own a complete governed surface. */
const surfaceOwnerPaths = new Set([
  "components/admin/ExamContextNav.tsx",
  "components/admin/MetricCard.tsx",
  "components/admin/SimpleDataTable.tsx",
  "components/exam/ExamFocusMode.tsx",
  "components/exam/ExamNavigator.tsx",
  "components/layout/UnsupportedBrowserNotice.tsx",
  "features/exam/ExamTakingWorkspace.tsx",
  "components/page/PageSection.tsx",
  "components/page/PageState.tsx",
  "components/ui/alert.tsx",
  "components/ui/card.tsx",
  "components/ui/table.tsx",
  "components/ui/dialog.tsx",
  "components/ui/sheet.tsx",
]);

const completeSurfaceExceptions: readonly AllowlistEntry[] = [
  {
    path: "pages/PracticePage.tsx",
    patterns: [/rounded-pill border border-footer bg-footer p-2 shadow-elevate/],
    reason: "Active-practice mobile control bar is dedicated Exam Focus chrome",
  },
];

/** Chinese-first copy and motion convergence leave no route-level bypasses. */
const bilingualExceptions = new Set<string>();
const workbenchStaggerExceptions = new Set<string>();

const namedMotionClasses = new Set([
  "animate-in",
  "animate-out",
  "animate-pulse",
  "animate-shimmer",
  "animate-spin",
  "duration-fast",
  "duration-instant",
  "duration-normal",
  "duration-pulse",
  "duration-shimmer",
  "duration-slow",
  "ease-linear",
  "ease-standard",
  "transition-colors",
  "transition-opacity",
  "transition-transform",
]);

export const presentationPolicyAllowlist = {
  canonicalOwners: {
    css: canonicalCssOwner,
    identityPalette: identityPaletteOwner,
    breakpoints: typedBreakpointOwner,
  },
  arbitraryTypographyExceptions,
  pageWidthExceptions,
  rawColorClassExceptions,
  surfaceOwnerPaths,
  completeSurfaceExceptions,
  bilingualExceptions,
  workbenchStaggerExceptions,
  english: {
    productNames: englishAllowlist.productNames,
    operationalTerms: englishAllowlist.operationalTerms,
  },
} as const;

export function normalizeSourcePath(relativePath: string): string {
  const normalized = relativePath.replace(/\\/g, "/").replace(/^\.\//, "");
  const sourceIndex = normalized.lastIndexOf("/src/");
  if (sourceIndex >= 0) return normalized.slice(sourceIndex + 5);
  return normalized.replace(/^src\//, "");
}

function lineNumber(source: string, offset: number): number {
  return source.slice(0, offset).split("\n").length;
}

function entryAllows(entries: readonly AllowlistEntry[], path: string, match: string): boolean {
  return entries.some(
    (entry) => entry.path === path && entry.patterns.some((pattern) => pattern.test(match)),
  );
}

function addMatches(
  violations: PresentationPolicyViolation[],
  sourceFile: PresentationSource,
  rule: PresentationPolicyRule,
  pattern: RegExp,
  message: string,
  allows: (match: string) => boolean = () => false,
) {
  const source = sourceFile.source;
  for (const match of source.matchAll(
    new RegExp(pattern.source, pattern.flags.includes("g") ? pattern.flags : `${pattern.flags}g`),
  )) {
    const value = match[0];
    if (allows(value)) continue;
    const offset = match.index ?? 0;
    violations.push({
      rule,
      relativePath: normalizeSourcePath(sourceFile.relativePath),
      line: lineNumber(source, offset),
      match: value,
      message,
    });
  }
}

function isSafeLayoutExpression(match: string): boolean {
  return /safe-area|env\(|dvh|svh|lvh|grid/i.test(match);
}

function sourceClassTokens(source: string): Array<{ token: string; offset: number }> {
  const tokens: Array<{ token: string; offset: number }> = [];
  const classPattern = /(?:className|class)\s*=\s*(?:"([^"]*)"|'([^']*)'|`([^`]*)`)/g;
  for (const match of source.matchAll(classPattern)) {
    const classText = match[1] ?? match[2] ?? match[3] ?? "";
    const classOffset = (match.index ?? 0) + match[0].indexOf(classText);
    for (const tokenMatch of classText.matchAll(/[^\s]+/g)) {
      tokens.push({ token: tokenMatch[0], offset: classOffset + (tokenMatch.index ?? 0) });
    }
  }
  return tokens;
}

function isCompleteSurfaceClass(classText: string): boolean {
  const hasRadius = /\brounded(?:-[^\s]+)?\b/.test(classText);
  const hasBorder = /\bborder(?:-[^\s]+)?\b/.test(classText);
  const hasBackground = /\bbg-[^\s]+\b/.test(classText);
  const hasElevation = /\bshadow-(?:card|pop|elevate|sticky|focus|overlay|popover)\b/.test(
    classText,
  );
  const hasPadding = /\b(?:p|px|py|pt|pb|pl|pr)-[^\s]+\b/.test(classText);
  return hasRadius && hasBorder && (hasBackground || hasElevation) && hasPadding;
}

function scanSurfaceOwners(
  sourceFile: PresentationSource,
  violations: PresentationPolicyViolation[],
) {
  const path = normalizeSourcePath(sourceFile.relativePath);
  if (surfaceOwnerPaths.has(path)) return;

  const classPattern = /(?:className|class)\s*=\s*(?:"([^"]*)"|'([^']*)'|`([^`]*)`)/g;
  for (const match of sourceFile.source.matchAll(classPattern)) {
    const classText = match[1] ?? match[2] ?? match[3] ?? "";
    if (!isCompleteSurfaceClass(classText)) continue;
    if (entryAllows(completeSurfaceExceptions, path, classText)) continue;
    const offset = match.index ?? 0;
    violations.push({
      rule: "duplicate-surface",
      relativePath: path,
      line: lineNumber(sourceFile.source, offset),
      match: classText,
      message:
        "Complete surface treatment belongs to a shared surface owner; use a plain wrapper or an explicit exception.",
    });
  }
}

function scanClassPolicy(
  sourceFile: PresentationSource,
  violations: PresentationPolicyViolation[],
) {
  const path = normalizeSourcePath(sourceFile.relativePath);
  const tokens = sourceClassTokens(sourceFile.source);

  for (const { token, offset } of tokens) {
    const baseToken = token.slice(token.lastIndexOf(":") + 1);

    if (/^(?:text|leading|tracking|font)-\[[^\]]+\]$/.test(baseToken)) {
      if (
        !entryAllows(arbitraryTypographyExceptions, path, token) &&
        !entryAllows(arbitraryTypographyExceptions, path, baseToken)
      ) {
        violations.push({
          rule: "arbitrary-typography",
          relativePath: path,
          line: lineNumber(sourceFile.source, offset),
          match: token,
          message: "Use a semantic type or tracking alias owned by index.css.",
        });
      }
    }

    if (
      /^(?:max-w-(?:xs|sm|md|lg|xl|2xl|3xl|4xl|5xl|6xl|7xl)|(?:w|min-w)-\[[^\]]+\])$/.test(
        baseToken,
      ) &&
      !isSafeLayoutExpression(baseToken) &&
      !entryAllows(pageWidthExceptions, path, token) &&
      !entryAllows(pageWidthExceptions, path, baseToken)
    ) {
      violations.push({
        rule: "independent-frame",
        relativePath: path,
        line: lineNumber(sourceFile.source, offset),
        match: token,
        message: "Use the PageShell/page-frame role or a documented local data/overlay measure.",
      });
    }

    if (/^(?:min|max)-\[[^\]]+\]:/.test(token)) {
      violations.push({
        rule: "independent-frame",
        relativePath: path,
        line: lineNumber(sourceFile.source, offset),
        match: token,
        message: "Use the typed breakpoint map instead of an independent responsive threshold.",
      });
    }

    if (
      /^(?:animate|duration|ease)-\[[^\]]+\]$/.test(baseToken) ||
      /^duration-\d+$/.test(baseToken)
    ) {
      violations.push({
        rule: "unsupported-motion",
        relativePath: path,
        line: lineNumber(sourceFile.source, offset),
        match: token,
        message:
          "Use a named motion duration/easing alias or a reduced-motion-safe state treatment.",
      });
    }

    if (
      /^(?:animate|duration|ease|transition)-/.test(baseToken) &&
      !namedMotionClasses.has(baseToken)
    ) {
      const isPropertyTransition = /^transition-\[[^\]]+\]$/.test(baseToken);
      if (
        !isPropertyTransition ||
        !/\b(?:opacity|transform|background-color|border-color|box-shadow|color)\b/.test(baseToken)
      ) {
        violations.push({
          rule: "unsupported-motion",
          relativePath: path,
          line: lineNumber(sourceFile.source, offset),
          match: token,
          message: "Transitions are limited to named state properties.",
        });
      }
    }

    if (/(?:data-stagger|\bstagger\b)/.test(baseToken) && /admin\//.test(path)) {
      if (!workbenchStaggerExceptions.has(path)) {
        violations.push({
          rule: "workbench-stagger",
          relativePath: path,
          line: lineNumber(sourceFile.source, offset),
          match: token,
          message: "Admin Workbench rows and cards must not receive automatic stagger motion.",
        });
      }
    }

    if (
      /^(?:bg|text|border|ring|from|to|via)-(?:black|white|transparent|current)(?:\/\d+)?$/.test(
        baseToken,
      )
    ) {
      if (
        !entryAllows(rawColorClassExceptions, path, token) &&
        !entryAllows(rawColorClassExceptions, path, baseToken)
      ) {
        violations.push({
          rule: "raw-color",
          relativePath: path,
          line: lineNumber(sourceFile.source, offset),
          match: token,
          message: "Use a governed semantic color or a documented media/deep-chrome exception.",
        });
      }
    }
  }
}

/** Returns true when a label is one of the explicitly permitted English terms. */
export function isEnglishLabelAllowed(label: string): boolean {
  const normalized = label.trim();
  return (
    (englishAllowlist.productNames as readonly string[]).includes(normalized) ||
    (englishAllowlist.operationalTerms as readonly string[]).includes(normalized)
  );
}

const decorativeBilingualPattern = /\b[A-Z][A-Z0-9 ]{2,}\s*[·|—–-]\s*[\u3400-\u9fff]+/g;

/** Finds routine all-caps English + Chinese labels in visible source text. */
export function findDecorativeBilingualLabels(source: string): string[] {
  return [...source.matchAll(decorativeBilingualPattern)].map((match) => match[0].trim());
}

function scanDecorativeBilingual(
  sourceFile: PresentationSource,
  violations: PresentationPolicyViolation[],
) {
  const path = normalizeSourcePath(sourceFile.relativePath);
  if (bilingualExceptions.has(path)) return;
  for (const match of sourceFile.source.matchAll(decorativeBilingualPattern)) {
    const value = match[0].trim();
    if (isEnglishLabelAllowed(value)) continue;
    const offset = match.index ?? 0;
    violations.push({
      rule: "decorative-bilingual",
      relativePath: path,
      line: lineNumber(sourceFile.source, offset),
      match: value,
      message:
        "Visible copy must be Chinese-first; English is limited to the canonical product/operational allowlist.",
    });
  }
}

function scanWorkbenchStagger(
  sourceFile: PresentationSource,
  violations: PresentationPolicyViolation[],
) {
  const path = normalizeSourcePath(sourceFile.relativePath);
  if (workbenchStaggerExceptions.has(path)) return;
  const workbenchStaggerPattern =
    /(?:density\s*=\s*["']workbench["'][^>]*\bstagger\b|\bstagger\b[^>]*density\s*=\s*["']workbench["'])/g;
  for (const match of sourceFile.source.matchAll(workbenchStaggerPattern)) {
    const offset = match.index ?? 0;
    violations.push({
      rule: "workbench-stagger",
      relativePath: path,
      line: lineNumber(sourceFile.source, offset),
      match: match[0],
      message: "Admin Workbench rows and cards must not receive automatic stagger motion.",
    });
  }
  if (/\bdata-stagger\b/.test(sourceFile.source) && /(?:admin|workbench)/i.test(path)) {
    const offset = sourceFile.source.search(/\bdata-stagger\b/);
    violations.push({
      rule: "workbench-stagger",
      relativePath: path,
      line: lineNumber(sourceFile.source, offset),
      match: "data-stagger",
      message: "Admin Workbench rows and cards must not receive automatic stagger motion.",
    });
  }
}

export function inspectPresentationSource(
  sourceFile: PresentationSource,
): PresentationPolicyViolation[] {
  const path = normalizeSourcePath(sourceFile.relativePath);
  if (path === "lib/presentationPolicy.ts") return [];
  const violations: PresentationPolicyViolation[] = [];

  if (path !== canonicalCssOwner && path !== identityPaletteOwner) {
    addMatches(
      violations,
      sourceFile,
      "raw-color",
      /#[0-9a-fA-F]{3,8}\b|\brgba?\([^)]*\)|\bhsla?\([^)]*\)/g,
      "Runtime colors belong in the CSS root; identity colors belong only to pastelPalette.ts.",
      (match) => path === identityPaletteOwner && match.startsWith("#"),
    );
  }

  addMatches(
    violations,
    sourceFile,
    "font-asset",
    /@font-face|@import\s+[^;]*(?:https?:\/\/|font)|url\([^)]*\.(?:woff2?|ttf|otf|eot)(?:\?[^)]*)?\)|font-\[[^\]]+\]/gi,
    "Fonts remain offline-safe and system-owned; do not add external or bundled font assets.",
  );

  if (path !== canonicalCssOwner) {
    addMatches(
      violations,
      sourceFile,
      "font-asset",
      /font-family\s*:/gi,
      "Runtime font-family values are owned by index.css.",
    );
  }

  if (path !== canonicalCssOwner) {
    addMatches(
      violations,
      sourceFile,
      "independent-frame",
      /@media\s*\([^)]*(?:min|max)-width\s*:\s*\d+px[^)]*\)/gi,
      "Structural breakpoints belong to the typed breakpoint map.",
      () => path === typedBreakpointOwner,
    );
  }

  if (path !== canonicalCssOwner) {
    addMatches(
      violations,
      sourceFile,
      "unsupported-motion",
      /(?:@keyframes\s+[\w-]+|animation\s*:\s*[^;]+)/gi,
      "Motion is limited to named, reduced-motion-safe owners in index.css.",
      (match) => /@keyframes\s+(?:shimmer|editorial-rise)\b/.test(match),
    );
  } else {
    addMatches(
      violations,
      sourceFile,
      "unsupported-motion",
      /@keyframes\s+([\w-]+)/gi,
      "Only named motion keyframes may be added to the CSS owner.",
      (match) => /@keyframes\s+(?:shimmer|editorial-rise)\b/.test(match),
    );
  }

  scanClassPolicy(sourceFile, violations);
  scanSurfaceOwners(sourceFile, violations);
  scanWorkbenchStagger(sourceFile, violations);
  scanDecorativeBilingual(sourceFile, violations);
  return violations;
}

export function inspectPresentationSources(
  sourceFiles: readonly PresentationSource[],
): PresentationPolicyViolation[] {
  return sourceFiles.flatMap((sourceFile) => inspectPresentationSource(sourceFile));
}

export function formatPresentationPolicyViolations(
  violations: readonly PresentationPolicyViolation[],
): string {
  return violations
    .map(
      (violation) =>
        `${violation.relativePath}:${violation.line} [${violation.rule}] ${violation.message} (${violation.match})`,
    )
    .join("\n");
}
