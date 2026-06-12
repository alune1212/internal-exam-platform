# Phase 1: Design Tokens & Fonts — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current teal-themed shadcn HSL tokens with the new Academic Editorial CSS variable system, and add Manrope / Inter / JetBrains Mono web font loading.

**Architecture:** Single source of truth in `:root` CSS variables; `tailwind.config.ts` maps them via `var(--token)`; `lib/design-tokens.ts` mirrors them as TypeScript constants for components that need raw values.

**Tech Stack:** Tailwind CSS 3.4, CSS custom properties, Google Fonts CDN, Vitest 1.x (newly added for type-shape test)

---

## Working Directory

All paths in this plan are relative to `frontend/` unless explicitly noted. Run `cd frontend &&` before every npm command shown.

---

## Task 1: Add Google Fonts link to `index.html`

**Files:**
- Modify: `frontend/index.html:1-12`

- [ ] **Step 1: Edit `index.html` to add the Google Fonts `<link>` tags**

Replace the entire contents of `frontend/index.html` with:

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=Manrope:ital,wght@0,400;0,500;0,600;0,700;1,600&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap"
      rel="stylesheet"
    />
    <title>内部临时考试平台</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 2: Verify the edit**

Run: `cd frontend && head -20 index.html`
Expected: First 20 lines match the snippet above (with preconnect + Google Fonts link before `<title>`).

- [ ] **Step 3: Commit**

```bash
git add frontend/index.html
git commit -m "feat(frontend): 引入 Manrope / Inter / JetBrains Mono 字体"
```

---

## Task 2: Rewrite `src/index.css` with new CSS variables

**Files:**
- Modify: `frontend/src/index.css:1-47` (full rewrite)

- [ ] **Step 1: Replace `frontend/src/index.css` with the new token system**

Overwrite `frontend/src/index.css` with the following content:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    /* Surfaces */
    --canvas: #ffffff;
    --canvas-warm: #fafaf7;
    --surface-card: #f5f3ee;
    --surface-elev: #ffffff;

    /* Ink */
    --ink: #111111;
    --ink-soft: #2a2a2a;
    --body: #374151;
    --muted: #6b7280;

    /* Lines */
    --hairline: #e5e7eb;
    --hairline-soft: #f3f4f6;

    /* Footer */
    --footer: #0a0a0a;
    --footer-soft: #a1a1aa;

    /* Status */
    --success: #166534;
    --warning: #b45309;
    --error: #b91c1c;

    /* Radius */
    --radius-pill: 9999px;
    --radius-lg: 16px;
    --radius-md: 8px;
    --radius-sm: 4px;

    /* Shadows */
    --shadow-card: 0 1px 2px rgba(17, 17, 17, 0.04),
      0 4px 12px rgba(17, 17, 17, 0.04);
    --shadow-pop: 0 8px 24px rgba(17, 17, 17, 0.08);
    --shadow-elevate: 0 16px 40px rgba(17, 17, 17, 0.1);

    /* Fonts */
    --font-display: "Manrope", "Inter", system-ui, sans-serif;
    --font-body: "Inter", system-ui, sans-serif;
    --font-mono: "JetBrains Mono", ui-monospace, monospace;
  }

  * {
    @apply border-hairline;
  }

  html,
  body,
  #root {
    min-height: 100%;
  }

  body {
    @apply min-h-screen bg-canvas text-ink antialiased;
    font-family: var(--font-body);
    font-feature-settings: "ss01", "cv11";
    line-height: 1.7;
  }

  h1,
  h2,
  h3 {
    font-family: var(--font-display);
    letter-spacing: -0.04em;
  }

  code,
  kbd,
  samp,
  pre {
    font-family: var(--font-mono);
    font-variant-numeric: tabular-nums;
  }

  [data-icon] {
    width: 1rem;
    height: 1rem;
  }

  /* Focus ring: WCAG-friendly 2px ink ring with 2px offset */
  :focus-visible {
    outline: 2px solid var(--ink);
    outline-offset: 2px;
    border-radius: 2px;
  }
}
```

- [ ] **Step 2: Verify the file is correct**

Run: `cd frontend && wc -l src/index.css`
Expected: At least 80 lines (sanity check — old file was 47, new file is bigger).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/index.css
git commit -m "refactor(frontend): 用学术编辑设计令牌替换 shadcn HSL 变量"
```

---

## Task 3: Update `tailwind.config.ts` to map tokens

**Files:**
- Modify: `frontend/tailwind.config.ts:1-47` (full rewrite)

- [ ] **Step 1: Replace `frontend/tailwind.config.ts` with the new mapping**

Overwrite `frontend/tailwind.config.ts` with:

