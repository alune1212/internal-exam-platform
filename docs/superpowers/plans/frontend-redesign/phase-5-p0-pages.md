# Phase 5: P0 Pages — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the 4 highest-priority pages (Login, ExamTaking Focus Mode, ExamResult, Practice) with deep visual fidelity, plus 5 new exam-specific components, following the Academic Editorial aesthetic.

**Architecture:** Each page is a route component; pages compose primitives from Phase 2 (Button, Card, Input), editorial components from Phase 3 (ChapterNumber, Wordmark, NamePlate, StatusPill, EmptyState), and the 5 new exam components (`OptionCard`, `ProgressCapsule`, `Timer`, `ExamFocusMode`, `ExamNavigator`). All pages must work in both desktop (≥1024px) and mobile (<768px) viewports.

**Tech Stack:** React 19, React Router 7, TanStack Query, React Hook Form + Zod, lucide-react, all Phase 1–4 outputs

---

## Working Directory

All paths in this plan are relative to the repo root unless explicitly noted. Run `cd frontend &&` before every npm command shown.

---

## Prerequisites

Phase 1–4 outputs must already exist:
- `frontend/src/index.css` — Academic Editorial CSS variables (--canvas, --ink, --surface-card, --font-display, etc.)
- `frontend/tailwind.config.ts` — utilities `bg-canvas`, `bg-canvas-warm`, `text-ink`, `rounded-pill`, `font-mono`, etc.
- `frontend/src/components/ui/button.tsx` — pill-shaped, variants `default | outline | ghost | secondary | destructive`
- `frontend/src/components/ui/card.tsx` — rounded-lg (16px) cards
- `frontend/src/components/ui/input.tsx` — rounded-md (8px), h-11
- `frontend/src/components/ui/label.tsx` — body-sm 600
- `frontend/src/components/editorial/ChapterNumber.tsx` — accepts `chapter="01"` and `title="WELCOME"` props
- `frontend/src/components/editorial/Wordmark.tsx` — Z circle + 知试 wordmark
- `frontend/src/components/editorial/NamePlate.tsx` — avatar + name + employee_no/department caption
- `frontend/src/components/editorial/StatusPill.tsx` — LIVE/DRAFT/ENDED pill
- `frontend/src/components/editorial/EmptyState.tsx` — chapter + italic h2 + description + CTA
- `frontend/src/lib/design-tokens.ts` — typed mirror of CSS variables

Verify before starting:

```bash
ls frontend/src/components/editorial/ frontend/src/components/ui/
```

If Phase 3 components are missing, stop and complete Phase 3 first.

---

## Snapshot field contract (do NOT change)

The following fields on `attempt.questions[]` are read-only and must stay unchanged across this phase (per CLAUDE.md "硬边界"):

- `stem_snapshot: string`
- `options_snapshot: Array<{ label: string; content: string; sort_order: number }>`
- `score: number`
- `sort_order: number`
- `selected_answer?: string | null`

API functions stay unchanged:
- `getAttempt(attemptId) → Attempt`
- `saveAttemptAnswers(attemptId, items) → { saved_count; saved_at }`
- `submitAttempt(attemptId, submitType) → AttemptResult`
- `getAttemptResult(attemptId) → AttemptResult`
- `getPracticeQuestions() → Question[]`
- `submitPracticeAnswer({ candidate_id, question_id, selected_answer }) → PracticeAnswerResult`
- `loginCandidate({ name, employee_no? }) → Candidate`

---

## Task 1: Create `components/exam/OptionCard.tsx`

**Files:**
- Create: `frontend/src/components/exam/OptionCard.tsx`
- Create: `frontend/src/components/exam/OptionCard.test.tsx`

- [ ] **Step 1: Write the failing test first — `frontend/src/components/exam/OptionCard.test.tsx`**

This test asserts:
- Renders the option label letter and option content text
- When `selected` is false, the card has class `bg-canvas` and `border-hairline`
- When `selected` is true, the card has class `bg-surface-card` and `border-ink`
- The indicator is `aria-checked="true"` when selected
- Calls `onSelect(label)` exactly once when clicked

Create the file with:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { OptionCard } from "./OptionCard";

describe("OptionCard", () => {
  it("renders option label letter and content", () => {
    render(
      <OptionCard
        label="A"
        content="Beijing"
        selected={false}
        onSelect={() => undefined}
      />,
    );
    expect(screen.getByText("A")).toBeInTheDocument();
    expect(screen.getByText("Beijing")).toBeInTheDocument();
  });

  it("applies unselected surface (canvas + hairline) when not selected", () => {
    render(
      <OptionCard
        label="A"
        content="Beijing"
        selected={false}
        onSelect={() => undefined}
      />,
    );
    const card = screen.getByRole("button");
    expect(card.className).toContain("bg-canvas");
    expect(card.className).toContain("border-hairline");
  });

  it("applies selected surface (surface-card + ink) when selected", () => {
    render(
      <OptionCard
        label="A"
        content="Beijing"
        selected={true}
        onSelect={() => undefined}
      />,
    );
    const card = screen.getByRole("button");
    expect(card.className).toContain("bg-surface-card");
    expect(card.className).toContain("border-ink");
  });

  it("exposes aria-checked reflecting selected state", () => {
    render(
      <OptionCard
        label="A"
        content="Beijing"
        selected={true}
        onSelect={() => undefined}
      />,
    );
    expect(screen.getByRole("button")).toHaveAttribute("aria-checked", "true");
  });

  it("calls onSelect with the label exactly once on click", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(
      <OptionCard
        label="B"
        content="Shanghai"
        selected={false}
        onSelect={onSelect}
      />,
    );
    await user.click(screen.getByRole("button"));
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith("B");
  });
});
```

- [ ] **Step 2: Run the test to verify it fails (RED)**

Run: `cd frontend && npm test -- src/components/exam/OptionCard.test.tsx`
Expected: FAIL with `Failed to resolve import "./OptionCard"` (file does not exist yet).

If the test runner reports "Cannot find module '@testing-library/react'", install it:

```bash
cd frontend && npm install --save-dev @testing-library/react @testing-library/user-event jsdom
```

Then add `jsdom` to `vitest.config.ts` `test.environment`:

```ts
test: {
  environment: "jsdom",
  include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
},
```

Re-run; expected: still RED due to missing component.

- [ ] **Step 3: Write the implementation — `frontend/src/components/exam/OptionCard.tsx`**

Create the file with:

```tsx
import { cn } from "@/lib/utils";

export type OptionCardProps = {
  label: string;
  content: string;
  selected: boolean;
  onSelect: (label: string) => void;
  disabled?: boolean;
};

/**
 * 整张可点击的考试选项卡。
 * - 左侧 24×24 圆形单选/多选指示器（内部显示 label 大写字母）
 * - 右侧选项文字
 * - 选中：bg-surface-card + border-ink + 2px ink ring
 * - 未选：bg-canvas + border-hairline
 * - 圆角 rounded-md (8px)，最小高度 56px（手机端 48px）
 */
export function OptionCard({ label, content, selected, onSelect, disabled }: OptionCardProps) {
  return (
    <button
      type="button"
      role="button"
      aria-checked={selected}
      aria-label={`选项 ${label}：${content}`}
      disabled={disabled}
      onClick={() => onSelect(label)}
      className={cn(
        "flex w-full min-h-12 md:min-h-14 items-center gap-3 rounded-md border px-4 py-3 text-left",
        "transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2",
        "disabled:cursor-not-allowed disabled:opacity-50",
        selected ? "border-ink bg-surface-card ring-1 ring-ink" : "border-hairline bg-canvas",
      )}
    >
      <span
        aria-hidden="true"
        className={cn(
          "inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full",
          "font-mono text-xs font-semibold tabular-nums",
          selected ? "bg-ink text-canvas" : "border border-hairline bg-canvas text-ink",
        )}
      >
        {label}
      </span>
      <span className="flex-1 text-body leading-relaxed text-ink">{content}</span>
    </button>
  );
}
```

- [ ] **Step 4: Run the test to verify it passes (GREEN)**

Run: `cd frontend && npm test -- src/components/exam/OptionCard.test.tsx`
Expected: PASS — all 5 tests pass.

- [ ] **Step 5: Verify TypeScript still compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: Exit code 0.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/exam/OptionCard.tsx frontend/src/components/exam/OptionCard.test.tsx
git commit -m "feat(exam): 实现 OptionCard 可点击选项卡"
```

---

## Task 2: Create `components/exam/ProgressCapsule.tsx`

**Files:**
- Create: `frontend/src/components/exam/ProgressCapsule.tsx`
- Create: `frontend/src/components/exam/ProgressCapsule.test.tsx`

- [ ] **Step 1: Write the failing test first**

