# Phase 3: Editorial Components — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build 5 academic-editorial specialized components that define the visual voice of the redesigned app: ChapterNumber, NamePlate, Wordmark, StatusPill, EmptyState.

**Architecture:** All 5 components live under `frontend/src/components/editorial/`. They consume design tokens from Phase 1 (CSS variables surfaced as Tailwind utilities — `text-muted`, `bg-ink`, `text-success`, `rounded-sm`, `tracking-[0.18em]`, etc.) and may reuse the `Button` primitive from Phase 2 (EmptyState only). All components are pure presentational; no state, no effects, no API calls. Tests live as sibling `.test.tsx` files next to each component using Vitest + React Testing Library (installed via Phase 1 dev deps).

**Tech Stack:** React 19, TypeScript, Tailwind 3.4, lucide-react (only available icon library — `EmptyState` does not require it; we keep the API icon-optional but include a small `Plus` icon by default for visual interest), Vitest + @testing-library/react + jsdom for tests.

---

## Files Created

| Path | Purpose |
|---|---|
| `frontend/src/components/editorial/ChapterNumber.tsx` | Italic + caps + tracking small heading prefix |
| `frontend/src/components/editorial/ChapterNumber.test.tsx` | Test: renders text + key classes |
| `frontend/src/components/editorial/NamePlate.tsx` | Pastel avatar + name + italic subtitle |
| `frontend/src/components/editorial/NamePlate.test.tsx` | Test: renders name/subtitle, deterministic avatar color |
| `frontend/src/components/editorial/Wordmark.tsx` | Z circle + 知试 + optional subtitle (light/dark) |
| `frontend/src/components/editorial/Wordmark.test.tsx` | Test: Z circle + wordmark text + subtitle + variant flip |
| `frontend/src/components/editorial/StatusPill.tsx` | Stamp-style badge with semantic color variants |
| `frontend/src/components/editorial/StatusPill.test.tsx` | Test: variant → text color class mapping |
| `frontend/src/components/editorial/EmptyState.tsx` | Centered chapter + italic h2 + CTA composition |
| `frontend/src/components/editorial/EmptyState.test.tsx` | Test: renders all parts; CTA optional; tone='error' colors chapter |
| `frontend/src/components/editorial/index.ts` | Barrel export for clean imports |
| `frontend/src/lib/pastelPalette.ts` | Shared pastel palette + deterministic pick-by-name util |

## Token Reference (from Phase 1 `index.css` + `tailwind.config.ts`)

These tokens must already exist after Phase 1; if not, they need to be created first (Phase 3 does NOT add tokens).

| Token | Class | Source |
|---|---|---|
| `--muted` | `text-muted` | `tailwind.config.ts → colors.muted` |
| `--ink` | `text-ink`, `bg-ink` | `tailwind.config.ts → colors.ink` |
| `--success` | `text-success` | `tailwind.config.ts → colors.success` |
| `--warning` | `text-warning` | `tailwind.config.ts → colors.warning` |
| `--error` | `text-error` | `tailwind.config.ts → colors.error` |
| `--canvas` | `bg-canvas`, `text-canvas` | `tailwind.config.ts → colors.canvas` |
| `--radius-sm` | `rounded-sm` (4px) | `tailwind.config.ts → borderRadius.sm` |
| `--radius-pill` | `rounded-pill` | `tailwind.config.ts → borderRadius.pill` |
| `--font-display` | `font-display` | `tailwind.config.ts → fontFamily.display` |
| `--font-mono` | `font-mono` | `tailwind.config.ts → fontFamily.mono` |
| custom size | `text-caption` (11px) | added in Phase 1 |
| custom size | `text-display-md` (28/22) | added in Phase 1 |

If any of these classes are missing in Phase 1, Phase 3 falls back to raw CSS-var Tailwind utilities (e.g. `text-[var(--muted)]`) — **do not add new tokens here**.

---

## Task 1: Shared pastel palette util

**Files:**
- Create: `frontend/src/lib/pastelPalette.ts`