```ts
import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "var(--canvas)",
        "canvas-warm": "var(--canvas-warm)",
        "surface-card": "var(--surface-card)",
        "surface-elev": "var(--surface-elev)",
        ink: {
          DEFAULT: "var(--ink)",
          soft: "var(--ink-soft)",
        },
        body: "var(--body)",
        muted: "var(--muted)",
        hairline: {
          DEFAULT: "var(--hairline)",
          soft: "var(--hairline-soft)",
        },
        footer: {
          DEFAULT: "var(--footer)",
          soft: "var(--footer-soft)",
        },
        success: "var(--success)",
        warning: "var(--warning)",
        error: "var(--error)",
      },
      borderRadius: {
        pill: "var(--radius-pill)",
        lg: "var(--radius-lg)",
        md: "var(--radius-md)",
        sm: "var(--radius-sm)",
      },
      fontFamily: {
        display: ["var(--font-display)"],
        body: ["var(--font-body)"],
        mono: ["var(--font-mono)"],
      },
      boxShadow: {
        card: "var(--shadow-card)",
        pop: "var(--shadow-pop)",
        elevate: "var(--shadow-elevate)",
      },
      fontSize: {
        "display-2xl": ["72px", { lineHeight: "1.05", letterSpacing: "-0.04em" }],
        "display-xl": ["56px", { lineHeight: "1.08", letterSpacing: "-0.04em" }],
        "display-lg": ["40px", { lineHeight: "1.1", letterSpacing: "-0.03em" }],
        "display-md": ["28px", { lineHeight: "1.2", letterSpacing: "-0.02em" }],
        "display-sm": ["22px", { lineHeight: "1.3", letterSpacing: "-0.02em" }],
        "body-lg": ["17px", { lineHeight: "1.7" }],
        body: ["15px", { lineHeight: "1.7" }],
        "body-sm": ["13px", { lineHeight: "1.6" }],
        caption: [
          "11px",
          {
            lineHeight: "1.4",
            letterSpacing: "0.16em",
          },
        ],
      },
    },
  },
  plugins: [],
} satisfies Config;
```

- [ ] **Step 2: Verify TypeScript still compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: Exit code 0, no errors. (Tailwind config is type-checked via the import in this project.)

- [ ] **Step 3: Commit**

```bash
git add frontend/tailwind.config.ts
git commit -m "refactor(frontend): tailwind 映射学术编辑令牌为 utility class"
```

---

## Task 4: Set up Vitest and create `lib/design-tokens.ts` with type-shape test

**Files:**
- Modify: `frontend/package.json` (add `vitest` devDep + `test` script)
- Create: `frontend/vitest.config.ts`
- Create: `frontend/src/lib/design-tokens.ts`
- Create: `frontend/src/lib/design-tokens.test.ts`

- [ ] **Step 1: Install Vitest as a dev dependency**

Run: `cd frontend && npm install --save-dev vitest@^1.6.0`

Expected: `vitest` appears in `devDependencies` in `frontend/package.json`.

- [ ] **Step 2: Add the `test` script to `frontend/package.json`**

Edit `frontend/package.json` to add a `"test"` script inside the existing `"scripts"` block. The new `"scripts"` section should be:

```json
  "scripts": {
    "dev": "vite --host 0.0.0.0",
    "build": "tsc --noEmit && vite build",
    "preview": "vite preview --host 0.0.0.0",
    "lint": "eslint .",
    "lint:fix": "eslint . --fix",
    "format": "prettier --write \"src/**/*.{ts,tsx,css,json}\"",
    "format:check": "prettier --check \"src/**/*.{ts,tsx,css,json}\"",
    "test": "vitest run"
  },
```

- [ ] **Step 3: Create `frontend/vitest.config.ts`**

Write to `frontend/vitest.config.ts`:

```ts
import path from "node:path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
  },
});
```

- [ ] **Step 4: Write the failing test first — `frontend/src/lib/design-tokens.test.ts`**

Create the test file. The test asserts that the exported `designTokens` object has exactly the expected key set AND that every value is a non-empty string. It will fail because the implementation file doesn't exist yet.

Write to `frontend/src/lib/design-tokens.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import { designTokens } from "./design-tokens";

const EXPECTED_KEYS = [
  // Surfaces
  "canvas",
  "canvasWarm",
  "surfaceCard",
  "surfaceElev",
  // Ink
  "ink",
  "inkSoft",
  "body",
  "muted",
  // Lines
  "hairline",
  "hairlineSoft",
  // Footer
  "footer",
  "footerSoft",
  // Status
  "success",
  "warning",
  "error",
  // Radius
  "radiusPill",
  "radiusLg",
  "radiusMd",
  "radiusSm",
  // Shadows
  "shadowCard",
  "shadowPop",
  "shadowElevate",
  // Fonts
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
    const fontTokens: Array<keyof typeof designTokens> = [
      "fontDisplay",
      "fontBody",
      "fontMono",
    ];
    for (const key of fontTokens) {
      expect(designTokens[key]).toMatch(/^"[^"]+"/);
    }
  });
});
```

- [ ] **Step 5: Run the test to verify it fails (RED)**

Run: `cd frontend && npm test -- src/lib/design-tokens.test.ts`
Expected: FAIL with `Failed to resolve import "./design-tokens" from "src/lib/design-tokens.test.ts"`.

- [ ] **Step 6: Write the minimal implementation — `frontend/src/lib/design-tokens.ts`**