Create `frontend/src/components/exam/ProgressCapsule.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ProgressCapsule } from "./ProgressCapsule";

describe("ProgressCapsule", () => {
  it("renders the question index label Q 03 / 10", () => {
    render(<ProgressCapsule current={3} total={10} answered={3} />);
    expect(screen.getByText(/Q\s*03\s*\/\s*10/)).toBeInTheDocument();
  });

  it("renders the percentage derived from answered/total", () => {
    render(<ProgressCapsule current={3} total={10} answered={3} />);
    expect(screen.getByText(/30%/)).toBeInTheDocument();
  });

  it("renders 0% when nothing is answered", () => {
    render(<ProgressCapsule current={1} total={10} answered={0} />);
    expect(screen.getByText(/0%/)).toBeInTheDocument();
  });

  it("renders 100% when all answered", () => {
    render(<ProgressCapsule current={10} total={10} answered={10} />);
    expect(screen.getByText(/100%/)).toBeInTheDocument();
  });

  it("renders 0% when total is 0 without throwing", () => {
    render(<ProgressCapsule current={0} total={0} answered={0} />);
    expect(screen.getByText(/0%/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the test to verify it fails (RED)**

Run: `cd frontend && npm test -- src/components/exam/ProgressCapsule.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Write the implementation**

Create `frontend/src/components/exam/ProgressCapsule.tsx`:

```tsx
import { cn } from "@/lib/utils";

export type ProgressCapsuleProps = {
  current: number;
  total: number;
  answered: number;
  /** 当 variant="dark" 时整体使用黑底白字（手机端 sticky 胶囊用）。 */
  variant?: "light" | "dark";
  className?: string;
};

/**
 * 进度胶囊：`Q 03 / 10 · 30%`，pill 形标签 + 内含 1px hairline 分割的进度条。
 * - 桌面端用 light 形态（白底 hairline）
 * - 手机端 sticky 用 dark 形态（黑底白字）
 */
export function ProgressCapsule({
  current,
  total,
  answered,
  variant = "light",
  className,
}: ProgressCapsuleProps) {
  const safeTotal = total > 0 ? total : 0;
  const percent = safeTotal > 0 ? Math.round((answered / safeTotal) * 100) : 0;
  const paddedCurrent = String(current).padStart(2, "0");
  const paddedTotal = String(safeTotal).padStart(2, "0");
  const isDark = variant === "dark";

  return (
    <div
      role="status"
      aria-label={`进度：第 ${current} 题，共 ${total} 题，已答 ${answered} 题`}
      className={cn(
        "inline-flex items-center gap-3 rounded-pill border px-4 py-2 font-mono text-caption uppercase tabular-nums",
        isDark ? "border-footer bg-footer text-canvas" : "border-hairline bg-canvas text-ink",
        className,
      )}
    >
      <span>
        Q&nbsp;{paddedCurrent}&nbsp;/&nbsp;{paddedTotal}
      </span>
      <span aria-hidden="true" className={cn("h-3 w-px", isDark ? "bg-footer-soft" : "bg-hairline")} />
      <span
        aria-hidden="true"
        className={cn(
          "relative h-1 w-24 overflow-hidden rounded-pill",
          isDark ? "bg-footer-soft/40" : "bg-hairline",
        )}
      >
        <span
          className={cn("absolute inset-y-0 left-0 rounded-pill", isDark ? "bg-canvas" : "bg-ink")}
          style={{ width: `${percent}%` }}
        />
      </span>
      <span>{percent}%</span>
    </div>
  );
}
```

- [ ] **Step 4: Run the test to verify it passes (GREEN)**

Run: `cd frontend && npm test -- src/components/exam/ProgressCapsule.test.tsx`
Expected: PASS — all 5 tests pass.

- [ ] **Step 5: Verify TypeScript still compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: Exit code 0.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/exam/ProgressCapsule.tsx frontend/src/components/exam/ProgressCapsule.test.tsx
git commit -m "feat(exam): 实现 ProgressCapsule 进度胶囊"
```

---

## Task 3: Create `components/exam/Timer.tsx` (with ≤5min pulse logic)

**Files:**
- Create: `frontend/src/components/exam/Timer.tsx`
- Create: `frontend/src/components/exam/Timer.test.tsx`

- [ ] **Step 1: Write the failing test first**

The Timer receives `remainingSeconds: number` as a prop (the parent computes it). The component handles:
- Two-digit zero-padded mm:ss display
- When `remainingSeconds <= 300` (5 minutes), text colour switches to `text-error` and the wrapper receives an `animate-pulse` class (Tailwind `animate-pulse` defaults to ~2000ms, so we test for the class existence and override duration via inline style if needed)
- `aria-live="polite"` is always present (so screen readers hear time updates)
- The REMAINING caption label renders above the time

Create `frontend/src/components/exam/Timer.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Timer } from "./Timer";

describe("Timer", () => {
  it("renders the REMAINING caption label", () => {
    render(<Timer remainingSeconds={1200} />);
    expect(screen.getByText(/REMAINING/i)).toBeInTheDocument();
  });

  it("renders padded mm:ss for > 5 minutes (green/no-pulse state)", () => {
    render(<Timer remainingSeconds={1500} />);
    const time = screen.getByText("25:00");
    expect(time).toBeInTheDocument();
    expect(time.className).not.toContain("text-error");
  });

  it("renders 00:00 when remaining is zero", () => {
    render(<Timer remainingSeconds={0} />);
    expect(screen.getByText("00:00")).toBeInTheDocument();
  });

  it("switches to text-error colour when remaining is <= 5 minutes", () => {
    render(<Timer remainingSeconds={299} />);
    const time = screen.getByText("04:59");
    expect(time.className).toContain("text-error");
  });

  it("applies the animate-pulse class when remaining is exactly 5 minutes", () => {
    render(<Timer remainingSeconds={300} />);
    const time = screen.getByText("05:00");
    const wrapper = time.parentElement;
    expect(wrapper?.className).toContain("animate-pulse");
  });

  it("does not apply animate-pulse when remaining is > 5 minutes", () => {
    render(<Timer remainingSeconds={301} />);
    const time = screen.getByText("05:01");
    const wrapper = time.parentElement;
    expect(wrapper?.className).not.toContain("animate-pulse");
  });

  it("always sets aria-live=polite on the live region", () => {
    render(<Timer remainingSeconds={1200} />);
    const time = screen.getByText("20:00");
    expect(time).toHaveAttribute("aria-live", "polite");
  });
});
```

- [ ] **Step 2: Run the test to verify it fails (RED)**

Run: `cd frontend && npm test -- src/components/exam/Timer.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Write the implementation**

Create `frontend/src/components/exam/Timer.tsx`:

```tsx
import { cn } from "@/lib/utils";

export type TimerProps = {
  /** 剩余秒数（父组件基于 attempt.started_at + duration_minutes 计算后传入）。 */
  remainingSeconds: number;
  /** 临界值（秒）：≤ 该值时数字变红并 pulse。默认 300（5 分钟）。 */
  criticalThresholdSeconds?: number;
  className?: string;
};

const PULSE_DURATION_MS = 1000;

function formatMmSs(totalSeconds: number): string {
  const safe = Math.max(0, Math.floor(totalSeconds));
  const minutes = Math.floor(safe / 60);
  const seconds = safe % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

/**
 * 考试倒计时：
 * - 大号 Manrope 600 / 32px / tabular-nums
 * - 上方 REMAINING 全大写小标签
 * - 剩余 ≤ 5 分钟时数字变红 + 1000ms pulse
 * - aria-live="polite" 让屏幕阅读器读到时间更新
 */
export function Timer({ remainingSeconds, criticalThresholdSeconds = 300, className }: TimerProps) {
  const isCritical = remainingSeconds <= criticalThresholdSeconds;
  const display = formatMmSs(remainingSeconds);

  return (
    <div className={cn("flex flex-col gap-1", className)}>
      <span className="text-caption uppercase tracking-[0.16em] text-muted">REMAINING · 剩余时间</span>
      <span
        aria-live="polite"
        aria-atomic="true"
        className={cn(
          "font-display text-[32px] font-semibold tabular-nums leading-none text-ink",
          isCritical && "text-error animate-pulse",
        )}
        style={isCritical ? { animationDuration: `${PULSE_DURATION_MS}ms` } : undefined}
      >
        {display}
      </span>
    </div>
  );
}
```

- [ ] **Step 4: Run the test to verify it passes (GREEN)**

Run: `cd frontend && npm test -- src/components/exam/Timer.test.tsx`
Expected: PASS — all 7 tests pass.