**Why:** `NamePlate` needs a deterministic, name-stable pastel color. Centralizing the palette avoids duplication and gives a single test seam.

**Step 1.1: Write the file**

```ts
// frontend/src/lib/pastelPalette.ts

/** Editorial pastel palette for avatar / chip accents. */
export const PASTEL_COLORS = [
  "#fef3c7", // 黄 yellow
  "#dbeafe", // 蓝 blue
  "#dcfce7", // 绿 green
  "#fce7f3", // 粉 pink
  "#e0e7ff", // 靛 indigo
] as const;

export type PastelColor = (typeof PASTEL_COLORS)[number];

/**
 * Deterministically pick a pastel color from a string seed (e.g. user name).
 * Same input → same output across renders and tests.
 */
export function pickPastel(seed: string): PastelColor {
  if (!seed) return PASTEL_COLORS[0];
  let hash = 0;
  for (let i = 0; i < seed.length; i++) {
    hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
  }
  return PASTEL_COLORS[hash % PASTEL_COLORS.length];
}
```

**Step 1.2: Verify it compiles**

```bash
cd /Users/alune/Documents/code/internal-exam-platform/frontend
npx tsc --noEmit
```

Expected: no errors.

**Step 1.3: Commit**

```bash
git add frontend/src/lib/pastelPalette.ts
git commit -m "feat(editorial): 添加 NamePlate 共享 pastel 调色板工具"
```

---

## Task 2: ChapterNumber component

**Files:**
- Create: `frontend/src/components/editorial/ChapterNumber.tsx`
- Create: `frontend/src/components/editorial/ChapterNumber.test.tsx`

**Spec recap:** A small heading prefix rendered as `<span>———</span> {children}` (italic + 全大写 + 0.18em tracking). Use `<span>` so consumers can wrap it inside a heading without breaking block layout.

**Step 2.1: Write the test**

```tsx
// frontend/src/components/editorial/ChapterNumber.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ChapterNumber } from "./ChapterNumber";

describe("ChapterNumber", () => {
  it("renders the chapter text", () => {
    render(<ChapterNumber>CHAPTER 01 · WELCOME</ChapterNumber>);
    expect(screen.getByText("CHAPTER 01 · WELCOME")).toBeInTheDocument();
  });

  it("renders the leading horizontal-line marker", () => {
    render(<ChapterNumber>CHAPTER 01 · WELCOME</ChapterNumber>);
    expect(screen.getByText("———")).toBeInTheDocument();
  });

  it("applies italic, caption size, tracking, and muted color classes", () => {
    render(<ChapterNumber data-testid="cn">CHAPTER 02 · EXAM</ChapterNumber>);
    const el = screen.getByTestId("cn");
    expect(el.className).toMatch(/italic/);
    expect(el.className).toMatch(/text-caption|text-\[11px\]/);
    expect(el.className).toMatch(/tracking-\[0\.18em\]/);
    expect(el.className).toMatch(/text-muted/);
  });

  it("uppercases the chapter text", () => {
    render(<ChapterNumber data-testid="cn">chapter 03 · result</ChapterNumber>);
    expect(screen.getByTestId("cn")).toHaveClass("uppercase");
  });

  it("forwards additional className", () => {
    render(
      <ChapterNumber data-testid="cn" className="text-error">
        CHAPTER 99
      </ChapterNumber>,
    );
    expect(screen.getByTestId("cn")).toHaveClass("text-error");
  });
});
```

**Step 2.2: Write the component**

```tsx
// frontend/src/components/editorial/ChapterNumber.tsx
import * as React from "react";

import { cn } from "@/lib/utils";

export interface ChapterNumberProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** Chapter string, e.g. "CHAPTER 01 · WELCOME". Will be uppercased. */
  children: React.ReactNode;
}

/**
 * Small italic + uppercase prefix rendered above h1/h2 to label sections.
 * Visual: `——— CHAPTER 01 · WELCOME` (11px, italic, 0.18em tracking, muted).
 */
export function ChapterNumber({ children, className, ...props }: ChapterNumberProps) {
  return (
    <span
      {...props}
      className={cn(
        "inline-flex items-center text-caption italic uppercase tracking-[0.18em] text-muted",
        className,
      )}
    >
      <span aria-hidden="true" className="mr-3">
        ———
      </span>
      <span>{children}</span>
    </span>
  );
}
```

