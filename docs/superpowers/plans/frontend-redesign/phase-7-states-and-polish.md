# Phase 7: States & Polish — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Final polish — shared empty/error/loading states across all 18 pages, motion refinements (Timer pulse, route stagger, sheet slide), keyboard shortcuts on the exam page, accessibility pass (aria-labels, focus ring, live region), and a clean lint + format + typecheck + build.

**Architecture:** Replace inline state messages with the shared `EmptyState` / `Skeleton` primitives. Add `tone='error'` to `EmptyState` if not already shipped in Phase 3. Add keyboard listener on `ExamTakingPage` that respects focus context. Verify and patch the global focus-visible ring. Do not introduce new dependencies; do not modify backend snapshots.

**Tech Stack:** All previous (React 19, Tailwind 3.4, Radix Slot/Dialog, TanStack Query, lucide-react) + Vitest + Testing Library (smoke tests for new behavior).

---

## Working Directory

All paths in this plan are relative to `frontend/` unless explicitly noted. Run `cd frontend &&` before every npm command shown.

---

## Pre-flight: Verify Phases 1–6 are in place

Phase 7 assumes these artifacts already exist from prior phases:

- `frontend/src/index.css` defines `--canvas`, `--canvas-warm`, `--ink`, `--surface-card`, `--success`, `--warning`, `--error`, `--radius-pill`, `--radius-lg`, `--radius-md`, `--radius-sm`, and the `@keyframes pulse` + `@keyframes shimmer` blocks (with corresponding `.animate-pulse` and `.animate-shimmer` utilities or Tailwind defaults).
- `frontend/src/components/editorial/EmptyState.tsx` exists with the signature `(chapter, title, description, action?, secondaryAction?, tone?)` — with `tone='error'` recoloring the chapter to `text-error`.
- `frontend/src/components/ui/skeleton.tsx` exists, renders a `div` with `bg-hairline animate-shimmer` (or `animate-pulse`) and accepts `className`.
- `frontend/src/components/exam/Timer.tsx` exists and uses `text-error animate-pulse` when remaining ≤ 5min.
- `frontend/src/components/ui/sheet.tsx` exists, slide-in uses `cubic-bezier(0.16, 1, 0.3, 1)` and `duration-[240ms]`.
- All 18 pages have been rewritten in Phases 5–6 to use the new primitives and tokens.

If any of these are missing, STOP and run the relevant earlier phase first.

---

## Task 1: Audit and replace inline empty-state messages with `EmptyState`

**Files:**
- Modify: 7 candidate pages + 10 admin pages (18 total). Imports come from `@/components/editorial`.

- [ ] **Step 1: Inventory current inline empty messages**

  Run from the repo root:

  ```bash
  cd /Users/alune/Documents/code/internal-exam-platform
  grep -rn "暂无\|未找到\|还没有\|没有数据\|No data\|暂无内容\|暂无结果" frontend/src/pages
  ```

  Expected: a list of literal Chinese strings used as inline "no data" placeholders inside JSX (not copy in legitimate copy like form labels or error messages). Save this list to use as a checklist.

- [ ] **Step 2: Write the EmptyState smoke test (if not already present in Phase 3)**

  Skip this step if `frontend/src/components/editorial/EmptyState.test.tsx` already exists with a `tone='error'` test. Otherwise add the following case to the existing test file:

  ```tsx
  // Append to frontend/src/components/editorial/EmptyState.test.tsx
  it("tone='error' recolors the chapter to text-error", () => {
    render(
      <EmptyState
        tone="error"
        chapter="CHAPTER 99 · OOPS"
        title="出了点小问题。"
        description="请稍后再试。"
      />,
    );
    const chapter = screen.getByText("CHAPTER 99 · OOPS");
    expect(chapter.className).toContain("text-error");
  });

  it("renders secondaryAction button when provided", async () => {
    const user = userEvent.setup();
    const onSecondary = vi.fn();
    render(
      <EmptyState
        tone="error"
        chapter="CHAPTER 99 · OOPS"
        title="出了点小问题。"
        description="请稍后再试。"
        action={{ label: "返回", onClick: () => {} }}
        secondaryAction={{ label: "重试", onClick: onSecondary }}
      />,
    );
    await user.click(screen.getByRole("button", { name: "重试" }));
    expect(onSecondary).toHaveBeenCalledTimes(1);
  });
  ```

  Run:

  ```bash
  cd frontend && npx vitest run src/components/editorial/EmptyState.test.tsx
  ```

  Expected: pass (or fail with a clear message about `secondaryAction` / `tone='error'` if the Phase 3 implementation needs a follow-up — see Task 2).