- [ ] **Step 5: Verify TypeScript still compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: Exit code 0.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/exam/Timer.tsx frontend/src/components/exam/Timer.test.tsx
git commit -m "feat(exam): 实现 Timer 含 ≤5min 红字 pulse 逻辑"
```

---

## Task 4: Create `components/exam/ExamNavigator.tsx` (replaces QuestionNavigator)

**Files:**
- Create: `frontend/src/components/exam/ExamNavigator.tsx`

- [ ] **Step 1: Write the implementation**

This is a pure rewrite — no TDD for the layout-heavy component, since it composes primitives only. Behaviour is covered indirectly by page-level tests in Tasks 7 and 9.

Create `frontend/src/components/exam/ExamNavigator.tsx`:

```tsx
import { ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { getQuestionTypeLabel, type QuestionNavItem } from "@/lib/questionNavigation";

const QUESTION_TYPE_ORDER = ["single", "multiple", "judge"];

export type ExamNavigatorProps = {
  items: QuestionNavItem[];
  activeId?: number | null;
  className?: string;
  /** 桌面端：右侧悬浮固定卡 */
  desktopLayout?: boolean;
  /** 手机端：底部 sheet 内容时改用全宽列表形态 */
  sheetLayout?: boolean;
  onJump: (targetId: string, itemId: number) => void;
  onSubmit?: () => void;
  submitLabel?: string;
};

function groupNavItems(items: QuestionNavItem[]) {
  const sortedTypes = Array.from(new Set(items.map((item) => item.type))).sort((a, b) => {
    const indexA = QUESTION_TYPE_ORDER.indexOf(a);
    const indexB = QUESTION_TYPE_ORDER.indexOf(b);
    if (indexA === -1 && indexB === -1) {
      return a.localeCompare(b);
    }
    if (indexA === -1) {
      return 1;
    }
    if (indexB === -1) {
      return -1;
    }
    return indexA - indexB;
  });
  return sortedTypes.map((type) => ({
    type,
    items: items.filter((item) => item.type === type),
  }));
}

/**
 * 题号导航（重写 QuestionNavigator）：
 * - 左侧垂直 hairline + 24px mono tabular 数字
 * - 桌面端：右侧 240px 悬浮固定，米色卡，章节分组 italic caps + mono 题号
 * - 手机端：作为底部 sheet 内容（全宽列表，无 sticky 定位）
 * - 已答 bg-success；当前：ink 边框 + 2px ring
 * - 底部「提前交卷」pill 黑底按钮（仅在提供 onSubmit 时显示）
 */
export function ExamNavigator({
  items,
  activeId,
  className,
  desktopLayout = true,
  sheetLayout = false,
  onJump,
  onSubmit,
  submitLabel = "提前交卷",
}: ExamNavigatorProps) {
  const groups = groupNavItems(items);
  const hasSubmittedResult = items.some((item) => item.submittedResult);

  if (!items.length) {
    return null;
  }

  return (
    <section
      aria-label="题号导航"
      className={cn(
        "flex flex-col gap-4",
        desktopLayout && "rounded-lg border border-hairline bg-surface-card p-5 shadow-card",
        sheetLayout && "bg-canvas p-5",
        className,
      )}
    >
      <header className="flex items-baseline justify-between border-b border-hairline pb-3">
        <h3 className="font-display text-display-sm font-semibold text-ink">题号导航</h3>
        <span className="text-caption uppercase tracking-[0.16em] text-muted">共 {items.length} 题</span>
      </header>

      <div className="flex flex-col gap-4 overflow-y-auto overscroll-contain">
        {groups.map((group) => (
          <div key={group.type} className="flex flex-col gap-2">
            <div className="flex items-baseline justify-between">
              <span className="font-display text-caption italic uppercase tracking-[0.18em] text-muted">
                CHAPTER&nbsp;{String(group.items[0]?.displayIndex ?? "").padStart(2, "0")}
                &nbsp;·&nbsp;{getQuestionTypeLabel(group.type)}
              </span>
              <span className="text-body-sm text-muted">{group.items.length} 题</span>
            </div>
            <ul className="grid grid-cols-5 gap-2">
              {group.items.map((item) => (
                <li key={item.id} className="contents">
                  <button
                    type="button"
                    onClick={() => onJump(item.targetId, item.id)}
                    aria-label={`跳转到第 ${item.displayIndex} 题`}
                    aria-current={activeId === item.id ? "true" : undefined}
                    className={cn(
                      "flex h-10 items-center justify-center rounded-md border font-mono text-base tabular-nums transition-colors",
                      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2",
                      !item.answered && "border-hairline bg-canvas text-ink",
                      item.answered && !item.submittedResult && "border-ink bg-ink text-canvas",
                      item.submittedResult === "correct" &&
                        "border-success bg-success text-canvas",
                      item.submittedResult === "wrong" && "border-error bg-error text-canvas",
                      activeId === item.id && "ring-2 ring-ink ring-offset-2",
                    )}
                  >
                    {item.displayIndex}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {hasSubmittedResult ? (
        <div className="flex flex-wrap items-center gap-3 border-t border-hairline pt-3 text-body-sm text-muted">
          <span className="inline-flex items-center gap-1">
            <span className="size-2 rounded-full border border-hairline" />
            未作答
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="size-2 rounded-full bg-ink" />
            已作答
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="size-2 rounded-full bg-success" />
            正确
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="size-2 rounded-full bg-error" />
            错误
          </span>
        </div>
      ) : null}

      {onSubmit ? (
        <Button type="button" onClick={onSubmit} className="w-full">
          {submitLabel}
          <ChevronRight data-icon="inline-end" />
        </Button>
      ) : null}
    </section>
  );
}
```

Note: `data-icon="inline-end"` requires either Phase 2 `button.tsx` to honour the attribute (recommended) or be a no-op if absent. Verify with `grep -n "inline-end" frontend/src/components/ui/button.tsx`. If absent, drop the `data-icon="inline-end"` markup — Lucide icon stays at its rendered size.

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: Exit code 0.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/exam/ExamNavigator.tsx
git commit -m "feat(exam): 实现 ExamNavigator 桌面+手机双形态题号导航"
```

---

## Task 5: Create `components/exam/ExamFocusMode.tsx` (composition container)

**Files:**
- Create: `frontend/src/components/exam/ExamFocusMode.tsx`

This is a layout component composing `ProgressCapsule`, `Timer`, `OptionCard`, the question stem area, and the prev/save/next nav buttons. The parent page owns state and passes it down.

- [ ] **Step 1: Write the implementation**

Create `frontend/src/components/exam/ExamFocusMode.tsx`:

```tsx
import { ChevronLeft, ChevronRight, Save, Send } from "lucide-react";
import { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import { OptionCard } from "./OptionCard";
import { ProgressCapsule } from "./ProgressCapsule";
import { Timer } from "./Timer";

export type ExamFocusModeProps = {
  /** 顶部进度胶囊（左侧）和倒计时（右侧） */
  progress: {
    current: number;
    total: number;
    answered: number;
  };
  remainingSeconds: number;

  /** 题干头部 */
  stem: {
    chapterLabel: string; // 例如 "CHAPTER A · SINGLE · 2 分"
    title: string; // 题干正文
  };

  /** 选项列表（父组件根据答案状态计算 selected） */
  options: Array<{
    label: string;
    content: string;
    selected: boolean;
  }>;
  onSelectOption: (label: string) => void;

  /** 底部按钮组 */
  nav: {
    onPrev?: () => void;
    onSave?: () => void;
    onNext?: () => void;
    prevDisabled?: boolean;
    nextDisabled?: boolean;
    saveLabel?: string;
    nextLabel?: string;
    saving?: boolean;
  };

  /** 整页容器 className（手机端用 fixed inset-0） */
  className?: string;
  children?: ReactNode;
};

/**
 * Focus Mode 单题全屏容器。
 * 桌面端：嵌入主区，顶部 ProgressCapsule + Timer，stem 卡 + OptionCard 列表，底部 nav 按钮。
 * 手机端：传 className="fixed inset-0 bg-canvas overflow-y-auto pb-24" 即可。
 */
export function ExamFocusMode({
  progress,
  remainingSeconds,
  stem,
  options,
  onSelectOption,
  nav,
  className,
  children,
}: ExamFocusModeProps) {
  return (
    <div className={cn("flex flex-col gap-6", className)}>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <ProgressCapsule
          current={progress.current}
          total={progress.total}
          answered={progress.answered}
        />
        <Timer remainingSeconds={remainingSeconds} />
      </div>

      <article className="flex flex-col gap-6 rounded-lg border border-hairline bg-surface-card p-6 shadow-card md:p-8">
        <header className="flex flex-col gap-2 border-b border-hairline pb-4">
          <span className="font-display text-caption italic uppercase tracking-[0.18em] text-muted">
            {stem.chapterLabel}
          </span>
          <h2 className="font-display text-[26px] font-semibold leading-snug tracking-[-0.02em] text-ink">
            {stem.title}
          </h2>
        </header>

        <div className="flex flex-col gap-3">
          {options.map((option) => (
            <OptionCard
              key={option.label}
              label={option.label}
              content={option.content}
              selected={option.selected}
              onSelect={onSelectOption}
            />
          ))}
        </div>

        {children ? <div className="border-t border-hairline pt-4">{children}</div> : null}

        <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-hairline pt-4">
          <Button
            type="button"
            variant="outline"
            onClick={nav.onPrev}
            disabled={nav.prevDisabled || !nav.onPrev}
            aria-label="上一题"
          >
            <ChevronLeft data-icon="inline-start" />
            上一题
          </Button>

          <div className="flex flex-wrap items-center gap-3">
            {nav.onSave ? (
              <Button
                type="button"
                variant="outline"
                onClick={nav.onSave}
                disabled={nav.saving}
                aria-label={nav.saveLabel ?? "暂存答案"}
              >
                <Save data-icon="inline-start" />
                {nav.saving ? "正在暂存" : (nav.saveLabel ?? "暂存答案")}
              </Button>
            ) : null}
            {nav.onNext ? (
              <Button type="button" onClick={nav.onNext} disabled={nav.nextDisabled} aria-label={nav.nextLabel ?? "下一题"}>
                {nav.nextLabel ?? "下一题"}
                <ChevronRight data-icon="inline-end" />
              </Button>
            ) : null}
          </div>
        </footer>
      </article>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: Exit code 0.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/exam/ExamFocusMode.tsx
git commit -m "feat(exam): 实现 ExamFocusMode 单题全屏作答容器"
```

---

## Task 6: Rewrite `pages/LoginPage.tsx`

**Files:**
- Modify: `frontend/src/pages/LoginPage.tsx` (full rewrite)

- [ ] **Step 1: Replace `frontend/src/pages/LoginPage.tsx`**

```tsx
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { LogIn } from "lucide-react";
import { useForm } from "react-hook-form";
import { Navigate, useNavigate, useOutletContext } from "react-router-dom";
import { z } from "zod";

import { loginCandidate as requestCandidateLogin } from "@/api/auth";
import { ChapterNumber } from "@/components/editorial/ChapterNumber";
import { Wordmark } from "@/components/editorial/Wordmark";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { CandidateSessionContext } from "@/components/layout/CandidateLayout";

const schema = z.object({
  name: z.string().min(1, "请输入姓名"),
  employee_no: z.string().optional(),
});

type LoginForm = z.infer<typeof schema>;

export function LoginPage() {
  const navigate = useNavigate();
  const { candidate, loginCandidate } = useOutletContext<CandidateSessionContext>();
  const form = useForm<LoginForm>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", employee_no: "" },
  });
  const mutation = useMutation({
    mutationFn: requestCandidateLogin,
    onSuccess: (nextCandidate) => {
      loginCandidate(nextCandidate);
      navigate("/exams", { replace: true });
    },
  });

  if (candidate) {
    return <Navigate to="/exams" replace />;
  }

  return (
    <div className="flex min-h-screen flex-col bg-canvas-warm">
      <header className="border-b border-hairline-soft bg-canvas">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 md:px-6">
          <Wordmark subtitle="— internal exam platform" />
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center gap-8 px-4 py-12 md:px-8 md:py-16">
        <div className="flex flex-col gap-6">
          <ChapterNumber chapter="01" title="WELCOME" />
          <h1 className="font-display text-[40px] font-semibold italic leading-[1.05] tracking-[-0.04em] text-ink md:text-[72px]">
            坐下来，开始考试。
          </h1>
          <p className="max-w-xl text-body-lg text-muted">
            填写姓名即可进入练习或考试。系统会先在应考名单中匹配；如有员工号会优先用于识别。整个过程不会发送邮件或短信。
          </p>
        </div>

        <Card className="bg-canvas-warm">
          <CardContent className="p-6 md:p-8">
            <form
              className="flex flex-col gap-5"
              onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
              noValidate
            >
              <div className="flex flex-col gap-2">
                <Label htmlFor="name">
                  姓名 · <span className="text-muted">Name</span>
                </Label>
                <Input
                  id="name"
                  autoComplete="name"
                  aria-invalid={Boolean(form.formState.errors.name)}
                  {...form.register("name")}
                />
                {form.formState.errors.name ? (
                  <p className="text-body-sm text-error">{form.formState.errors.name.message}</p>
                ) : null}
              </div>

              <div className="flex flex-col gap-2">
                <Label htmlFor="employee_no">
                  员工号 · <span className="text-muted">Employee No.</span>
                  <span className="ml-1 text-muted">（可选）</span>
                </Label>
                <Input
                  id="employee_no"
                  autoComplete="off"
                  placeholder="例如 10042"
                  {...form.register("employee_no")}
                />
              </div>

              <Button type="submit" size="lg" className="h-12 w-full" disabled={mutation.isPending}>
                <LogIn data-icon="inline-start" />
                {mutation.isPending ? "正在进入" : "进入系统"}
              </Button>

              {mutation.isError ? (
                <p className="text-body-sm text-error">
                  未找到匹配的考试人员，请核对姓名或员工号。
                </p>
              ) : null}
              {mutation.data ? (
                <p className="text-body-sm text-muted">已识别：{mutation.data.name}</p>
              ) : null}
            </form>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: Exit code 0.

- [ ] **Step 3: Smoke-test in dev server**

```bash
cd frontend && npm run dev &
sleep 4
curl -sS http://localhost:5173/login | head -20
pkill -f vite
```

Expected: HTML shell loads; no runtime errors in console.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/LoginPage.tsx
git commit -m "feat(login): 重写登录页为学术编辑风格米色卡 + italic h1"
```

---

## Task 7: Rewrite `pages/ExamTakingPage.tsx` (Focus Mode)

**Files:**
- Modify: `frontend/src/pages/ExamTakingPage.tsx` (full rewrite)

Behaviour contract (preserve from current implementation):
- Countdown based on `attempt.started_at + duration_minutes * 60_000`
- Auto-submit when remaining hits 0 (existing `useEffect` pattern — keep)
- ← / → keyboard navigation between questions (only when not in input/textarea)
- API calls unchanged: `getAttempt`, `saveAttemptAnswers`, `submitAttempt`
- Snapshot field names unchanged: `stem_snapshot`, `options_snapshot`, `score`, `sort_order`, `selected_answer`

- [ ] **Step 1: Replace `frontend/src/pages/ExamTakingPage.tsx`**

```tsx
import { useMutation, useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, List, LogOut, Save, Send } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { getAttempt, saveAttemptAnswers, submitAttempt } from "@/api/attempts";
import { getActiveExams } from "@/api/exams";
import { ExamFocusMode } from "@/components/exam/ExamFocusMode";
import { ExamNavigator } from "@/components/exam/ExamNavigator";
import { ProgressCapsule } from "@/components/exam/ProgressCapsule";
import { Timer } from "@/components/exam/Timer";
import { ChapterNumber } from "@/components/editorial/ChapterNumber";
import { Wordmark } from "@/components/editorial/Wordmark";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn, splitAnswer, toggleMultipleAnswer } from "@/lib/utils";
import { buildQuestionNavItems, getQuestionTypeLabel } from "@/lib/questionNavigation";
import type { AttemptQuestion } from "@/types/attempt";

type AnswerMap = Record<number, string>;

export function ExamTakingPage() {
  const { examId = "1" } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const attemptId = searchParams.get("attemptId");

  const [answers, setAnswers] = useState<AnswerMap>({});
  const [now, setNow] = useState(() => Date.now());
  const [activeIndex, setActiveIndex] = useState(0);
  const [sheetOpen, setSheetOpen] = useState(false);

  const { data: attempt, isLoading } = useQuery({
    queryKey: ["attempt", attemptId],
    queryFn: () => getAttempt(attemptId ?? ""),
    enabled: Boolean(attemptId),
  });

  const { data: exams = [] } = useQuery({ queryKey: ["active-exams"], queryFn: getActiveExams });

  const saveMutation = useMutation({
    mutationFn: (items: Array<{ attempt_question_id: number; selected_answer: string }>) =>
      saveAttemptAnswers(attemptId ?? "", items),
  });

  const submitMutation = useMutation({
    mutationFn: async () => {
      if (!attempt) {
        return null;
      }
      const items = attempt.questions.map((question) => ({
        attempt_question_id: question.id,
        selected_answer: answers[question.id] ?? "",
      }));
      await saveAttemptAnswers(String(attempt.id), items);
      return submitAttempt(String(attempt.id), "manual");
    },
    onSuccess: (result) => {
      if (result) {
        navigate(`/exams/${examId}/result?attemptId=${result.attempt_id}`);
      }
    },
  });

  // Hydrate answers from attempt snapshot
  useEffect(() => {
    if (!attempt) {
      return;
    }
    setAnswers(
      Object.fromEntries(
        attempt.questions.map((question) => [question.id, question.selected_answer ?? ""]),
      ),
    );
  }, [attempt]);

  // 1s tick for countdown
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const durationMinutes = exams.find((exam) => String(exam.id) === examId)?.duration_minutes;

  const remainingSeconds = useMemo(() => {
    if (!attempt || !durationMinutes) {
      return Number.POSITIVE_INFINITY;
    }
    const endsAt = new Date(attempt.started_at).getTime() + durationMinutes * 60 * 1000;
    return Math.max(0, Math.floor((endsAt - now) / 1000));
  }, [attempt, durationMinutes, now]);

  const autoSubmittedRef = useRef(false);
  useEffect(() => {
    if (!attempt) {
      return;
    }
    if (remainingSeconds === 0 && !autoSubmittedRef.current && !submitMutation.isPending) {
      autoSubmittedRef.current = true;
      submitMutation.mutate();
    }
  }, [attempt, remainingSeconds, submitMutation]);

  const total = attempt?.questions.length ?? 0;
  const activeQuestion: AttemptQuestion | undefined = attempt?.questions[activeIndex];

  const answeredCount = useMemo(() => {
    if (!attempt) {
      return 0;
    }
    return attempt.questions.reduce(
      (count, question) => count + (answers[question.id] ? 1 : 0),
      0,
    );
  }, [attempt, answers]);

  const navItems = useMemo(
    () =>
      buildQuestionNavItems({
        questions: attempt?.questions ?? [],
        answers,
        getTargetId: () => `exam-question-focus`,
      }),
    [answers, attempt?.questions],
  );

  function handleSingleChange(question: AttemptQuestion, label: string) {
    setAnswers((current) => ({ ...current, [question.id]: label }));
    saveMutation.mutate([{ attempt_question_id: question.id, selected_answer: label }]);
  }

  function handleMultipleChange(question: AttemptQuestion, label: string, checked: boolean) {
    const next = toggleMultipleAnswer(answers[question.id], label, checked);
    setAnswers((current) => ({ ...current, [question.id]: next }));
    saveMutation.mutate([{ attempt_question_id: question.id, selected_answer: next }]);
  }

  function handleSave() {
    if (!attempt) {
      return;
    }
    saveMutation.mutate(
      attempt.questions.map((question) => ({
        attempt_question_id: question.id,
        selected_answer: answers[question.id] ?? "",
      })),
    );
  }

  const goPrev = useCallback(() => {
    setActiveIndex((index) => Math.max(0, index - 1));
  }, []);

  const goNext = useCallback(() => {
    if (!attempt) {
      return;
    }
    setActiveIndex((index) => Math.min(attempt.questions.length - 1, index + 1));
  }, [attempt]);

  // Keyboard ← / → navigation (skip when typing)
  useEffect(() => {
    function handleKeydown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      if (target) {
        const tag = target.tagName.toLowerCase();
        if (tag === "input" || tag === "textarea" || target.isContentEditable) {
          return;
        }
      }
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        goPrev();
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        goNext();
      }
    }
    window.addEventListener("keydown", handleKeydown);
    return () => window.removeEventListener("keydown", handleKeydown);
  }, [goNext, goPrev]);

  if (!attemptId) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12 md:px-8">
        <Card className="bg-surface-card">
          <CardContent className="flex flex-col gap-4 p-8">
            <ChapterNumber chapter="00" title="NOT STARTED" />
            <h1 className="font-display text-display-lg font-semibold italic tracking-[-0.03em] text-ink">
              未开始考试。
            </h1>
            <Button asChild>
              <Link to={`/exams/${examId}/start`}>返回考试说明</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (isLoading || !attempt || !activeQuestion) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12 md:px-8">
        <Card className="bg-surface-card">
          <CardContent className="p-8">
            <p className="text-body text-muted">正在加载题目</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const isMultiple = activeQuestion.question_type === "multiple";
  const selectedLabels = isMultiple
    ? splitAnswer(answers[activeQuestion.id])
    : [];
  const singleValue = !isMultiple ? answers[activeQuestion.id] ?? "" : "";

  const stemChapterLabel = `CHAPTER ${String(activeIndex + 1).padStart(2, "0")} · ${getQuestionTypeLabel(
    activeQuestion.question_type,
  ).toUpperCase()} · ${activeQuestion.score} 分`;

  return (
    <div className="flex min-h-screen flex-col bg-canvas-warm">
      {/* Top bar */}
      <header className="sticky top-0 z-30 border-b border-hairline-soft bg-canvas">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 md:px-6">
          <Wordmark subtitle={`— ${attempt.questions.length} 题`} />
          <div className="hidden items-center gap-3 md:flex">
            <ProgressCapsule current={activeIndex + 1} total={total} answered={answeredCount} />
            <Timer remainingSeconds={remainingSeconds} />
          </div>
          <Button asChild variant="ghost" size="icon" aria-label="退出考试">
            <Link to="/exams">
              <LogOut />
            </Link>
          </Button>
        </div>
      </header>

      {/* Desktop layout */}
      <div className="mx-auto hidden w-full max-w-6xl flex-1 grid-cols-[1fr_240px] gap-8 px-4 py-8 md:px-8 lg:grid">
        <div id="exam-question-focus">
          <ExamFocusMode
            progress={{ current: activeIndex + 1, total, answered: answeredCount }}
            remainingSeconds={remainingSeconds}
            stem={{
              chapterLabel: stemChapterLabel,
              title: activeQuestion.stem_snapshot,
            }}
            options={activeQuestion.options_snapshot.map((option) => ({
              label: option.label,
              content: option.content,
              selected: isMultiple
                ? selectedLabels.includes(option.label)
                : singleValue === option.label,
            }))}
            onSelectOption={(label) => {
              if (isMultiple) {
                const currentlyChecked = selectedLabels.includes(label);
                handleMultipleChange(activeQuestion, label, !currentlyChecked);
              } else {
                handleSingleChange(activeQuestion, label);
              }
            }}
            nav={{
              onPrev: goPrev,
              onSave: handleSave,
              onNext: goNext,
              prevDisabled: activeIndex === 0,
              nextDisabled: activeIndex === total - 1,
              saving: saveMutation.isPending,
            }}
          />
        </div>
        <aside className="sticky top-24 self-start">
          <ExamNavigator
            items={navItems}
            activeId={activeQuestion.id}
            desktopLayout
            onJump={(_targetId, id) => {
              const idx = attempt.questions.findIndex((q) => q.id === id);
              if (idx >= 0) {
                setActiveIndex(idx);
              }
            }}
            onSubmit={() => submitMutation.mutate()}
            submitLabel={submitMutation.isPending ? "正在交卷" : "提前交卷"}
          />
        </aside>
      </div>

      {/* Mobile layout */}
      <div className="flex flex-1 flex-col px-4 py-6 lg:hidden">
        <ExamFocusMode
          className="pb-24"
          progress={{ current: activeIndex + 1, total, answered: answeredCount }}
          remainingSeconds={remainingSeconds}
          stem={{
            chapterLabel: stemChapterLabel,
            title: activeQuestion.stem_snapshot,
          }}
          options={activeQuestion.options_snapshot.map((option) => ({
            label: option.label,
            content: option.content,
            selected: isMultiple
              ? selectedLabels.includes(option.label)
              : singleValue === option.label,
          }))}
          onSelectOption={(label) => {
            if (isMultiple) {
              const currentlyChecked = selectedLabels.includes(label);
              handleMultipleChange(activeQuestion, label, !currentlyChecked);
            } else {
              handleSingleChange(activeQuestion, label);
            }
          }}
          nav={{
            onPrev: goPrev,
            onNext: goNext,
            prevDisabled: activeIndex === 0,
            nextDisabled: activeIndex === total - 1,
          }}
        />

        {/* Sticky bottom progress capsule + FAB */}
        <div className="fixed inset-x-0 bottom-3 z-40 flex justify-center px-3">
          <div className="flex w-full max-w-md items-center gap-2 rounded-pill border border-footer bg-footer p-2 shadow-elevate">
            <ProgressCapsule
              current={activeIndex + 1}
              total={total}
              answered={answeredCount}
              variant="dark"
              className="flex-1"
            />
            <button
              type="button"
              aria-label="打开题号导航"
              onClick={() => setSheetOpen(true)}
              className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-pill text-canvas"
            >
              <List />
            </button>
          </div>
        </div>
      </div>

      {/* Mobile navigator sheet (portal) */}
      {sheetOpen
        ? createPortal(
            <MobileNavigatorSheet
              items={navItems}
              activeId={activeQuestion.id}
              onJump={(id) => {
                const idx = attempt.questions.findIndex((q) => q.id === id);
                if (idx >= 0) {
                  setActiveIndex(idx);
                }
                setSheetOpen(false);
              }}
              onSubmit={() => {
                setSheetOpen(false);
                submitMutation.mutate();
              }}
              submitting={submitMutation.isPending}
              onClose={() => setSheetOpen(false)}
            />,
            document.body,
          )
        : null}

      {saveMutation.isError ? (
        <p className="sr-only" role="alert">
          暂存失败，请稍后重试。
        </p>
      ) : null}
      {submitMutation.isError ? (
        <p className="sr-only" role="alert">
          交卷失败，请确认考试仍在进行中。
        </p>
      ) : null}
    </div>
  );
}

function MobileNavigatorSheet({
  items,
  activeId,
  onJump,
  onSubmit,
  submitting,
  onClose,
}: {
  items: ReturnType<typeof buildQuestionNavItems>;
  activeId: number;
  onJump: (id: number) => void;
  onSubmit: () => void;
  submitting: boolean;
  onClose: () => void;
}) {
  // Body scroll lock while sheet open
  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, []);

  return (
    <div
      className="fixed inset-0 z-50 flex items-end bg-ink/40"
      role="dialog"
      aria-modal="true"
      aria-label="题号导航"
      onClick={onClose}
    >
      <div
        className={cn(
          "flex h-[80vh] w-full flex-col gap-4 rounded-t-lg bg-canvas p-5 shadow-elevate",
        )}
        onClick={(event) => event.stopPropagation()}
      >
        <header className="flex items-center justify-between border-b border-hairline pb-3">
          <span className="font-display text-display-sm font-semibold text-ink">题号导航</span>
          <Button type="button" variant="ghost" size="sm" onClick={onClose} aria-label="关闭">
            关闭
          </Button>
        </header>
        <div className="flex-1 overflow-y-auto overscroll-contain">
          <ExamNavigator
            items={items}
            activeId={activeId}
            sheetLayout
            desktopLayout={false}
            onJump={(_targetId, id) => onJump(id)}
          />
        </div>
        <Button type="button" onClick={onSubmit} disabled={submitting} className="w-full">
          <Send data-icon="inline-start" />
          {submitting ? "正在交卷" : "提前交卷"}
        </Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: Exit code 0.

- [ ] **Step 3: Smoke-test in dev server**

```bash
cd frontend && npm run dev &
sleep 4
curl -sS http://localhost:5173/exams/1/taking | head -20
pkill -f vite
```

Expected: HTML shell loads.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/ExamTakingPage.tsx
git commit -m "feat(exam): 重写作答页为 Focus Mode 桌面+手机双形态"
```

---

## Task 8: Rewrite `pages/ExamResultPage.tsx`

**Files:**
- Modify: `frontend/src/pages/ExamResultPage.tsx` (full rewrite)

- [ ] **Step 1: Replace `frontend/src/pages/ExamResultPage.tsx`**

```tsx
import { useQuery } from "@tanstack/react-query";
import { ChevronRight } from "lucide-react";
import { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { getAttemptResult } from "@/api/attempts";
import { ChapterNumber } from "@/components/editorial/ChapterNumber";
import { Wordmark } from "@/components/editorial/Wordmark";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function ExamResultPage() {
  const { examId = "1" } = useParams();
  const [searchParams] = useSearchParams();
  const attemptId = searchParams.get("attemptId");
  const [filter, setFilter] = useState<"all" | "wrong">("all");

  const { data: result, isLoading } = useQuery({
    queryKey: ["attempt-result", attemptId],
    queryFn: () => getAttemptResult(attemptId ?? ""),
    enabled: Boolean(attemptId),
  });

  const visibleQuestions =
    result?.questions.filter((question) =>
      filter === "wrong" ? !question.is_correct : true,
    ) ?? [];

  return (
    <div className="flex min-h-screen flex-col bg-canvas-warm">
      <header className="border-b border-hairline-soft bg-canvas">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 md:px-6">
          <Wordmark subtitle="— 结果" />
          <Button asChild variant="ghost" size="sm">
            <Link to="/exams">返回考试列表</Link>
          </Button>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-4 py-8 md:px-8 md:py-10">
        <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
          {/* Left: full-black score card */}
          <Card className="rounded-lg border-0 bg-footer text-canvas shadow-pop">
            <CardContent className="flex flex-col gap-6 p-6 md:p-8">
              <ChapterNumber chapter="99" title="RESULT" inverted />
              <h1 className="font-display text-[40px] font-semibold italic leading-[1.05] tracking-[-0.04em] text-canvas md:text-[48px]">
                考试结束。
              </h1>

              <div className="flex flex-col gap-2 border-t border-footer-soft/40 pt-6">
                <span className="text-caption uppercase tracking-[0.16em] text-footer-soft">
                  YOUR SCORE · 你的分数
                </span>
                <p className="font-display text-[56px] font-semibold tabular-nums leading-none tracking-[-0.04em] text-canvas md:text-[64px]">
                  {result ? `${result.score}` : isLoading ? "—" : "—"}
                  <span className="ml-2 text-body-lg text-footer-soft">
                    / {result ? result.total_score : "—"}
                  </span>
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-6 border-t border-footer-soft/40 pt-6 text-body">
                <div className="flex flex-col gap-1">
                  <span className="text-caption uppercase tracking-[0.16em] text-footer-soft">
                    正确
                  </span>
                  <span className="font-display text-display-md font-semibold tabular-nums text-success">
                    {result?.correct_count ?? "—"}
                  </span>
                </div>
                <div className="flex flex-col gap-1">
                  <span className="text-caption uppercase tracking-[0.16em] text-footer-soft">
                    错误
                  </span>
                  <span className="font-display text-display-md font-semibold tabular-nums text-error">
                    {result?.wrong_count ?? "—"}
                  </span>
                </div>
              </div>

              <Button asChild className="w-full bg-canvas text-ink hover:bg-canvas-warm">
                <Link to={`/exams/${examId}/ranking`}>
                  查看排名
                  <ChevronRight data-icon="inline-end" />
                </Link>
              </Button>
            </CardContent>
          </Card>

          {/* Right: answer list */}
          <section className="flex flex-col gap-4">
            <header className="flex flex-wrap items-end justify-between gap-3 border-b border-hairline pb-3">
              <div className="flex flex-col gap-1">
                <span className="font-display text-caption italic uppercase tracking-[0.18em] text-muted">
                  CHAPTER&nbsp;R · REVIEW
                </span>
                <h2 className="font-display text-display-md font-semibold tracking-[-0.02em] text-ink">
                  答案与解析
                </h2>
              </div>
              <div className="inline-flex items-center gap-2 rounded-pill border border-hairline bg-canvas p-1 text-body-sm">
                <button
                  type="button"
                  onClick={() => setFilter("all")}
                  className={cn(
                    "rounded-pill px-4 py-1",
                    filter === "all" ? "bg-ink text-canvas" : "text-muted",
                  )}
                >
                  全部 ({result?.questions.length ?? 0})
                </button>
                <button
                  type="button"
                  onClick={() => setFilter("wrong")}
                  className={cn(
                    "rounded-pill px-4 py-1",
                    filter === "wrong" ? "bg-ink text-canvas" : "text-muted",
                  )}
                >
                  只看错题 ({result?.wrong_count ?? 0})
                </button>
              </div>
            </header>

            <div className="flex flex-col gap-4">
              {visibleQuestions.length ? (
                visibleQuestions.map((question, index) => (
                  <article
                    key={question.attempt_question_id}
                    className="flex flex-col gap-3 rounded-lg border border-hairline bg-canvas p-5 shadow-card"
                  >
                    <header className="flex items-baseline justify-between gap-3">
                      <span className="font-mono text-caption uppercase tracking-[0.16em] text-muted">
                        Q&nbsp;
                        {String(
                          (result?.questions.findIndex(
                            (q) => q.attempt_question_id === question.attempt_question_id,
                          ) ?? index) + 1,
                        ).padStart(2, "0")}
                      </span>
                      <span
                        className={cn(
                          "text-caption uppercase tracking-[0.16em]",
                          question.is_correct ? "text-success" : "text-error",
                        )}
                      >
                        {question.is_correct ? "CORRECT · 正确" : "WRONG · 错误"}
                      </span>
                    </header>
                    <p className="text-body text-ink">{question.stem_snapshot}</p>
                    <dl className="grid gap-1 border-t border-hairline pt-3 text-body-sm">
                      <div className="flex flex-wrap items-baseline gap-2">
                        <dt className="text-caption uppercase tracking-[0.16em] text-muted">
                          你的答案
                        </dt>
                        <dd className="text-ink">{question.selected_answer || "未作答"}</dd>
                      </div>
                      <div className="flex flex-wrap items-baseline gap-2">
                        <dt className="text-caption uppercase tracking-[0.16em] text-muted">
                          正确答案
                        </dt>
                        <dd className="text-ink">{question.correct_answer_snapshot}</dd>
                      </div>
                      <div className="flex flex-wrap items-baseline gap-2">
                        <dt className="text-caption uppercase tracking-[0.16em] text-muted">
                          得分
                        </dt>
                        <dd className="font-mono tabular-nums text-ink">
                          {question.score_awarded} / {question.score}
                        </dd>
                      </div>
                    </dl>
                    {question.analysis_snapshot ? (
                      <p className="text-body-sm text-muted">
                        <span className="text-caption uppercase tracking-[0.16em]">解析 · </span>
                        {question.analysis_snapshot}
                      </p>
                    ) : null}
                  </article>
                ))
              ) : (
                <p className="text-body-sm text-muted">
                  {isLoading ? "正在加载结果" : "暂无结果，请先完成考试。"}
                </p>
              )}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
```

Note: `ChapterNumber` with `inverted` prop means it renders light-on-dark. If Phase 3 `ChapterNumber` doesn't accept that prop yet, remove `inverted` here and confirm it still reads well on the black card. The plan accepts either approach — the contract is "the chapter label appears on the black score card."

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: Exit code 0.

- [ ] **Step 3: Smoke-test in dev server**

```bash
cd frontend && npm run dev &
sleep 4
curl -sS http://localhost:5173/exams/1/result?attemptId=1 | head -20
pkill -f vite
```

Expected: HTML shell loads.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/ExamResultPage.tsx
git commit -m "feat(exam): 重写考试结果页为黑卡成绩 + 全部/只看错题切换"
```

---

## Task 9: Rewrite `pages/PracticePage.tsx`

**Files:**
- Modify: `frontend/src/pages/PracticePage.tsx` (full rewrite)

- [ ] **Step 1: Replace `frontend/src/pages/PracticePage.tsx`**

```tsx
import { useMutation, useQuery } from "@tanstack/react-query";
import { CheckCircle2, List, Send, XCircle } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { Link, useOutletContext } from "react-router-dom";

import { getPracticeQuestions, submitPracticeAnswer } from "@/api/questions";
import { ExamFocusMode } from "@/components/exam/ExamFocusMode";
import { ExamNavigator } from "@/components/exam/ExamNavigator";
import { ProgressCapsule } from "@/components/exam/ProgressCapsule";
import { ChapterNumber } from "@/components/editorial/ChapterNumber";
import { Wordmark } from "@/components/editorial/Wordmark";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { CandidateSessionContext } from "@/components/layout/CandidateLayout";
import { cn, splitAnswer, toggleMultipleAnswer } from "@/lib/utils";
import { buildQuestionNavItems, getQuestionTypeLabel } from "@/lib/questionNavigation";
import type { PracticeAnswerResult, Question } from "@/types/question";

type AnswerMap = Record<number, string>;
type ResultMap = Record<number, PracticeAnswerResult>;

export function PracticePage() {
  const { candidate } = useOutletContext<CandidateSessionContext>();
  const [answers, setAnswers] = useState<AnswerMap>({});
  const [results, setResults] = useState<ResultMap>({});
  const [activeIndex, setActiveIndex] = useState(0);
  const [sheetOpen, setSheetOpen] = useState(false);

  const { data = [], isLoading } = useQuery({
    queryKey: ["practice-questions"],
    queryFn: getPracticeQuestions,
  });

  const mutation = useMutation({
    mutationFn: submitPracticeAnswer,
    onSuccess: (result) => {
      setResults((current) => ({ ...current, [result.question_id]: result }));
    },
  });

  const total = data.length;
  const activeQuestion: Question | undefined = data[activeIndex];
  const activeResult = activeQuestion ? results[activeQuestion.id] : undefined;

  const answeredCount = useMemo(() => data.reduce((c, q) => c + (answers[q.id] ? 1 : 0), 0), [
    answers,
    data,
  ]);

  const navItems = useMemo(
    () =>
      buildQuestionNavItems({
        questions: data,
        answers,
        getSubmittedResult: (question) => {
          const result = results[question.id];
          return result ? (result.is_correct ? "correct" : "wrong") : undefined;
        },
        getTargetId: () => `practice-question-focus`,
      }),
    [answers, data, results],
  );

  function handleSingleChange(question: Question, label: string) {
    setAnswers((current) => ({ ...current, [question.id]: label }));
  }

  function handleMultipleChange(question: Question, label: string, checked: boolean) {
    setAnswers((current) => ({
      ...current,
      [question.id]: toggleMultipleAnswer(current[question.id], label, checked),
    }));
  }

  function handleSubmit(question: Question) {
    if (!candidate) {
      return;
    }
    mutation.mutate({
      candidate_id: candidate.id,
      question_id: question.id,
      selected_answer: answers[question.id] ?? "",
    });
  }

  const goPrev = useCallback(() => setActiveIndex((index) => Math.max(0, index - 1)), []);
  const goNext = useCallback(
    () => setActiveIndex((index) => Math.min(data.length - 1, index + 1)),
    [data.length],
  );

  useEffect(() => {
    function handleKeydown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      if (target) {
        const tag = target.tagName.toLowerCase();
        if (tag === "input" || tag === "textarea" || target.isContentEditable) {
          return;
        }
      }
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        goPrev();
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        goNext();
      }
    }
    window.addEventListener("keydown", handleKeydown);
    return () => window.removeEventListener("keydown", handleKeydown);
  }, [goNext, goPrev]);

  if (!candidate) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12 md:px-8">
        <Card className="bg-surface-card">
          <CardContent className="flex flex-col gap-4 p-8">
            <ChapterNumber chapter="00" title="NOT LOGGED IN" />
            <h1 className="font-display text-display-lg font-semibold italic tracking-[-0.03em] text-ink">
              请先登录考试人。
            </h1>
            <p className="text-body text-muted">登录后可提交练习答案并记录练习结果。</p>
            <Button asChild>
              <Link to="/login">去登录</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (isLoading || total === 0 || !activeQuestion) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12 md:px-8">
        <Card className="bg-surface-card">
          <CardContent className="flex flex-col gap-4 p-8">
            <ChapterNumber chapter="PR" title="PRACTICE" />
            <h1 className="font-display text-display-lg font-semibold italic tracking-[-0.03em] text-ink">
              {total === 0 ? "暂无题目" : "练习模式"}
            </h1>
            <p className="text-body text-muted">
              {total === 0
                ? "管理员导入题库后会显示在这里。"
                : `当前 ${total} 道题，可逐题提交并查看对错。`}
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const isMultiple = activeQuestion.question_type === "multiple";
  const selectedLabels = isMultiple ? splitAnswer(answers[activeQuestion.id]) : [];
  const singleValue = !isMultiple ? answers[activeQuestion.id] ?? "" : "";

  const stemChapterLabel = `CHAPTER ${String(activeIndex + 1).padStart(2, "0")} · ${getQuestionTypeLabel(
    activeQuestion.question_type,
  ).toUpperCase()} · ${activeQuestion.score} 分`;

  const chapterNumber = `PR · PRACTICE`;

  return (
    <div className="flex min-h-screen flex-col bg-canvas-warm">
      <header className="sticky top-0 z-30 border-b border-hairline-soft bg-canvas">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 md:px-6">
          <Wordmark subtitle="— 练习" />
          <div className="hidden items-center gap-3 md:flex">
            <ProgressCapsule current={activeIndex + 1} total={total} answered={answeredCount} />
          </div>
          <Button asChild variant="ghost" size="sm">
            <Link to="/exams">返回考试</Link>
          </Button>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-4 py-8 md:px-8 md:py-10">
        <div className="flex flex-col gap-3 border-b border-hairline pb-4">
          <ChapterNumber chapter={chapterNumber.split(" · ")[0]} title="PRACTICE" />
          <h1 className="font-display text-display-lg font-semibold italic tracking-[-0.03em] text-ink md:text-display-xl">
            刷一遍，记一遍。
          </h1>
          <p className="max-w-2xl text-body-lg text-muted">
            练习结果不计入正式成绩。提交后即时显示对错与解析。
          </p>
        </div>

        {/* Desktop layout */}
        <div className="hidden flex-1 grid-cols-[1fr_240px] gap-8 lg:grid">
          <div id="practice-question-focus" className="flex flex-col gap-4">
            <ExamFocusMode
              progress={{ current: activeIndex + 1, total, answered: answeredCount }}
              remainingSeconds={Number.POSITIVE_INFINITY}
              stem={{
                chapterLabel: stemChapterLabel,
                title: activeQuestion.stem,
              }}
              options={activeQuestion.options.map((option) => ({
                label: option.label,
                content: option.content,
                selected: isMultiple
                  ? selectedLabels.includes(option.label)
                  : singleValue === option.label,
              }))}
              onSelectOption={(label) => {
                if (isMultiple) {
                  const currentlyChecked = selectedLabels.includes(label);
                  handleMultipleChange(activeQuestion, label, !currentlyChecked);
                } else {
                  handleSingleChange(activeQuestion, label);
                }
              }}
              nav={{
                onPrev: goPrev,
                onNext: goNext,
                prevDisabled: activeIndex === 0,
                nextDisabled: activeIndex === total - 1,
              }}
            >
              <div className="flex flex-wrap items-center gap-3">
                <Button
                  type="button"
                  onClick={() => handleSubmit(activeQuestion)}
                  disabled={!answers[activeQuestion.id] || mutation.isPending}
                  aria-label="提交本题"
                >
                  <Send data-icon="inline-start" />
                  {mutation.isPending ? "正在提交" : "提交本题"}
                </Button>
                {activeResult ? (
                  <span
                    className={cn(
                      "inline-flex items-center gap-2 text-body",
                      activeResult.is_correct ? "text-success" : "text-error",
                    )}
                  >
                    {activeResult.is_correct ? <CheckCircle2 /> : <XCircle />}
                    {activeResult.is_correct ? "回答正确" : "回答错误"}，正确答案：
                    {activeResult.correct_answer}
                  </span>
                ) : (
                  <span className="text-body-sm text-muted">提交后显示正确答案和解析。</span>
                )}
              </div>
              {activeResult?.analysis ? (
                <p className="text-body-sm text-muted">
                  <span className="text-caption uppercase tracking-[0.16em]">解析 · </span>
                  {activeResult.analysis}
                </p>
              ) : null}
            </ExamFocusMode>
          </div>

          <aside className="sticky top-24 self-start">
            <ExamNavigator
              items={navItems}
              activeId={activeQuestion.id}
              desktopLayout
              onJump={(_targetId, id) => {
                const idx = data.findIndex((q) => q.id === id);
                if (idx >= 0) {
                  setActiveIndex(idx);
                }
              }}
            />
          </aside>
        </div>

        {/* Mobile layout */}
        <div className="flex flex-1 flex-col pb-24 lg:hidden">
          <ExamFocusMode
            className="pb-24"
            progress={{ current: activeIndex + 1, total, answered: answeredCount }}
            remainingSeconds={Number.POSITIVE_INFINITY}
            stem={{
              chapterLabel: stemChapterLabel,
              title: activeQuestion.stem,
            }}
            options={activeQuestion.options.map((option) => ({
              label: option.label,
              content: option.content,
              selected: isMultiple
                ? selectedLabels.includes(option.label)
                : singleValue === option.label,
            }))}
            onSelectOption={(label) => {
              if (isMultiple) {
                const currentlyChecked = selectedLabels.includes(label);
                handleMultipleChange(activeQuestion, label, !currentlyChecked);
              } else {
                handleSingleChange(activeQuestion, label);
              }
            }}
            nav={{
              onPrev: goPrev,
              onNext: goNext,
              prevDisabled: activeIndex === 0,
              nextDisabled: activeIndex === total - 1,
            }}
          >
            <div className="flex flex-wrap items-center gap-3">
              <Button
                type="button"
                onClick={() => handleSubmit(activeQuestion)}
                disabled={!answers[activeQuestion.id] || mutation.isPending}
              >
                <Send data-icon="inline-start" />
                {mutation.isPending ? "正在提交" : "提交本题"}
              </Button>
              {activeResult ? (
                <span
                  className={cn(
                    "inline-flex items-center gap-2 text-body",
                    activeResult.is_correct ? "text-success" : "text-error",
                  )}
                >
                  {activeResult.is_correct ? <CheckCircle2 /> : <XCircle />}
                  {activeResult.is_correct ? "回答正确" : "回答错误"}，正确答案：
                  {activeResult.correct_answer}
                </span>
              ) : null}
            </div>
            {activeResult?.analysis ? (
              <p className="text-body-sm text-muted">
                <span className="text-caption uppercase tracking-[0.16em]">解析 · </span>
                {activeResult.analysis}
              </p>
            ) : null}
          </ExamFocusMode>

          <div className="fixed inset-x-0 bottom-3 z-40 flex justify-center px-3">
            <div className="flex w-full max-w-md items-center gap-2 rounded-pill border border-footer bg-footer p-2 shadow-elevate">
              <ProgressCapsule
                current={activeIndex + 1}
                total={total}
                answered={answeredCount}
                variant="dark"
                className="flex-1"
              />
              <button
                type="button"
                aria-label="打开题号导航"
                onClick={() => setSheetOpen(true)}
                className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-pill text-canvas"
              >
                <List />
              </button>
            </div>
          </div>
        </div>
      </main>

      {sheetOpen
        ? createPortal(
            <MobileSheet
              items={navItems}
              activeId={activeQuestion.id}
              onJump={(id) => {
                const idx = data.findIndex((q) => q.id === id);
                if (idx >= 0) {
                  setActiveIndex(idx);
                }
                setSheetOpen(false);
              }}
              onClose={() => setSheetOpen(false)}
            />,
            document.body,
          )
        : null}
    </div>
  );
}

function MobileSheet({
  items,
  activeId,
  onJump,
  onClose,
}: {
  items: ReturnType<typeof buildQuestionNavItems>;
  activeId: number;
  onJump: (id: number) => void;
  onClose: () => void;
}) {
  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, []);

  return (
    <div
      className="fixed inset-0 z-50 flex items-end bg-ink/40"
      role="dialog"
      aria-modal="true"
      aria-label="题号导航"
      onClick={onClose}
    >
      <div
        className="flex h-[80vh] w-full flex-col gap-4 rounded-t-lg bg-canvas p-5 shadow-elevate"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="flex items-center justify-between border-b border-hairline pb-3">
          <span className="font-display text-display-sm font-semibold text-ink">题号导航</span>
          <Button type="button" variant="ghost" size="sm" onClick={onClose} aria-label="关闭">
            关闭
          </Button>
        </header>
        <div className="flex-1 overflow-y-auto overscroll-contain">
          <ExamNavigator
            items={items}
            activeId={activeId}
            sheetLayout
            desktopLayout={false}
            onJump={(_targetId, id) => onJump(id)}
          />
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: Exit code 0.

- [ ] **Step 3: Smoke-test in dev server**

```bash
cd frontend && npm run dev &
sleep 4
curl -sS http://localhost:5173/practice | head -20
pkill -f vite
```

Expected: HTML shell loads.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/PracticePage.tsx
git commit -m "feat(exam): 重写练习页为 Focus Mode 即时判分 + 题号按对错着色"
```

---

## Task 10: Delete old `components/QuestionNavigator.tsx`

**Files:**
- Delete: `frontend/src/components/QuestionNavigator.tsx`

- [ ] **Step 1: Verify no remaining imports**

```bash
cd frontend && grep -rn "QuestionNavigator" src/ || echo "no remaining imports"
```

Expected: `no remaining imports`. If any page or component still imports `QuestionNavigator` from `@/components/QuestionNavigator`, fix the import to `@/components/exam/ExamNavigator` first and commit that fix separately before deleting.

- [ ] **Step 2: Delete the file**

```bash
cd frontend && rm src/components/QuestionNavigator.tsx
ls src/components/QuestionNavigator.tsx 2>&1 || echo "deleted"
```

Expected: `No such file or directory`.

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: Exit code 0.

- [ ] **Step 4: Commit**

```bash
git add -u frontend/src/components/QuestionNavigator.tsx
git commit -m "refactor(exam): 删除旧 QuestionNavigator，已迁入 ExamNavigator"
```

---

## Task 11: Visual smoke test — all 4 pages

**Files:** none (read-only verification + screenshot)

- [ ] **Step 1: Run lint**

Run: `cd frontend && npm run lint`
Expected: Exit code 0. Zero warnings.

- [ ] **Step 2: Run format check**

Run: `cd frontend && npm run format:check`
Expected: Exit code 0.

- [ ] **Step 3: Run the full test suite**

Run: `cd frontend && npm test`
Expected: All tests pass (designTokens + OptionCard + ProgressCapsule + Timer).

- [ ] **Step 4: Run the full build**

Run: `cd frontend && npm run build`
Expected: `tsc --noEmit` succeeds; Vite emits `dist/`; console shows `built in <X>ms`.

- [ ] **Step 5: Run the dev server and screenshot the 4 pages**

```bash
cd frontend && (npm run dev &) ; sleep 5
```

Open these URLs in a browser (or use a screenshot tool):
- `http://localhost:5173/login` (desktop + mobile 375px)
- `http://localhost:5173/practice` (desktop + mobile 375px) — requires a candidate logged in; pre-seed via `localStorage.setItem('internal-exam-candidate', JSON.stringify({ id: 1, name: 'Test User', ... }))` in the browser console
- `http://localhost:5173/exams/1/taking?attemptId=<id>` — requires a real attempt id from the backend; if unavailable, verify the empty state renders
- `http://localhost:5173/exams/1/result?attemptId=<id>` — same caveat

Checklist per page:
- LoginPage: `CHAPTER 01 · WELCOME` chapter label visible; italic h1 72px (desktop) / 40px (mobile); 姓名 · Name bilingual label; pill submit button
- ExamTakingPage: ProgressCapsule shows `Q 01 / 10`; Timer shows mm:ss; OptionCard 56px+ tall; sticky bottom capsule on mobile; navigator sidebar on desktop
- ExamResultPage: full-black score card with `CHAPTER 99 · RESULT`; 64px score; pill 查看排名 button; answer cards on right with green/red status
- PracticePage: same ExamFocusMode layout; SubmitQuestion button shows in middle; correct/wrong feedback appears after submit

Kill the dev server:

```bash
pkill -f vite
```

- [ ] **Step 6: Note any visual issues for Phase 7 polish**

If anything is off (e.g. spacing, font weight, contrast), record in a follow-up note. Do NOT fix in this phase — Phase 7 handles cross-page polish.

- [ ] **Step 7: Commit (if any incidental fixes were needed)**

```bash
git add frontend/
git commit -m "chore(frontend): Phase 5 视觉烟测兜底修复"
```

Skip if no changes.

---

## Done

Phase 5 is complete when:
- `frontend/src/components/exam/OptionCard.tsx` + `.test.tsx` — pass
- `frontend/src/components/exam/ProgressCapsule.tsx` + `.test.tsx` — pass
- `frontend/src/components/exam/Timer.tsx` + `.test.tsx` — pass (≤5min pulse, aria-live)
- `frontend/src/components/exam/ExamNavigator.tsx` — desktop + sheet layouts
- `frontend/src/components/exam/ExamFocusMode.tsx` — single-question container
- `frontend/src/pages/LoginPage.tsx` — chapter + italic h1 + bilingual labels
- `frontend/src/pages/ExamTakingPage.tsx` — Focus Mode desktop+mobile, keyboard ←/→
- `frontend/src/pages/ExamResultPage.tsx` — black score card + filter toggle
- `frontend/src/pages/PracticePage.tsx` — Focus Mode + SubmitQuestion + per-result colouring
- `frontend/src/components/QuestionNavigator.tsx` — deleted
- `cd frontend && npm test` — all tests pass
- `cd frontend && npm run build` — succeeds
- `cd frontend && npm run lint` — 0 warning
- Snapshot field names unchanged: `stem_snapshot`, `options_snapshot`, `correct_answer_snapshot`, `analysis_snapshot`, `score`, `sort_order`, `selected_answer`
- API calls unchanged: `getAttempt`, `saveAttemptAnswers`, `submitAttempt`, `getAttemptResult`, `getPracticeQuestions`, `submitPracticeAnswer`, `loginCandidate`
- 倒计时逻辑保留: `attempt.started_at + duration_minutes * 60_000`，到 0 自动提交

Downstream phases (Phase 6: P1/P2 pages, Phase 7: polish) can now build on these P0 pages without touching them.