**Step 2.3: Run the test**

```bash
cd /Users/alune/Documents/code/internal-exam-platform/frontend
npx vitest run src/components/editorial/ChapterNumber.test.tsx
```

Expected: 5 passed.

**Step 2.4: Typecheck + lint**

```bash
cd /Users/alune/Documents/code/internal-exam-platform/frontend
npx tsc --noEmit
npm run lint -- src/components/editorial/ChapterNumber.tsx src/components/editorial/ChapterNumber.test.tsx
```

Expected: no errors, no warnings.

**Step 2.5: Commit**

```bash
git add frontend/src/components/editorial/ChapterNumber.tsx frontend/src/components/editorial/ChapterNumber.test.tsx
git commit -m "feat(editorial): 实现 ChapterNumber 组件"
```

---

## Task 3: NamePlate component

**Files:**
- Create: `frontend/src/components/editorial/NamePlate.tsx`
- Create: `frontend/src/components/editorial/NamePlate.test.tsx`

**Spec recap:** 24×24 circle avatar (pastel + uppercase first char) + 14px display-600 name + 11px italic caption subtitle.

**Step 3.1: Write the test**

```tsx
// frontend/src/components/editorial/NamePlate.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PASTEL_COLORS, pickPastel } from "@/lib/pastelPalette";

import { NamePlate } from "./NamePlate";

describe("NamePlate", () => {
  it("renders the name and subtitle", () => {
    render(<NamePlate name="张三" subtitle="EMP-001 · 研发部" />);
    expect(screen.getByText("张三")).toBeInTheDocument();
    expect(screen.getByText("EMP-001 · 研发部")).toBeInTheDocument();
  });

  it("omits subtitle paragraph when subtitle is empty", () => {
    render(<NamePlate name="李四" subtitle="" />);
    expect(screen.getByText("李四")).toBeInTheDocument();
    // The subtitle <p> should not be in the document
    expect(screen.queryByText(/EMP-001/)).not.toBeInTheDocument();
  });

  it("uses the first uppercase character as the avatar letter", () => {
    render(<NamePlate name="alice" />);
    expect(screen.getByText("A")).toBeInTheDocument();
  });

  it("applies one of the pastel palette colors as avatar background", () => {
    render(<NamePlate name="张三" />);
    const avatar = screen.getByText("张");
    const inlineStyle = (avatar as HTMLElement).style.backgroundColor;
    // jsdom normalizes hex to rgb()
    const hex = PASTEL_COLORS.find((c) => {
      const r = parseInt(c.slice(1, 3), 16);
      const g = parseInt(c.slice(3, 5), 16);
      const b = parseInt(c.slice(5, 7), 16);
      return `rgb(${r}, ${g}, ${b})` === inlineStyle;
    });
    expect(hex).toBeDefined();
  });

  it("pickPastel is deterministic for the same seed", () => {
    expect(pickPastel("张三")).toBe(pickPastel("张三"));
  });

  it("name text uses font-display + 14px size", () => {
    render(<NamePlate name="张三" subtitle="x" />);
    const name = screen.getByText("张三");
    expect(name.className).toMatch(/font-display/);
    expect(name.className).toMatch(/text-\[14px\]|text-sm/);
  });
});
```

**Step 3.2: Write the component**