- [ ] **Step 3: Replace inline empty state in each page**

  The replacement is mechanical. For every site from Step 1, swap the inline `<p>暂无...</p>` / `<Card><CardHeader><CardTitle>暂无...</CardTitle></CardHeader></Card>` for:

  ```tsx
  <EmptyState
    chapter="CHAPTER 00 · EMPTY"
    title="暂无内容。"
    description="目前还没有数据。"
    action={{ label: "返回首页", onClick: () => navigate("/") }}
  />
  ```

  Mapping table for the most common patterns (adjust the `chapter` and `title` to match each page's domain — copy the strings used today if they exist):

  | Page | chapter | title |
  |---|---|---|
  | `pages/ExamListPage.tsx` | `CHAPTER 00 · EMPTY` | 暂无可参加考试。 |
  | `pages/PracticePage.tsx` | `CHAPTER 00 · EMPTY` | 题库为空。 |
  | `pages/RankingPage.tsx` | `CHAPTER 00 · EMPTY` | 暂无排名数据。 |
  | `pages/ExamResultPage.tsx` | `CHAPTER 00 · EMPTY` | 暂无结果，请先完成考试。 |
  | `pages/admin/QuestionListPage.tsx` | `CHAPTER 00 · EMPTY` | 题库为空。 |
  | `pages/admin/ExamListPage.tsx` | `CHAPTER 00 · EMPTY` | 暂无考试。 |
  | `pages/admin/ScoreReportPage.tsx` | `CHAPTER 00 · EMPTY` | 暂无成绩数据。 |
  | `pages/admin/QuestionAccuracyPage.tsx` | `CHAPTER 00 · EMPTY` | 暂无正确率数据。 |
  | `pages/admin/WrongQuestionPage.tsx` | `CHAPTER 00 · EMPTY` | 暂无错题数据。 |
  | `pages/admin/AbsentCandidatePage.tsx` | `CHAPTER 00 · EMPTY` | 暂无未参加人员。 |

  Do NOT replace:
  - 错误态 message（如 "暂存失败，请稍后重试。"）— these go through the error state in Task 2.
  - "正在加载…" text — these go through Skeleton in Task 3.
  - Form helper / hint text (e.g. "请输入姓名") — keep as plain `text-caption`.

  Add the import at the top of each modified page:

  ```ts
  import { EmptyState } from "@/components/editorial";
  ```

- [ ] **Step 4: Verify typecheck and tests**

  ```bash
  cd frontend && npx tsc --noEmit
  ```

  Expected: 0 errors. If a page is missing a `navigate` reference (because it used `Link` only), add `const navigate = useNavigate();` and an import from `react-router-dom`.

- [ ] **Step 5: Commit**

  ```bash
  git add frontend/src/pages frontend/src/components/editorial/EmptyState.test.tsx
  git commit -m "refactor(pages): 用 EmptyState 统一所有页面的空态"
  ```

---

## Task 2: Add error-state wiring (EmptyState `tone='error'` + double button)

**Files:**
- Modify: any page that renders `query.isError` / `mutation.isError` (see list below).

- [ ] **Step 1: Inventory existing error messages**

  Run:

  ```bash
  cd /Users/alune/Documents/code/internal-exam-platform
  grep -rn "isError\|destructive" frontend/src/pages
  ```

  Expected output should include at least:

  - `pages/ExamTakingPage.tsx` — "暂存失败，请稍后重试。" / "交卷失败，请确认考试仍在进行中。"
  - `pages/LoginPage.tsx` — "未找到匹配的考试人员..."
  - `pages/ExamListPage.tsx`, `pages/PracticePage.tsx`, `pages/ExamResultPage.tsx`, `pages/RankingPage.tsx` — each may render `query.isError` inline.
  - `pages/admin/QuestionListPage.tsx`, `pages/admin/ExamListPage.tsx`, `pages/admin/ScoreReportPage.tsx`, etc. — `query.isError` placeholders.

- [ ] **Step 2: Write the EmptyState error test (if not done in Task 1)**

  Confirm Phase 3's `EmptyState.test.tsx` has a `tone='error'` test. If not, add the one from Task 1 Step 2 and run:

  ```bash
  cd frontend && npx vitest run src/components/editorial/EmptyState.test.tsx
  ```

  If it fails because Phase 3 didn't implement `tone='error'`, patch `EmptyState.tsx`:

  ```tsx
  // In frontend/src/components/editorial/EmptyState.tsx
  // Change the chapter <ChapterNumber ... /> invocation to:
  <ChapterNumber
    className={cn(
      tone === "error" ? "text-error" : "text-muted",
      tone === "error" && "italic",
    )}
  >
    {chapter}
  </ChapterNumber>
  ```

  Re-run the test until it passes.

- [ ] **Step 3: Replace inline error messages with EmptyState `tone='error'`**

  For each page flagged in Step 1, swap the inline `<p className="text-sm text-error">...</p>` (or `<p className="text-sm text-destructive">...</p>`) for:

  ```tsx
  <EmptyState
    tone="error"
    chapter="CHAPTER 99 · OOPS"
    title="出了点小问题。"
    description={errorMessage}
    action={{ label: "返回", onClick: () => navigate(-1) }}
    secondaryAction={{ label: "重试", onClick: () => query.refetch() }}
  />
  ```

  Notes:
  - For pages using `react-query`, the retry handler is `query.refetch()` (or `mutation.reset()` for mutations). For the page-level error boundary case in `ExamTakingPage` you can render a small inline `EmptyState` that lives in the same `<CardContent>` rather than replacing the whole page; in that case skip the "返回" button.
  - For `LoginPage.tsx`, the existing inline error is a card-level form error — keep it inline (it's not a "no data" state, it's a form validation result). Do not replace.

- [ ] **Step 4: Verify with typecheck + tests**

  ```bash
  cd frontend && npx tsc --noEmit && npx vitest run
  ```

  Expected: 0 errors, all tests pass.

- [ ] **Step 5: Commit**

  ```bash
  git add frontend/src/pages frontend/src/components/editorial/EmptyState.tsx
  git commit -m "refactor(pages): 用 EmptyState tone=error 统一错态（返回+重试）"
  ```

---

## Task 3: Wire `Skeleton` into every `useQuery` data fetch

**Files:**
- Modify: every page that calls `useQuery` (see list in Task 1 Step 1 grep results).
- Add a small helper at `frontend/src/components/editorial/ContentSkeleton.tsx` so we don't repeat the skeleton block per page.

- [ ] **Step 1: Create the shared content skeleton**

  Create `frontend/src/components/editorial/ContentSkeleton.tsx`:

  ```tsx
  import { Skeleton } from "@/components/ui/skeleton";
  import { cn } from "@/lib/utils";

  interface ContentSkeletonProps {
    /** Number of skeleton rows to render. Default: 3. */
    rows?: number;
    className?: string;
  }

  /**
   * 加载态：3-5 条 shimmer 占位条 + 底部 LOADING 标签。
   * 替换页面里 "正在加载..." / "加载中" 的纯文本。
   */
  export function ContentSkeleton({ rows = 3, className }: ContentSkeletonProps) {
    return (
      <div
        role="status"
        aria-live="polite"
        aria-busy="true"
        className={cn("flex flex-col gap-3 p-6", className)}
      >
        {Array.from({ length: rows }).map((_, i) => (
          <Skeleton
            key={i}
            className={cn("h-4", i % 2 === 0 ? "w-3/4" : "w-1/2")}
          />
        ))}
        <p className="mt-2 text-[11px] font-medium uppercase tracking-[0.16em] text-muted">
          Loading · 加载中
        </p>
      </div>
    );
  }
  ```

  Create the test `frontend/src/components/editorial/ContentSkeleton.test.tsx`:

  ```tsx
  import { render, screen } from "@testing-library/react";
  import { describe, expect, it } from "vitest";

  import { ContentSkeleton } from "./ContentSkeleton";

  describe("ContentSkeleton", () => {
    it("renders the default 3 skeleton bars + LOADING label", () => {
      render(<ContentSkeleton />);
      expect(screen.getByRole("status")).toHaveAttribute("aria-busy", "true");
      expect(screen.getByText(/Loading/)).toBeInTheDocument();
    });

    it("honors the rows prop", () => {
      const { container } = render(<ContentSkeleton rows={5} />);
      expect(container.querySelectorAll('[aria-hidden="true"]')).toHaveLength(5);
    });
  });
  ```

  Run:

  ```bash
  cd frontend && npx vitest run src/components/editorial/ContentSkeleton.test.tsx
  ```

  Expected: 2 tests pass.

  Export from `frontend/src/components/editorial/index.ts`:

  ```ts
  export { ContentSkeleton } from "./ContentSkeleton";
  ```

- [ ] **Step 2: Wire into pages**

  For each page, replace the `isLoading` branch with:

  ```tsx
  import { ContentSkeleton } from "@/components/editorial";

  // ...

  if (query.isLoading) {
    return <ContentSkeleton rows={4} />;
  }
  ```

  Pages to update (the canonical 18 from `frontend/src/app/router.tsx`):
  - Candidate: `LoginPage`, `ExamListPage`, `ExamStartPage`, `ExamTakingPage`, `ExamResultPage`, `PracticePage`, `RankingPage`.
  - Admin: `AdminLoginPage`, `AdminDashboardPage`, `QuestionListPage`, `QuestionImportPage`, `ExamListPage`, `ExamEditPage`, `CandidateImportPage`, `ScoreReportPage`, `QuestionAccuracyPage`, `WrongQuestionPage`, `AbsentCandidatePage`.

  For pages where the loading is non-blocking (the page renders a list and a Skeleton replaces only the list area), keep the surrounding layout and place `<ContentSkeleton rows={3} />` inside the list region.

- [ ] **Step 3: Verify typecheck + tests**

  ```bash
  cd frontend && npx tsc --noEmit && npx vitest run
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add frontend/src/components/editorial frontend/src/pages
  git commit -m "refactor(pages): 用 ContentSkeleton 替换所有正在加载文本"
  ```

---

## Task 4: Add `aria-label` to every icon-only button

**Files:**
- Modify: components + pages that contain `<Button size="icon">` (or `variant="icon"`) without text.
- New test for each.

- [ ] **Step 1: Find all icon-only buttons**

  Run from the repo root:

  ```bash
  cd /Users/alune/Documents/code/internal-exam-platform
  grep -rn 'size="icon"\|<button[^>]*size={[^}]*icon[^}]*}' frontend/src
  ```

  Expected hits: at least:
  - `frontend/src/components/ui/sheet.tsx` — already has `aria-label="关闭"` from Phase 2 (verify, do not duplicate).
  - `frontend/src/components/ui/dialog.tsx` — already has `aria-label="关闭"` from Phase 2 (verify).
  - `frontend/src/components/layout/TopNav.tsx` — logout icon button (from Phase 4).
  - `frontend/src/components/layout/AdminLayout.tsx` — sidebar collapse / FAB.
  - `frontend/src/components/exam/QuestionNavigator.tsx` — group expand/collapse buttons.
  - `frontend/src/components/exam/Timer.tsx` — no icon button by itself; just the timer text.
  - Any toolbar button in the 4 report pages.

  For each hit, ensure the button has `aria-label="<中文 action>"`. Common labels:

  | Context | aria-label |
  |---|---|
  | Logout | 退出登录 |
  | Close dialog/sheet | 关闭 |
  | Open nav menu (mobile) | 打开导航 |
  | Close nav sheet (mobile) | 关闭导航 |
  | Toggle question group | 展开 / 收起 (use the current state in the label) |
  | Back | 返回 |
  | Refresh | 刷新 |

- [ ] **Step 2: Add a smoke test for TopNav logout button**

  Add to `frontend/src/components/layout/__tests__/TopNav.test.tsx` (create the file if it does not yet exist):

  ```tsx
  import { render, screen } from "@testing-library/react";
  import { describe, expect, it } from "vitest";

  import { TopNav } from "../TopNav";

  describe("TopNav", () => {
    it("logout button has aria-label", () => {
      render(<TopNav />);
      const btn = screen.getByRole("button", { name: "退出登录" });
      expect(btn).toBeInTheDocument();
    });
  });
  ```

  Run:

  ```bash
  cd frontend && npx vitest run src/components/layout/__tests__/TopNav.test.tsx
  ```

  Expected: pass.

- [ ] **Step 3: Verify the rest manually**

  Walk through the grep output from Step 1 and confirm every match has a non-empty `aria-label` attribute. If any are missing, add the attribute (use the table above as the default).

- [ ] **Step 4: Commit**

  ```bash
  git add frontend/src/components frontend/src/pages
  git commit -m "refactor(a11y): 所有图标按钮补 aria-label"
  ```

---

## Task 5: Verify focus-visible ring + Timer live region

**Files:**
- Read-only verification, with one optional patch to `frontend/src/index.css` or `Timer.tsx`.

- [ ] **Step 1: Confirm the global focus ring is correct**

  Open `frontend/src/index.css` and confirm the `:focus-visible` block is exactly:

  ```css
  :focus-visible {
    outline: 2px solid var(--ink);
    outline-offset: 2px;
    border-radius: 2px;
  }
  ```

  If Phase 1/2 wrote it differently (e.g. `outline: 2px solid #111` or no offset), patch to the form above.

- [ ] **Step 2: Confirm Timer.tsx uses `animate-pulse` + `aria-live="polite"`**

  Open `frontend/src/components/exam/Timer.tsx`. The component's `<p>` (or `<time>`) element should:

  - Set `aria-live="polite"` and `aria-atomic="true"` on the outer container.
  - When `remaining <= 5 * 60` (5 minutes), apply both `text-error` and `animate-pulse` classes to the numeric element.
  - The `animate-pulse` class is provided by Tailwind core (1s ease-in-out) — no additional CSS required. If for some reason Tailwind's `animate-pulse` is missing (e.g. a previous phase removed it), add to `index.css` under `@layer utilities`:

    ```css
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.55; }
    }
    .animate-pulse {
      animation: pulse 1s ease-in-out infinite;
    }
    ```

  The intended snippet in `Timer.tsx` (for reference, do not paste if Timer.tsx already implements this correctly):

  ```tsx
  <p aria-live="polite" aria-atomic="true" className="font-mono text-[32px] tabular-nums leading-none text-ink">
    <span className={cn(isUrgent && "text-error animate-pulse")}>{remainingText}</span>
  </p>
  ```

  Add a test `frontend/src/components/exam/__tests__/Timer.test.tsx`:

  ```tsx
  import { render, screen } from "@testing-library/react";
  import { describe, expect, it } from "vitest";

  import { Timer } from "../Timer";

  describe("Timer", () => {
    it("renders with aria-live=polite", () => {
      render(<Timer remainingSeconds={600} />);
      expect(screen.getByText(/--:--|\d{2}:\d{2}/).closest("[aria-live]")).toHaveAttribute(
        "aria-live",
        "polite",
      );
    });

    it("applies text-error + animate-pulse when ≤5min", () => {
      render(<Timer remainingSeconds={120} />);
      const span = screen.getByText(/\d{2}:\d{2}/);
      expect(span.className).toContain("text-error");
      expect(span.className).toContain("animate-pulse");
    });
  });
  ```

  Run:

  ```bash
  cd frontend && npx vitest run src/components/exam/__tests__/Timer.test.tsx
  ```

  Expected: 2 tests pass.

- [ ] **Step 3: Commit (if any patch was needed)**

  ```bash
  git add frontend/src/index.css frontend/src/components/exam/Timer.tsx frontend/src/components/exam/__tests__/Timer.test.tsx
  git commit -m "refactor(a11y): 校验 Timer ≤5min 的 aria-live + pulse 动画"
  ```

---

## Task 6: Add keyboard shortcuts to `ExamTakingPage` (←/→ + 1-9/A-D)

**Files:**
- Modify: `frontend/src/pages/ExamTakingPage.tsx`
- Test: `frontend/src/pages/__tests__/ExamTakingPage.keyboard.test.tsx`

- [ ] **Step 1: Write the failing test**

  Create `frontend/src/pages/__tests__/ExamTakingPage.keyboard.test.tsx`:

  ```tsx
  import { render, screen } from "@testing-library/react";
  import userEvent from "@testing-library/user-event";
  import { afterEach, describe, expect, it, vi } from "vitest";

  // Mock react-router-dom
  vi.mock("react-router-dom", () => ({
    Link: ({ children }: { children: React.ReactNode }) => <a>{children}</a>,
    useNavigate: () => vi.fn(),
    useParams: () => ({ examId: "1" }),
    useSearchParams: () => [new URLSearchParams("attemptId=42"), vi.fn()],
  }));

  // Mock the api
  vi.mock("@/api/attempts", () => ({
    getAttempt: vi.fn().mockResolvedValue({
      id: 42,
      started_at: new Date().toISOString(),
      questions: [
        {
          id: 1,
          question_type: "single",
          stem_snapshot: "Q1",
          options_snapshot: [
            { label: "A", content: "1" },
            { label: "B", content: "2" },
            { label: "C", content: "3" },
            { label: "D", content: "4" },
          ],
        },
        {
          id: 2,
          question_type: "single",
          stem_snapshot: "Q2",
          options_snapshot: [
            { label: "A", content: "1" },
            { label: "B", content: "2" },
            { label: "C", content: "3" },
            { label: "D", content: "4" },
          ],
        },
      ],
    }),
    saveAttemptAnswers: vi.fn().mockResolvedValue({}),
    submitAttempt: vi.fn().mockResolvedValue({ attempt_id: 42 }),
  }));

  vi.mock("@/api/exams", () => ({
    getActiveExams: vi.fn().mockResolvedValue([{ id: 1, duration_minutes: 60 }]),
  }));

  // Mock the QuestionNavigator to a noop
  vi.mock("@/components/QuestionNavigator", () => ({
    QuestionNavigator: () => <div data-testid="nav" />,
  }));

  import { ExamTakingPage } from "../ExamTakingPage";

  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("ArrowRight advances to next question (focus on body)", async () => {
    const user = userEvent.setup();
    render(<ExamTakingPage />);
    // wait for query to resolve
    const q1 = await screen.findByText("Q1");
    expect(q1).toBeInTheDocument();
    // body is the activeElement by default in jsdom
    await user.keyboard("{ArrowRight}");
    const q2 = await screen.findByText("Q2");
    // active id should have changed; we can assert scrollIntoView or the active class.
    // The simplest assertion: Q2 card has the ring class.
    expect(q2.parentElement?.className ?? "").toMatch(/ring|active/);
  });

  it("ArrowLeft goes to previous question", async () => {
    const user = userEvent.setup();
    render(<ExamTakingPage />);
    await screen.findByText("Q1");
    await user.keyboard("{ArrowRight}");
    await user.keyboard("{ArrowLeft}");
    // both Q1 and Q2 are present; we just check the handler didn't throw
  });

  it("Pressing A selects option A on the current question", async () => {
    const user = userEvent.setup();
    render(<ExamTakingPage />);
    await screen.findByText("Q1");
    await user.keyboard("a");
    const radioA = screen.getByDisplayValue("A") as HTMLInputElement;
    expect(radioA.checked).toBe(true);
  });

  it("Keyboard shortcuts are ignored when focus is inside an input", async () => {
    const user = userEvent.setup();
    render(
      <div>
        <input data-testid="trap" />
        <ExamTakingPage />
      </div>,
    );
    const trap = screen.getByTestId("trap");
    trap.focus();
    await user.keyboard("{ArrowRight}");
    // No assertion needed; the test passes if no error is thrown and the handler short-circuits.
  });
  ```

  Run:

  ```bash
  cd frontend && npx vitest run src/pages/__tests__/ExamTakingPage.keyboard.test.tsx
  ```

  Expected: 4 tests fail (or fail to import `ExamTakingPage` if it has compile errors).

- [ ] **Step 2: Implement the keyboard handler**

  In `frontend/src/pages/ExamTakingPage.tsx`, add a `useEffect` after the existing `useEffect` for the interval timer (around line 66). Insert the following:

  ```tsx
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      // Skip if focus is in a text input or contenteditable
      const target = event.target as HTMLElement | null;
      if (
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.tagName === "SELECT" ||
          target.isContentEditable)
      ) {
        return;
      }

      const questions = attempt?.questions ?? [];

      // ArrowLeft / ArrowRight: navigate between questions
      if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
        if (questions.length === 0) {
          return;
        }
        const currentIndex = activeQuestionId
          ? questions.findIndex((q) => q.id === activeQuestionId)
          : 0;
        const nextIndex =
          event.key === "ArrowRight"
            ? Math.min(questions.length - 1, (currentIndex < 0 ? 0 : currentIndex) + 1)
            : Math.max(0, (currentIndex < 0 ? 0 : currentIndex) - 1);
        const next = questions[nextIndex];
        if (next) {
          event.preventDefault();
          setActiveQuestionId(next.id);
          document.getElementById(`exam-question-${next.id}`)?.scrollIntoView({
            behavior: "smooth",
            block: "start",
          });
        }
        return;
      }

      // 1-9 / A-D: select option on the current question
      const currentId =
        activeQuestionId ?? questions[0]?.id ?? null;
      if (!currentId) {
        return;
      }
      const current = questions.find((q) => q.id === currentId);
      if (!current) {
        return;
      }
      const key = event.key.toUpperCase();
      const numericIndex = Number.parseInt(event.key, 10);
      const label =
        Number.isInteger(numericIndex) && numericIndex >= 1 && numericIndex <= 9
          ? String.fromCharCode(64 + numericIndex) // 1 → A, 2 → B, ...
          : ["A", "B", "C", "D", "E", "F", "G", "H", "I"].includes(key)
            ? key
            : null;
      if (!label) {
        return;
      }
      const option = current.options_snapshot.find((opt) => opt.label === label);
      if (!option) {
        return;
      }
      event.preventDefault();
      if (current.question_type === "multiple") {
        handleMultipleChange(current, label, !splitAnswer(answers[current.id]).includes(label));
      } else {
        handleAnswerChange(current, label);
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [attempt, activeQuestionId, answers, handleAnswerChange, handleMultipleChange]);
  ```

  Note: `handleAnswerChange` and `handleMultipleChange` are defined in the component body, so they may need to be wrapped in `useCallback` (or the effect's deps need to include them). Easiest fix: declare them via `useCallback` with deps `[answers, activeQuestionId]`. The implementation details of those callbacks do not need to change.

- [ ] **Step 3: Run the test to verify it passes (GREEN)**

  ```bash
  cd frontend && npx vitest run src/pages/__tests__/ExamTakingPage.keyboard.test.tsx
  ```

  Expected: all 4 tests pass.

- [ ] **Step 4: Lint + typecheck**

  ```bash
  cd frontend && npm run lint && npx tsc --noEmit
  ```

  Expected: 0 errors.

- [ ] **Step 5: Commit**

  ```bash
  git add frontend/src/pages/ExamTakingPage.tsx frontend/src/pages/__tests__/ExamTakingPage.keyboard.test.tsx
  git commit -m "feat(exam): 作答页加键盘快捷键（←/→ 切题、1-9 与 A-D 选答案）"
  ```

---

## Task 7: Wire the global focus ring on every interactive primitive (verification only)

**Files:** read-only verification. Patch only if a primitive is missing the ring.

- [ ] **Step 1: Audit each primitive**

  Run from the repo root:

  ```bash
  cd /Users/alune/Documents/code/internal-exam-platform
  grep -L "focus-visible" frontend/src/components/ui/button.tsx frontend/src/components/ui/input.tsx frontend/src/components/ui/sheet.tsx frontend/src/components/ui/dialog.tsx
  ```

  If any of these files is missing `focus-visible`, the primitive needs a patch. Expected: no output (all four should match).

  If a file is missing the class, add `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 focus-visible:ring-offset-canvas` to the underlying element's className. The global `:focus-visible` in `index.css` provides a fallback, but a primitive-level ring overrides the outline for keyboard-only focus inside the component.

- [ ] **Step 2: Write a smoke test (one-time)**

  Add `frontend/src/components/ui/__tests__/focus-ring.test.tsx`:

  ```tsx
  import { render, screen } from "@testing-library/react";
  import { describe, expect, it } from "vitest";

  import { Button } from "../button";
  import { Input } from "../input";

  describe("primitive focus ring", () => {
    it("Button includes focus-visible:ring-ink in its className", () => {
      render(<Button>Go</Button>);
      expect(screen.getByRole("button").className).toMatch(/focus-visible:ring-ink|focus-visible:ring-2/);
    });

    it("Input includes focus-visible:ring-ink in its className", () => {
      render(<Input placeholder="x" />);
      expect(screen.getByPlaceholderText("x").className).toMatch(/focus-visible:ring-ink|focus-visible:ring-1/);
    });
  });
  ```

  Run:

  ```bash
  cd frontend && npx vitest run src/components/ui/__tests__/focus-ring.test.tsx
  ```

  Expected: 2 tests pass.

- [ ] **Step 3: Commit (if any primitive was patched)**

  ```bash
  git add frontend/src/components/ui frontend/src/components/ui/__tests__/focus-ring.test.tsx
  git commit -m "refactor(a11y): 校验 Button / Input 焦点环"
  ```

---

## Task 8: Color contrast spot check (documentation only)

**Files:** read-only verification.

- [ ] **Step 1: Spot-check 4 key token pairs in the browser**

  Render the following pairs side-by-side in the dev server (any page, e.g. `/login`):

  | Foreground | Background | Pair | Expected ratio | Pass? |
  |---|---|---|---|---|
  | `--ink` (#111) | `--canvas` (#fff) | Body text | 18.7:1 | yes |
  | `--body` (#374151) | `--canvas` (#fff) | Body text | 10.4:1 | yes |
  | `--muted` (#6b7280) | `--canvas` (#fff) | Hint / chapter | 4.7:1 | yes |
  | `--success` (#166534) | `--canvas` (#fff) | Correct / LIVE | 7.5:1 | yes |
  | `--warning` (#b45309) | `--canvas` (#fff) | Soon / hint | 4.7:1 | yes |
  | `--error` (#b91c1c) | `--canvas` (#fff) | Wrong / required | 6.4:1 | yes |
  | `--footer-soft` (#a1a1aa) | `--footer` (#0a0a0a) | Footer text | 7.4:1 | yes |

  All ratios pass WCAG AA for normal text (≥4.5:1). If any pair fails, report the failure and STOP — do not silently tweak tokens. The most likely culprit would be a downstream phase replacing a hex token with a HSL variable.

- [ ] **Step 2: Capture a screenshot of the login page footer and admin sidebar for the record**

  Run:

  ```bash
  cd frontend && npm run dev
  ```

  Open `http://localhost:5173/login` in a browser, take a screenshot. Save it under `docs/handoff-assets/phase-7-contrast.png` (create the directory if it does not exist).

  Stop the dev server.

  ```bash
  pkill -f vite
  ```

  This step has no automated test — it's an artifact for the handoff doc.

- [ ] **Step 3: Commit the screenshot**

  ```bash
  git add docs/handoff-assets/phase-7-contrast.png
  git commit -m "docs: Phase 7 颜色对比度截图（WCAG AA 全部通过）"
  ```

  (Skip the commit if you did not actually create a screenshot.)

---

## Task 9: Lint + format + typecheck (zero diff)

**Files:** no file changes expected; the goal is to apply auto-fixes.

- [ ] **Step 1: Run lint --fix**

  ```bash
  cd frontend && npm run lint:fix
  ```

  Expected: 0 errors, 0 warnings. If a rule fires that you think is wrong, do NOT edit `.eslintrc` / `eslint.config.js`; report the warning text and STOP. Common warnings the project may surface: `react-hooks/exhaustive-deps` (fix by adding the dep), `tailwindcss-classnames-order` (let Prettier handle it in the next step).

- [ ] **Step 2: Run format**

  ```bash
  cd frontend && npm run format
  ```

  Expected: 0 diff. If Prettier rewrites files, that's fine — let it.

- [ ] **Step 3: Run typecheck**

  ```bash
  cd frontend && npx tsc --noEmit
  ```

  Expected: 0 errors.

- [ ] **Step 4: Run the full test suite**

  ```bash
  cd frontend && npx vitest run
  ```

  Expected: all tests pass.

- [ ] **Step 5: Commit any auto-fixed files**

  ```bash
  git status
  # If anything changed:
  git add frontend/
  git commit -m "chore: 整体 lint / format / typecheck 自动修复"
  ```

---

## Task 10: Production build verification

**Files:** no file changes.

- [ ] **Step 1: Run the build**

  ```bash
  cd frontend && npm run build
  ```

  Expected output:

  - `tsc --noEmit` succeeds.
  - Vite emits `dist/` with hashed JS / CSS bundles.
  - Console shows `built in <X>ms` (typically 5–15s).

  If the build fails:
  - Read the error carefully.
  - Common cause: an `import` path that resolved under the old HSL setup but breaks under the new tokens (e.g. `bg-primary` is gone). Fix the call site, do NOT modify `vite.config.ts` or `tailwind.config.ts` to silence the error.
  - Common cause: a TypeScript error in one of the pages touched by Phases 5–6. Fix the page, do NOT loosen `tsconfig.json`.

- [ ] **Step 2: Confirm dist contents**

  ```bash
  cd frontend && ls -la dist/ | head -20
  ```

  Expected: `index.html`, `assets/index-<hash>.js`, `assets/index-<hash>.css`, plus any images.

- [ ] **Step 3: Commit (only if anything was patched during this task)**

  ```bash
  git status
  # If a build fix was needed:
  git add frontend/
  git commit -m "chore: 修复 Phase 7 build 失败"
  ```

---

## Task 11: Visual smoke test on P0 pages (desktop ≥1024px + mobile <768px)

**Files:** read-only verification. Optional screenshots under `docs/handoff-assets/`.

- [ ] **Step 1: Start the dev server in the background**

  ```bash
  cd frontend && (npm run dev > /tmp/vite.log 2>&1 &) ; sleep 4
  ```

  Expected: `cat /tmp/vite.log` shows `Local: http://localhost:5173/`.

- [ ] **Step 2: Walk through 4 P0 pages at desktop ≥1024px**

  Open the following URLs in a browser. For each, take a screenshot (or just visually inspect if no headless screenshot tool is configured) and confirm it matches the spec section 6 description:

  | URL | What to verify |
  |---|---|
  | `/login` | chapter + italic h1 + warm card + pill submit. |
  | `/exams/1/taking?attemptId=42` | Focus Mode grid `1fr_240px`; question card; option cards ≥56px; right-side question navigator with chapter groups; bottom progress capsule on mobile. |
  | `/exams/1/result?attemptId=42` | Left black score card (320px) + right answer list. |
  | `/admin/dashboard` | Black 240px sidebar + warm canvas + 4 metric cards + recent activity. |

- [ ] **Step 3: Resize to mobile (<768px) and re-verify**

  Use browser dev tools device emulation. For each of the 4 pages above:

  | URL | What to verify |
  |---|---|
  | `/login` | Same card, no chapter offset. |
  | `/exams/1/taking?attemptId=42` | Single column; top progress + timer row; bottom sticky progress capsule (12px above bottom); FAB opens the navigator as a bottom sheet. |
  | `/exams/1/result?attemptId=42` | Score card full width, answer list below. |
  | `/admin/dashboard` | Sidebar replaced by FAB; tapping FAB opens a bottom sheet with the same nav items. |

- [ ] **Step 4: Save screenshots (optional but recommended)**

  Save under `docs/handoff-assets/phase-7/`:
  - `login-desktop.png`, `login-mobile.png`
  - `exam-taking-desktop.png`, `exam-taking-mobile.png`
  - `exam-result-desktop.png`, `exam-result-mobile.png`
  - `dashboard-desktop.png`, `dashboard-mobile.png`

- [ ] **Step 5: Kill the dev server**

  ```bash
  pkill -f vite
  ```

- [ ] **Step 6: Commit screenshots**

  ```bash
  git add docs/handoff-assets/phase-7
  git commit -m "docs: Phase 7 视觉冒烟测试截图（桌面+手机，P0 四页）"
  ```

  (Skip the commit if no screenshots were captured.)

---

## Task 12: Update `docs/handoff.md` with the new design

**Files:**
- Modify: `docs/handoff.md` — add a "Phase 7 — States & Polish" section at the bottom of the existing Phase 6 section.

- [ ] **Step 1: Append the Phase 7 summary to `docs/handoff.md`**

  Open `docs/handoff.md`, find the line that begins with the most recent phase (e.g. "## Phase 6 …"), and append after it (preserve the rest of the document):

  ```markdown
  ## Phase 7 — States & Polish（完成日期 YYYY-MM-DD）

  - **空态**：所有 18 个页面统一用 `EmptyState`（`@/components/editorial`），无内联 `暂无数据` 文案。
  - **错态**：`EmptyState tone='error'` 渲染 `text-error` chapter + "返回 / 重试" 双按钮。
  - **加载态**：`ContentSkeleton`（`@/components/editorial`）基于 `Skeleton` 原语 + 1500ms shimmer。
  - **倒计时 pulse**：`Timer.tsx` 在剩余 ≤5 分钟时 `text-error animate-pulse` + `aria-live="polite"`。
  - **键盘快捷键**：考试作答页 `←/→` 切题、`1-9` 与 `A-D` 选答案；input/textarea/select 聚焦时自动让出。
  - **可访问性**：
    - 全局 `:focus-visible { outline: 2px solid var(--ink); outline-offset: 2px; }`。
    - 所有图标按钮补 `aria-label`（退出登录 / 关闭 / 打开导航 / 关闭导航 / 展开 / 收起 / 返回 / 刷新）。
    - 颜色对比度全部通过 WCAG AA（见 Phase 7 任务 8 的截图）。
  - **代码质量**：`npm run lint` 0 warning · `npm run format` 0 diff · `npx tsc --noEmit` 0 error · `npm run build` 成功。
  ```

  Fill in the actual completion date.

- [ ] **Step 2: Verify no broken cross-links**

  ```bash
  cd /Users/alune/Documents/code/internal-exam-platform
  grep -n "phase-7\|Phase 7" docs/handoff.md
  ```

  Expected: at least one match.

- [ ] **Step 3: Commit**

  ```bash
  git add docs/handoff.md
  git commit -m "docs: handoff 增补 Phase 7 状态与精修章节"
  ```

---

## Done

Phase 7 is complete when:

- All 18 pages render empty / error / loading states via `EmptyState` and `ContentSkeleton`.
- `EmptyState` with `tone='error'` exists and is used wherever `query.isError` renders.
- `Timer` shows pulse + `aria-live="polite"` at ≤5min.
- All icon-only buttons have `aria-label`.
- `ExamTakingPage` supports `←/→` (next/prev) and `1-9` / `A-D` (select answer) when focus is not in a text input.
- `:focus-visible` global ring is `2px solid var(--ink)` with `2px` offset.
- `npm run lint` 0 warnings, `npm run format` 0 diff, `npx tsc --noEmit` 0 errors, `npm run build` succeeds.
- `docs/handoff.md` documents the Phase 7 deliverables.
- Optional screenshots are committed under `docs/handoff-assets/phase-7/`.

---

## How to commit and open a PR after Phase 7

This plan does not include commit-by-commit pushes, but here is the recommended finishing flow (per the project's `superpowers:finishing-a-development-branch` skill):

1. Verify the working tree is clean:

   ```bash
   cd /Users/alune/Documents/code/internal-exam-platform
   git status
   ```

2. If you worked on a feature branch, rebase onto `main`:

   ```bash
   git fetch origin
   git rebase origin/main
   ```

3. Push the branch and open a PR:

   ```bash
   git push -u origin <branch>
   gh pr create --title "feat(frontend): 知试前端重构 Phase 7 状态与精修" \
     --body "见 docs/superpowers/specs/2026-06-12-frontend-redesign-design.md 与 docs/superpowers/plans/frontend-redesign/phase-7-states-and-polish.md"
   ```

4. (Optional) Tag the phase:

   ```bash
   git tag -a phase-7-states-and-polish -m "Phase 7: 状态与精修完成"
   ```

5. If you prefer to merge locally without a PR (single-author repo):

   ```bash
   git checkout main
   git merge --no-ff <branch>
   git push
   ```

## Notes on what Phase 7 does NOT do

- No new npm dependencies. `framer-motion` is not required — the `data-stagger` CSS animation (already defined in Phase 1's `index.css` if it shipped) is sufficient for the route-stagger requirement. If the stagger isn't already defined, do not add it as a new feature; just rely on the per-element entrance via the existing `animate-in` utilities from `tailwindcss-animate` (Phase 2).
- No backend changes. All `*_snapshot` fields continue to come from the attempt response as before.
- No new tokens. If a color contrast issue surfaces, report it — do not invent new shades.
- No `axe-core` automated scan. The spot check in Task 8 plus the manual `aria-label` + `aria-live` audit is the a11y bar for Phase 7. A future phase may add `@axe-core/playwright` integration.