Create the implementation file. Values must mirror the `:root` block in `src/index.css` from Task 2 (except: camelCased keys for JS ergonomics).

Write to `frontend/src/lib/design-tokens.ts`:

```ts
/**
 * TypeScript mirror of the CSS custom properties defined in `src/index.css :root`.
 *
 * Use these constants when a component needs the raw token value at runtime
 * (e.g. inline styles, computed styles, dynamic CSS injection). For everyday
 * styling prefer the Tailwind utilities (`bg-canvas`, `text-ink`, etc.)
 * defined in `tailwind.config.ts`.
 *
 * Color tokens are hex (per design spec section 3.1 — no HSL).
 */

export const designTokens = {
  // Surfaces
  canvas: "#ffffff",
  canvasWarm: "#fafaf7",
  surfaceCard: "#f5f3ee",
  surfaceElev: "#ffffff",

  // Ink
  ink: "#111111",
  inkSoft: "#2a2a2a",
  body: "#374151",
  muted: "#6b7280",

  // Lines
  hairline: "#e5e7eb",
  hairlineSoft: "#f3f4f6",

  // Footer
  footer: "#0a0a0a",
  footerSoft: "#a1a1aa",

  // Status
  success: "#166534",
  warning: "#b45309",
  error: "#b91c1c",

  // Radius
  radiusPill: "9999px",
  radiusLg: "16px",
  radiusMd: "8px",
  radiusSm: "4px",

  // Shadows (full shadow strings — drop straight into `box-shadow`)
  shadowCard: "0 1px 2px rgba(17, 17, 17, 0.04), 0 4px 12px rgba(17, 17, 17, 0.04)",
  shadowPop: "0 8px 24px rgba(17, 17, 17, 0.08)",
  shadowElevate: "0 16px 40px rgba(17, 17, 17, 0.1)",

  // Fonts
  fontDisplay: '"Manrope", "Inter", system-ui, sans-serif',
  fontBody: '"Inter", system-ui, sans-serif',
  fontMono: '"JetBrains Mono", ui-monospace, monospace',
} as const;

export type DesignTokenKey = keyof typeof designTokens;
export type DesignTokenValue = (typeof designTokens)[DesignTokenKey];
```

- [ ] **Step 7: Run the test to verify it passes (GREEN)**

Run: `cd frontend && npm test -- src/lib/design-tokens.test.ts`
Expected: PASS — all 5 tests pass (key set, value types, hex format, radius format, font format).

- [ ] **Step 8: Verify TypeScript still compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: Exit code 0, no errors.

- [ ] **Step 9: Commit**

```bash
git add frontend/package.json frontend/vitest.config.ts frontend/src/lib/design-tokens.ts frontend/src/lib/design-tokens.test.ts
git commit -m "feat(frontend): 新增 design-tokens 常量及 Vitest 类型校验测试"
```

---

## Task 5: Verify `npm run build` succeeds end-to-end

**Files:** none (read-only verification)

- [ ] **Step 1: Run lint**

Run: `cd frontend && npm run lint`
Expected: Exit code 0. Existing code may show warnings for usages of removed shadcn HSL classes (e.g. `bg-primary`, `text-foreground`) — those are addressed in later phases and should NOT block Phase 1. If lint reports errors, fix them before continuing.

- [ ] **Step 2: Run format check**

Run: `cd frontend && npm run format:check`
Expected: Exit code 0.

- [ ] **Step 3: Run the full build (type-check + Vite production build)**

Run: `cd frontend && npm run build`
Expected:
- `tsc --noEmit` succeeds
- Vite emits `dist/` without errors
- Console shows `built in <X>ms`

- [ ] **Step 4: Smoke-test the dev server**

Run: `cd frontend && npm run dev` (background, then kill after 5 seconds)

```bash
cd frontend && (npm run dev &) ; sleep 5 ; pkill -f "vite"
```

Expected: Vite reports `Local: http://localhost:5173/` and serves without errors. No `Failed to load` for Google Fonts in the (brief) startup output.

- [ ] **Step 5: Commit any incidental fixes (if needed)**

If steps 1–4 required no edits, skip this commit. Otherwise:

```bash
git add frontend/
git commit -m "chore(frontend): Phase 1 构建 / lint 兜底修复"
```

---

## Done

Phase 1 is complete when:

- `frontend/index.html` loads Manrope / Inter / JetBrains Mono via Google Fonts CDN
- `frontend/src/index.css` defines the Academic Editorial CSS variables (hex, no HSL)
- `frontend/tailwind.config.ts` maps every token to a Tailwind utility class
- `frontend/src/lib/design-tokens.ts` exports a typed mirror of those tokens
- `cd frontend && npm test` passes (Vitest)
- `cd frontend && npm run build` succeeds

Downstream phases (Phase 2: base components, Phase 3: editorial components, etc.) can now reference `var(--token)` directly, use Tailwind utilities like `bg-canvas-warm` / `text-ink` / `rounded-pill`, or import `designTokens` from `@/lib/design-tokens`.