```tsx
// frontend/src/components/editorial/NamePlate.tsx
import * as React from "react";

import { pickPastel } from "@/lib/pastelPalette";
import { cn } from "@/lib/utils";

export interface NamePlateProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Display name. First non-space character becomes the avatar letter. */
  name: string;
  /** Optional caption shown under the name (e.g. "EMP-001 · 研发部"). */
  subtitle?: string;
  /** Avatar diameter in px. Default 24. */
  avatarSize?: number;
}

/**
 * Editorial name plate: pastel avatar + name (display 600) + italic caption.
 * Used in TopNav, post-login banners, and result pages.
 */
export function NamePlate({
  name,
  subtitle,
  avatarSize = 24,
  className,
  ...props
}: NamePlateProps) {
  const initial = (name.trim().charAt(0) || "?").toUpperCase();
  const avatarBg = pickPastel(name);

  return (
    <div
      {...props}
      className={cn("inline-flex items-center gap-2", className)}
    >
      <span
        aria-hidden="true"
        className="inline-flex shrink-0 items-center justify-center rounded-full font-display text-[12px] font-semibold text-ink"
        style={{
          width: `${avatarSize}px`,
          height: `${avatarSize}px`,
          backgroundColor: avatarBg,
        }}
      >
        {initial}
      </span>
      <span className="flex flex-col leading-tight">
        <span className="font-display text-[14px] font-semibold text-ink">
          {name}
        </span>
        {subtitle ? (
          <span className="text-caption italic text-muted">{subtitle}</span>
        ) : null}
      </span>
    </div>
  );
}
```

**Step 3.3: Run tests**

```bash
cd /Users/alune/Documents/code/internal-exam-platform/frontend
npx vitest run src/components/editorial/NamePlate.test.tsx
```

Expected: 6 passed.

**Step 3.4: Typecheck + lint**

```bash
cd /Users/alune/Documents/code/internal-exam-platform/frontend
npx tsc --noEmit
npm run lint -- src/components/editorial/NamePlate.tsx src/components/editorial/NamePlate.test.tsx
```

Expected: clean.

**Step 3.5: Commit**

```bash
git add frontend/src/components/editorial/NamePlate.tsx frontend/src/components/editorial/NamePlate.test.tsx
git commit -m "feat(editorial): 实现 NamePlate 组件"
```

---

## Task 4: Wordmark component

**Files:**
- Create: `frontend/src/components/editorial/Wordmark.tsx`
- Create: `frontend/src/components/editorial/Wordmark.test.tsx`

**Spec recap:** 28×28 or 36×36 Z circle + "知试" Manrope 600 + optional italic subtitle. Variants: `light` (default: black Z on white) / `dark` (white Z on black for admin footer/sidebar).

**Step 4.1: Write the test**

```tsx
// frontend/src/components/editorial/Wordmark.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Wordmark } from "./Wordmark";

describe("Wordmark", () => {
  it("renders the brand text 知试", () => {
    render(<Wordmark />);
    expect(screen.getByText("知试")).toBeInTheDocument();
  });

  it("renders the Z mark inside the circle", () => {
    render(<Wordmark data-testid="wm" />);
    // The Z is a separate element with aria-hidden
    expect(screen.getByText("Z")).toBeInTheDocument();
  });

  it("renders optional subtitle in italic caption", () => {
    render(<Wordmark subtitle="internal exam platform" />);
    const sub = screen.getByText("internal exam platform");
    expect(sub.className).toMatch(/italic/);
    expect(sub.className).toMatch(/text-caption|text-\[11px\]/);
  });

  it("uses dark colors on the circle for dark variant", () => {
    render(<Wordmark variant="dark" data-testid="wm" />);
    const root = screen.getByTestId("wm");
    // dark variant → circle is bg-canvas (white) with text-ink (black)
    const circle = root.querySelector("span") as HTMLElement;
    expect(circle.className).toMatch(/bg-canvas|text-ink/);
  });

  it("uses light (default) colors on the circle for light variant", () => {
    render(<Wordmark variant="light" data-testid="wm" />);
    const circle = screen.getByTestId("wm").querySelector("span") as HTMLElement;
    expect(circle.className).toMatch(/bg-ink/);
  });

  it("uses size=md (36×36 circle, 24px text) by default? — actually default is md", () => {
    render(<Wordmark size="md" />);
    const z = screen.getByText("Z");
    expect(z.parentElement?.className).toMatch(/size-9|h-9|w-9/);
  });

  it("uses size=sm (28×28 circle, 18px text)", () => {
    render(<Wordmark size="sm" data-testid="wm" />);
    const circle = screen.getByTestId("wm").querySelector("span") as HTMLElement;
    expect(circle.className).toMatch(/size-7|h-7|w-7/);
    const wordmark = screen.getByText("知试");
    expect(wordmark.className).toMatch(/text-\[18px\]/);
  });
});
```

**Step 4.2: Write the component**

```tsx
// frontend/src/components/editorial/Wordmark.tsx
import * as React from "react";

import { cn } from "@/lib/utils";

export type WordmarkSize = "sm" | "md";
export type WordmarkVariant = "light" | "dark";

export interface WordmarkProps extends React.HTMLAttributes<HTMLDivElement> {
  /** 28×28 (sm) or 36×36 (md). Default md. */
  size?: WordmarkSize;
  /** "light" = black Z on white (default). "dark" = white Z on black (admin). */
  variant?: WordmarkVariant;
  /** Optional italic caption after the wordmark. */
  subtitle?: string;
  /** Optional override for the brand text (default: "知试"). */
  label?: string;
}

const sizeStyles: Record<
  WordmarkSize,
  { circle: string; text: string; subtitle: string }
> = {
  sm: {
    circle: "size-7 text-[12px]",
    text: "text-[18px]",
    subtitle: "text-[11px]",
  },
  md: {
    circle: "size-9 text-[14px]",
    text: "text-[24px]",
    subtitle: "text-[11px]",
  },
};

/**
 * Brand wordmark: a Z circle + 知试 + optional italic subtitle.
 * Used in TopNav (light), AdminSideRail (dark), and Footer (dark).
 */
export function Wordmark({
  size = "md",
  variant = "light",
  subtitle,
  label = "知试",
  className,
  ...props
}: WordmarkProps) {
  const s = sizeStyles[size];
  const isDark = variant === "dark";

  return (
    <div
      {...props}
      className={cn("inline-flex items-center gap-2.5", className)}
    >
      <span
        aria-hidden="true"
        className={cn(
          "inline-flex shrink-0 items-center justify-center rounded-full font-display font-semibold",
          s.circle,
          isDark ? "bg-canvas text-ink" : "bg-ink text-canvas",
        )}
      >
        Z
      </span>
      <span className="flex flex-col leading-none">
        <span
          className={cn(
            "font-display font-semibold tracking-tight",
            s.text,
            isDark ? "text-canvas" : "text-ink",
          )}
        >
          {label}
        </span>
        {subtitle ? (
          <span
            className={cn(
              "mt-1 italic text-muted",
              s.subtitle,
            )}
          >
            {subtitle}
          </span>
        ) : null}
      </span>
    </div>
  );
}
```

**Step 4.3: Run tests**

```bash
cd /Users/alune/Documents/code/internal-exam-platform/frontend
npx vitest run src/components/editorial/Wordmark.test.tsx
```

Expected: 7 passed.

**Step 4.4: Typecheck + lint**

```bash
cd /Users/alune/Documents/code/internal-exam-platform/frontend
npx tsc --noEmit
npm run lint -- src/components/editorial/Wordmark.tsx src/components/editorial/Wordmark.test.tsx
```

Expected: clean.

**Step 4.5: Commit**

```bash
git add frontend/src/components/editorial/Wordmark.tsx frontend/src/components/editorial/Wordmark.test.tsx
git commit -m "feat(editorial): 实现 Wordmark 组件"
```

---

## Task 5: StatusPill component

**Files:**
- Create: `frontend/src/components/editorial/StatusPill.tsx`
- Create: `frontend/src/components/editorial/StatusPill.test.tsx`

**Spec recap:** Stamp-style badge — padding `1px 8px`, rounded-sm (4px), text-caption + tracking 0.16em + uppercase. Variants: `default` (ink), `success`, `warning`, `error`. Children are auto-uppercased.

**Step 5.1: Write the test**

```tsx
// frontend/src/components/editorial/StatusPill.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatusPill } from "./StatusPill";

describe("StatusPill", () => {
  it("renders the label", () => {
    render(<StatusPill>live</StatusPill>);
    expect(screen.getByText("live")).toBeInTheDocument();
  });

  it("applies uppercase + caption size + 0.16em tracking", () => {
    render(<StatusPill data-testid="p">live</StatusPill>);
    const el = screen.getByTestId("p");
    expect(el.className).toMatch(/uppercase/);
    expect(el.className).toMatch(/text-caption|text-\[11px\]/);
    expect(el.className).toMatch(/tracking-\[0\.16em\]/);
    expect(el.className).toMatch(/rounded-sm/);
  });

  it("uses ink (dark text) by default — i.e. text-ink + bg-canvas-warm", () => {
    render(<StatusPill data-testid="p">draft</StatusPill>);
    const el = screen.getByTestId("p");
    expect(el.className).toMatch(/text-ink/);
  });

  it("success variant uses text-success", () => {
    render(<StatusPill variant="success" data-testid="p">live</StatusPill>);
    expect(screen.getByTestId("p").className).toMatch(/text-success/);
  });

  it("warning variant uses text-warning", () => {
    render(<StatusPill variant="warning" data-testid="p">soon</StatusPill>);
    expect(screen.getByTestId("p").className).toMatch(/text-warning/);
  });

  it("error variant uses text-error", () => {
    render(<StatusPill variant="error" data-testid="p">wrong</StatusPill>);
    expect(screen.getByTestId("p").className).toMatch(/text-error/);
  });

  it("forwards extra className", () => {
    render(
      <StatusPill data-testid="p" className="ml-2">
        live
      </StatusPill>,
    );
    expect(screen.getByTestId("p")).toHaveClass("ml-2");
  });
});
```

**Step 5.2: Write the component**

```tsx
// frontend/src/components/editorial/StatusPill.tsx
import * as React from "react";

import { cn } from "@/lib/utils";

export type StatusPillVariant = "default" | "success" | "warning" | "error";

export interface StatusPillProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** Semantic color. Default uses ink; success/warning/error map to status tokens. */
  variant?: StatusPillVariant;
  /** Visible label. Auto-uppercased by CSS. */
  children: React.ReactNode;
}

const variantClass: Record<StatusPillVariant, string> = {
  default: "text-ink bg-canvas-warm border border-hairline",
  success: "text-success bg-canvas border border-success/30",
  warning: "text-warning bg-canvas border border-warning/30",
  error: "text-error bg-canvas border border-error/30",
};

/**
 * Stamp-style status badge: 4px corners, 11px uppercase 0.16em tracking.
 * Used to replace shadcn Badge where "印章感" matters (LIVE / SOON / WRONG).
 */
export function StatusPill({
  variant = "default",
  className,
  children,
  ...props
}: StatusPillProps) {
  return (
    <span
      {...props}
      className={cn(
        "inline-flex items-center rounded-sm px-2 py-px text-caption uppercase tracking-[0.16em]",
        variantClass[variant],
        className,
      )}
    >
      {children}
    </span>
  );
}
```

**Step 5.3: Run tests**

```bash
cd /Users/alune/Documents/code/internal-exam-platform/frontend
npx vitest run src/components/editorial/StatusPill.test.tsx
```

Expected: 7 passed.

**Step 5.4: Typecheck + lint**

```bash
cd /Users/alune/Documents/code/internal-exam-platform/frontend
npx tsc --noEmit
npm run lint -- src/components/editorial/StatusPill.tsx src/components/editorial/StatusPill.test.tsx
```

Expected: clean.

**Step 5.5: Commit**

```bash
git add frontend/src/components/editorial/StatusPill.tsx frontend/src/components/editorial/StatusPill.test.tsx
git commit -m "feat(editorial): 实现 StatusPill 印章感徽章"
```

---

## Task 6: EmptyState component

**Files:**
- Create: `frontend/src/components/editorial/EmptyState.tsx`
- Create: `frontend/src/components/editorial/EmptyState.test.tsx`

**Spec recap:** Centered layout — chapter (ChapterNumber) + italic h2 + description + optional Button (lg). `tone='error'` recolors the chapter to `--error`. Reuses `Button` from `components/ui/button.tsx`.

**Step 6.1: Write the test**

```tsx
// frontend/src/components/editorial/EmptyState.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { EmptyState } from "./EmptyState";

describe("EmptyState", () => {
  it("renders chapter, title, description", () => {
    render(
      <EmptyState
        chapter="CHAPTER 00"
        title="暂无内容"
        description="还没有任何数据。"
      />,
    );
    expect(screen.getByText("CHAPTER 00")).toBeInTheDocument();
    expect(screen.getByText("暂无内容")).toBeInTheDocument();
    expect(screen.getByText("还没有任何数据。")).toBeInTheDocument();
  });

  it("renders an action button when action is provided", () => {
    const onClick = vi.fn();
    render(
      <EmptyState
        chapter="CHAPTER 00"
        title="暂无内容"
        description="还没有任何数据。"
        action={{ label: "新建", onClick }}
      />,
    );
    const btn = screen.getByRole("button", { name: "新建" });
    expect(btn).toBeInTheDocument();
  });

  it("invokes action.onClick when the button is clicked", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(
      <EmptyState
        chapter="CHAPTER 00"
        title="暂无内容"
        description="x"
        action={{ label: "新建", onClick }}
      />,
    );
    await user.click(screen.getByRole("button", { name: "新建" }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("omits the action button when action is not provided", () => {
    render(
      <EmptyState chapter="CHAPTER 00" title="暂无内容" description="x" />,
    );
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("error tone recolors chapter to error", () => {
    render(
      <EmptyState
        tone="error"
        chapter="CHAPTER 99 · ERROR"
        title="出错了"
        description="请稍后重试。"
      />,
    );
    const chapter = screen.getByText("CHAPTER 99 · ERROR");
    expect(chapter.className).toMatch(/text-error/);
  });

  it("default tone keeps chapter muted", () => {
    render(
      <EmptyState
        chapter="CHAPTER 00"
        title="暂无内容"
        description="x"
      />,
    );
    const chapter = screen.getByText("CHAPTER 00");
    expect(chapter.className).toMatch(/text-muted/);
  });

  it("title uses italic + display size", () => {
    render(
      <EmptyState chapter="x" title="暂无内容" description="y" />,
    );
    const h = screen.getByRole("heading", { level: 2, name: "暂无内容" });
    expect(h.className).toMatch(/italic/);
    expect(h.className).toMatch(/font-display/);
  });
});
```

**Step 6.2: Write the component**

```tsx
// frontend/src/components/editorial/EmptyState.tsx
import * as React from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import { ChapterNumber } from "./ChapterNumber";

export type EmptyStateTone = "default" | "error";

export interface EmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Small chapter prefix (rendered via ChapterNumber). */
  chapter: string;
  /** Italic h2 headline. */
  title: string;
  /** Muted body description paragraph. */
  description: string;
  /** Optional primary CTA. */
  action?: { label: string; onClick: () => void };
  /** "default" → muted chapter; "error" → error-toned chapter for failure pages. */
  tone?: EmptyStateTone;
}

/**
 * Centered empty / error state. Used for empty lists, no data, and error pages.
 */
export function EmptyState({
  chapter,
  title,
  description,
  action,
  tone = "default",
  className,
  ...props
}: EmptyStateProps) {
  const chapterTone = tone === "error" ? "text-error" : undefined;

  return (
    <div
      {...props}
      className={cn(
        "mx-auto flex max-w-md flex-col items-center gap-6 py-16 text-center",
        className,
      )}
    >
      <ChapterNumber className={cn(chapterTone)}>{chapter}</ChapterNumber>
      <h2 className="font-display text-display-md italic text-ink">{title}</h2>
      <p className="text-body text-muted">{description}</p>
      {action ? (
        <Button size="lg" variant="default" onClick={action.onClick}>
          {action.label}
        </Button>
      ) : null}
    </div>
  );
}
```

**Step 6.3: Run tests**

```bash
cd /Users/alune/Documents/code/internal-exam-platform/frontend
npx vitest run src/components/editorial/EmptyState.test.tsx
```

Expected: 7 passed.

**Step 6.4: Typecheck + lint**

```bash
cd /Users/alune/Documents/code/internal-exam-platform/frontend
npx tsc --noEmit
npm run lint -- src/components/editorial/EmptyState.tsx src/components/editorial/EmptyState.test.tsx
```

Expected: clean.

**Step 6.5: Commit**

```bash
git add frontend/src/components/editorial/EmptyState.tsx frontend/src/components/editorial/EmptyState.test.tsx
git commit -m "feat(editorial): 实现 EmptyState 空态与错态组件"
```

---

## Task 7: Barrel export + full sweep

**Files:**
- Create: `frontend/src/components/editorial/index.ts`

**Step 7.1: Write the barrel**

```ts
// frontend/src/components/editorial/index.ts
export { ChapterNumber } from "./ChapterNumber";
export type { ChapterNumberProps } from "./ChapterNumber";

export { NamePlate } from "./NamePlate";
export type { NamePlateProps } from "./NamePlate";

export { Wordmark } from "./Wordmark";
export type { WordmarkProps, WordmarkSize, WordmarkVariant } from "./Wordmark";

export { StatusPill } from "./StatusPill";
export type { StatusPillProps, StatusPillVariant } from "./StatusPill";

export { EmptyState } from "./EmptyState";
export type { EmptyStateProps, EmptyStateTone } from "./EmptyState";
```

**Step 7.2: Full verification sweep**

```bash
cd /Users/alune/Documents/code/internal-exam-platform/frontend
npm run lint
npm run format:check
npx tsc --noEmit
npx vitest run src/components/editorial
```

Expected: lint 0 warnings; format 0 diff; tsc clean; all editorial tests pass.

**Step 7.3: Commit**

```bash
git add frontend/src/components/editorial/index.ts
git commit -m "feat(editorial): 暴露 5 个学术感组件 barrel 导出"
```

---

## Done Criteria

- [ ] `frontend/src/lib/pastelPalette.ts` exists and exports `PASTEL_COLORS` + `pickPastel`
- [ ] `frontend/src/components/editorial/ChapterNumber.tsx` + `.test.tsx` — 5 tests pass
- [ ] `frontend/src/components/editorial/NamePlate.tsx` + `.test.tsx` — 6 tests pass
- [ ] `frontend/src/components/editorial/Wordmark.tsx` + `.test.tsx` — 7 tests pass
- [ ] `frontend/src/components/editorial/StatusPill.tsx` + `.test.tsx` — 7 tests pass
- [ ] `frontend/src/components/editorial/EmptyState.tsx` + `.test.tsx` — 7 tests pass
- [ ] `frontend/src/components/editorial/index.ts` barrel re-exports all 5 components + their types
- [ ] `npx tsc --noEmit` clean across all new files
- [ ] `npm run lint` 0 warning
- [ ] `npm run format:check` 0 diff
- [ ] No new runtime dependencies added; only devDeps from Phase 1 (Vitest + RTL) are used
- [ ] No `any` types in any of the 5 components
- [ ] All commits follow `<type>(<scope>): <中文描述>` convention
- [ ] Phase 4 (layout) can now import from `@/components/editorial` cleanly

## Out of Scope (deferred to later phases)

- Timer / ProgressCapsule / OptionCard / QuestionNavigator / ExamFocusMode (Phase 5 — pages)
- TopNav / CandidateLayout / AdminSideRail / Footer (Phase 4 — layout)
- Tailwind tokens not present in Phase 1 will fail silently via fallback classes; this plan does NOT add new tokens
- Any new runtime dependency (e.g. icons beyond what lucide-react already provides) — none of these 5 components import an icon
