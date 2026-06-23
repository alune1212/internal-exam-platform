# Frontend Page Consistency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build shared page structure primitives and migrate candidate/admin pages so both sides follow one Academic Editorial page skeleton while keeping their different navigation models.

**Architecture:** Add focused primitives under `frontend/src/components/page/` for shell, header, section, actions, and page states. Keep `CandidateLayout` top navigation and `AdminLayout` side rail unchanged; migrate pages to compose the new primitives around existing business components, API hooks, and editorial primitives.

**Tech Stack:** React, TypeScript, Vite, Tailwind CSS aliases from `frontend/src/index.css`, Vitest, Testing Library, React Router, TanStack Query, local shadcn-compatible UI primitives, existing `frontend/src/components/editorial/*`.

---

## Source Design

Implementation follows:

- `docs/superpowers/specs/2026-06-23-frontend-page-consistency-design.md`
- `frontend/DESIGN.md`
- `AGENTS.md`

Hard boundaries:

- Do not change backend APIs or request/response shapes.
- Do not change auth, exam scoring, import, autosave, report, or result behavior.
- Do not replace candidate top navigation with admin side rail.
- Do not replace admin side rail with candidate top navigation.
- Do not replace the Academic Editorial token system.
- Do not migrate exam/practice focus mode aggressively; preserve fixed desktop question navigation and mobile sheet navigation.

## File Structure

Create:

- `frontend/src/components/page/PageShell.tsx`: outer rhythm and density variants.
- `frontend/src/components/page/PageHeader.tsx`: shared page eyebrow, H1, description, and actions.
- `frontend/src/components/page/PageSection.tsx`: shared content surface variants.
- `frontend/src/components/page/PageActions.tsx`: responsive action row.
- `frontend/src/components/page/PageState.tsx`: wrapper around `EmptyState` and `ContentSkeleton`.
- `frontend/src/components/page/index.ts`: exports.
- `frontend/src/components/page/__tests__/PageShell.test.tsx`
- `frontend/src/components/page/__tests__/PageHeader.test.tsx`
- `frontend/src/components/page/__tests__/PageSection.test.tsx`
- `frontend/src/components/page/__tests__/PageActions.test.tsx`
- `frontend/src/components/page/__tests__/PageState.test.tsx`

Modify:

- `frontend/src/components/admin/ReportPage.tsx`: compose `PageShell`, `PageHeader`, and `PageSection`.
- `frontend/src/components/admin/__tests__/ReportPage.test.tsx`: assert wrapper still renders reports correctly.
- `frontend/src/pages/LoginPage.tsx`: candidate auth canvas uses shared header/section.
- `frontend/src/pages/ExamListPage.tsx`: candidate ordinary page uses shared shell/header/state.
- `frontend/src/pages/ExamStartPage.tsx`: candidate exam rules page uses shared shell/header/section/state.
- `frontend/src/pages/ExamResultPage.tsx`: result page uses shared shell/header/state where it does not weaken the score hero.
- `frontend/src/pages/PracticePage.tsx`: focus page uses shared shell/state only at safe boundaries.
- `frontend/src/pages/ExamTakingPage.tsx`: focus page uses shared shell/state only at safe boundaries.
- `frontend/src/pages/admin/AdminLoginPage.tsx`: admin auth canvas uses shared header/section.
- `frontend/src/pages/admin/AdminDashboardPage.tsx`: dashboard uses shared shell/header/section/state.
- `frontend/src/pages/admin/ExamEditPage.tsx`: edit page uses shared shell/header/section.
- `frontend/src/pages/admin/ExamCandidatesPage.tsx`: scoped candidate page uses shared shell/header/section.
- `frontend/src/pages/admin/QuestionImportPage.tsx`: import page uses shared shell/header/section.
- `frontend/src/pages/admin/CandidateImportPage.tsx`: candidate import page uses shared shell/header/section.
- Existing page tests under `frontend/src/pages/**/*.test.tsx`: add assertions that shared page structures render while behavior remains intact.
- `frontend/DESIGN.md`: document shared page primitives and migration rules.

Do not modify:

- `frontend/src/components/layout/TopNav.tsx`
- `frontend/src/components/layout/AdminSideRail.tsx`
- `frontend/src/components/layout/CandidateLayout.tsx`
- `frontend/src/components/layout/AdminLayout.tsx`

These layout files stay stable unless a test proves the new shared page primitives require a narrow integration adjustment.

## Task 1: Create Shared Page Primitives

**Files:**

- Create: `frontend/src/components/page/PageShell.tsx`
- Create: `frontend/src/components/page/PageHeader.tsx`
- Create: `frontend/src/components/page/PageSection.tsx`
- Create: `frontend/src/components/page/PageActions.tsx`
- Create: `frontend/src/components/page/PageState.tsx`
- Create: `frontend/src/components/page/index.ts`
- Test: `frontend/src/components/page/__tests__/PageShell.test.tsx`
- Test: `frontend/src/components/page/__tests__/PageHeader.test.tsx`
- Test: `frontend/src/components/page/__tests__/PageSection.test.tsx`
- Test: `frontend/src/components/page/__tests__/PageActions.test.tsx`
- Test: `frontend/src/components/page/__tests__/PageState.test.tsx`

- [ ] **Step 1: Write failing tests for `PageShell`**

Create `frontend/src/components/page/__tests__/PageShell.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PageShell } from "../PageShell";

describe("PageShell", () => {
  it("renders children with calm page rhythm by default", () => {
    render(<PageShell>内容</PageShell>);

    const shell = screen.getByText("内容");
    expect(shell).toHaveClass("flex", "flex-col", "gap-8");
  });

  it("supports workbench density for admin pages", () => {
    render(<PageShell density="workbench">管理页</PageShell>);

    expect(screen.getByText("管理页")).toHaveClass("gap-6");
  });

  it("supports focus density for exam and practice pages", () => {
    render(<PageShell density="focus">作答页</PageShell>);

    expect(screen.getByText("作答页")).toHaveClass("gap-6");
  });

  it("can opt into stagger entrance", () => {
    render(<PageShell stagger>动效页</PageShell>);

    expect(screen.getByText("动效页")).toHaveAttribute("data-stagger");
  });
});
```

- [ ] **Step 2: Write failing tests for `PageHeader`**

Create `frontend/src/components/page/__tests__/PageHeader.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Button } from "@/components/ui/button";

import { PageHeader } from "../PageHeader";

describe("PageHeader", () => {
  it("renders the shared eyebrow, title, and description", () => {
    render(
      <PageHeader
        eyebrow="EXAMS · 考试"
        title="可参加考试"
        description="选择一场考试，开始前请确认考试规则。"
      />,
    );

    expect(screen.getByText("EXAMS · 考试")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "可参加考试" })).toHaveClass(
      "font-display",
      "text-display-lg",
      "font-semibold",
      "text-ink",
    );
    expect(screen.getByText("选择一场考试，开始前请确认考试规则。")).toHaveClass("text-body-lg");
  });

  it("places actions in a responsive action region", () => {
    render(
      <PageHeader
        eyebrow="LIBRARY · 题库"
        title="题库管理"
        actions={<Button type="button">新增题目</Button>}
      />,
    );

    expect(screen.getByRole("button", { name: "新增题目" })).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Write failing tests for `PageSection`**

Create `frontend/src/components/page/__tests__/PageSection.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PageSection } from "../PageSection";

describe("PageSection", () => {
  it("renders a plain section without framed card styling", () => {
    render(<PageSection variant="plain">普通区块</PageSection>);

    const section = screen.getByText("普通区块");
    expect(section).toHaveClass("flex", "flex-col");
    expect(section).not.toHaveClass("shadow-card");
  });

  it("renders a card section for display content", () => {
    render(<PageSection variant="card">展示卡片</PageSection>);

    expect(screen.getByText("展示卡片")).toHaveClass(
      "rounded-lg",
      "border",
      "border-hairline",
      "bg-canvas",
      "shadow-card",
    );
  });

  it("renders a panel section for dense forms", () => {
    render(<PageSection variant="panel">表单面板</PageSection>);

    expect(screen.getByText("表单面板")).toHaveClass("rounded-md", "bg-surface-card");
  });

  it("renders a table section for admin data tables", () => {
    render(<PageSection variant="table">表格区块</PageSection>);

    expect(screen.getByText("表格区块")).toHaveClass("overflow-hidden", "rounded-lg");
  });
});
```

- [ ] **Step 4: Write failing tests for `PageActions`**

Create `frontend/src/components/page/__tests__/PageActions.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Button } from "@/components/ui/button";

import { PageActions } from "../PageActions";

describe("PageActions", () => {
  it("wraps actions without forcing one-line overflow", () => {
    render(
      <PageActions>
        <Button type="button">主要操作</Button>
        <Button type="button" variant="outline">
          次要操作
        </Button>
      </PageActions>,
    );

    const group = screen.getByRole("group", { name: "页面操作" });
    expect(group).toHaveClass("flex", "flex-wrap", "gap-2");
    expect(screen.getByRole("button", { name: "主要操作" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "次要操作" })).toBeInTheDocument();
  });
});
```

- [ ] **Step 5: Write failing tests for `PageState`**

Create `frontend/src/components/page/__tests__/PageState.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PageState } from "../PageState";

describe("PageState", () => {
  it("renders loading through ContentSkeleton", () => {
    render(<PageState state="loading" />);

    expect(screen.getByRole("status")).toHaveAttribute("aria-busy", "true");
  });

  it("renders empty state through EmptyState", () => {
    render(
      <PageState
        state="empty"
        eyebrow="STATE · 空状态"
        title="暂无内容"
        description="这里还没有可显示的数据。"
      />,
    );

    expect(screen.getByText("STATE · 空状态")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "暂无内容" })).toBeInTheDocument();
    expect(screen.getByText("这里还没有可显示的数据。")).toBeInTheDocument();
  });

  it("renders error state with error tone", () => {
    render(
      <PageState
        state="error"
        eyebrow="STATE · 异常状态"
        title="加载失败"
        description="请稍后重试。"
      />,
    );

    expect(screen.getByText("STATE · 异常状态")).toHaveClass("text-error");
  });

  it("passes primary and secondary actions through", async () => {
    const action = vi.fn();
    const secondaryAction = vi.fn();

    render(
      <PageState
        state="empty"
        eyebrow="STATE · 空状态"
        title="暂无内容"
        description="这里还没有可显示的数据。"
        action={{ label: "刷新", onClick: action }}
        secondaryAction={{ label: "返回", onClick: secondaryAction }}
      />,
    );

    screen.getByRole("button", { name: "刷新" }).click();
    screen.getByRole("button", { name: "返回" }).click();

    expect(action).toHaveBeenCalledTimes(1);
    expect(secondaryAction).toHaveBeenCalledTimes(1);
  });
});
```

- [ ] **Step 6: Run primitive tests to verify they fail**

Run:

```bash
cd frontend
npm test -- src/components/page
```

Expected: FAIL because `PageShell`, `PageHeader`, `PageSection`, `PageActions`, and `PageState` do not exist yet.

- [ ] **Step 7: Implement `PageShell`**

Create `frontend/src/components/page/PageShell.tsx`:

```tsx
import * as React from "react";

import { cn } from "@/lib/utils";

export type PageShellDensity = "calm" | "workbench" | "focus";
export type PageShellWidth = "default" | "wide" | "full";

export interface PageShellProps extends React.HTMLAttributes<HTMLDivElement> {
  density?: PageShellDensity;
  width?: PageShellWidth;
  stagger?: boolean;
}

const densityClassName: Record<PageShellDensity, string> = {
  calm: "gap-8",
  workbench: "gap-6",
  focus: "gap-6",
};

const widthClassName: Record<PageShellWidth, string> = {
  default: "mx-auto w-full max-w-6xl",
  wide: "mx-auto w-full max-w-7xl",
  full: "w-full",
};

export function PageShell({
  density = "calm",
  width = "default",
  stagger = false,
  className,
  children,
  ...props
}: PageShellProps) {
  return (
    <div
      data-stagger={stagger ? "" : undefined}
      className={cn("flex flex-col", densityClassName[density], widthClassName[width], className)}
      {...props}
    >
      {children}
    </div>
  );
}
```

- [ ] **Step 8: Implement `PageActions`**

Create `frontend/src/components/page/PageActions.tsx`:

```tsx
import * as React from "react";

import { cn } from "@/lib/utils";

export interface PageActionsProps extends React.HTMLAttributes<HTMLDivElement> {
  "aria-label"?: string;
}

export function PageActions({
  className,
  children,
  "aria-label": ariaLabel = "页面操作",
  ...props
}: PageActionsProps) {
  if (!children) {
    return null;
  }

  return (
    <div
      role="group"
      aria-label={ariaLabel}
      className={cn("flex flex-wrap items-center gap-2", className)}
      {...props}
    >
      {children}
    </div>
  );
}
```

- [ ] **Step 9: Implement `PageHeader`**

Create `frontend/src/components/page/PageHeader.tsx`:

```tsx
import * as React from "react";

import { ChapterNumber } from "@/components/editorial/ChapterNumber";
import { cn } from "@/lib/utils";

import { PageActions } from "./PageActions";

export interface PageHeaderProps extends React.HTMLAttributes<HTMLElement> {
  eyebrow: string;
  title: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  className,
  children,
  ...props
}: PageHeaderProps) {
  return (
    <header
      className={cn("flex flex-col gap-4 md:flex-row md:items-end md:justify-between", className)}
      {...props}
    >
      <div className="flex min-w-0 flex-col gap-3">
        <ChapterNumber>{eyebrow}</ChapterNumber>
        <h1 className="font-display text-display-lg font-semibold text-ink lg:text-display-xl">
          {title}
        </h1>
        {description ? <p className="max-w-3xl text-body-lg text-body">{description}</p> : null}
        {children}
      </div>
      {actions ? <PageActions className="md:justify-end">{actions}</PageActions> : null}
    </header>
  );
}
```

- [ ] **Step 10: Implement `PageSection`**

Create `frontend/src/components/page/PageSection.tsx`:

```tsx
import * as React from "react";

import { cn } from "@/lib/utils";

export type PageSectionVariant = "plain" | "card" | "panel" | "table";

export interface PageSectionProps extends React.HTMLAttributes<HTMLElement> {
  variant?: PageSectionVariant;
}

const variantClassName: Record<PageSectionVariant, string> = {
  plain: "flex flex-col gap-4",
  card: "flex flex-col gap-5 rounded-lg border border-hairline bg-canvas p-6 shadow-card lg:p-7",
  panel: "flex flex-col gap-5 rounded-md border border-hairline bg-surface-card p-5 lg:p-6",
  table: "overflow-hidden rounded-lg border border-hairline bg-canvas shadow-card",
};

export function PageSection({
  variant = "plain",
  className,
  children,
  ...props
}: PageSectionProps) {
  return (
    <section className={cn(variantClassName[variant], className)} {...props}>
      {children}
    </section>
  );
}
```

- [ ] **Step 11: Implement `PageState`**

Create `frontend/src/components/page/PageState.tsx`:

```tsx
import * as React from "react";

import {
  EmptyState,
  type EmptyStateAction,
  type EmptyStateTone,
} from "@/components/editorial/EmptyState";
import { ContentSkeleton } from "@/components/editorial/ContentSkeleton";
import { cn } from "@/lib/utils";

export type PageStateKind =
  | "loading"
  | "empty"
  | "error"
  | "notLoggedIn"
  | "notStarted"
  | "submitted";

export interface PageStateProps extends React.HTMLAttributes<HTMLDivElement> {
  state: PageStateKind;
  eyebrow?: string;
  title?: string;
  description?: string;
  action?: EmptyStateAction;
  secondaryAction?: EmptyStateAction;
  rows?: number;
  skeletonVariant?: "default" | "page" | "table" | "card";
  showLoadingCaption?: boolean;
}

const stateTone: Record<PageStateKind, EmptyStateTone> = {
  loading: "default",
  empty: "default",
  error: "error",
  notLoggedIn: "muted",
  notStarted: "muted",
  submitted: "default",
};

export function PageState({
  state,
  eyebrow = state === "error" ? "STATE · 异常状态" : "STATE · 空状态",
  title = state === "error" ? "加载失败" : "暂无内容",
  description = state === "error" ? "请稍后重试。" : "这里还没有可显示的数据。",
  action,
  secondaryAction,
  rows = 4,
  skeletonVariant = "page",
  showLoadingCaption = true,
  className,
  ...props
}: PageStateProps) {
  if (state === "loading") {
    return (
      <ContentSkeleton
        rows={rows}
        variant={skeletonVariant}
        showCaption={showLoadingCaption}
        className={cn("rounded-lg border border-hairline bg-canvas shadow-card", className)}
      />
    );
  }

  return (
    <EmptyState
      chapter={eyebrow}
      title={title}
      description={description}
      action={action}
      secondaryAction={secondaryAction}
      tone={stateTone[state]}
      className={className}
      {...props}
    />
  );
}
```

- [ ] **Step 12: Export page primitives**

Create `frontend/src/components/page/index.ts`:

```ts
export { PageActions } from "./PageActions";
export type { PageActionsProps } from "./PageActions";

export { PageHeader } from "./PageHeader";
export type { PageHeaderProps } from "./PageHeader";

export { PageSection } from "./PageSection";
export type { PageSectionProps, PageSectionVariant } from "./PageSection";

export { PageShell } from "./PageShell";
export type { PageShellDensity, PageShellProps, PageShellWidth } from "./PageShell";

export { PageState } from "./PageState";
export type { PageStateKind, PageStateProps } from "./PageState";
```

- [ ] **Step 13: Run primitive tests to verify they pass**

Run:

```bash
cd frontend
npm test -- src/components/page
```

Expected: PASS with 5 test files.

- [ ] **Step 14: Commit shared primitives**

Run:

```bash
git add frontend/src/components/page
git commit -m "新增共享页面结构组件"
```

Expected: commit succeeds.

## Task 2: Compose Admin `ReportPage` From Shared Primitives

**Files:**

- Modify: `frontend/src/components/admin/ReportPage.tsx`
- Modify: `frontend/src/components/admin/__tests__/ReportPage.test.tsx`

- [ ] **Step 1: Add failing wrapper assertions**

In `frontend/src/components/admin/__tests__/ReportPage.test.tsx`, add this test inside the existing ReportPage describe block:

```tsx
it("uses shared page shell and section structure", async () => {
  renderWithClient(
    <ReportPage
      title="个人成绩"
      chapterLabel="REPORTS · 报表"
      queryKey="score-report"
      queryFn={queryFn}
      columns={columns}
    />,
  );

  expect(screen.getByText("REPORTS · 报表")).toBeInTheDocument();
  expect(screen.getByRole("heading", { level: 1, name: "个人成绩" })).toHaveClass(
    "font-display",
    "text-display-lg",
  );
  expect(screen.getByTestId("report-page-shell")).toHaveClass("gap-6");
  expect(screen.getByTestId("report-page-table-section")).toHaveClass("rounded-lg", "shadow-card");
});
```

- [ ] **Step 2: Run the ReportPage test to verify it fails**

Run:

```bash
cd frontend
npm test -- src/components/admin/__tests__/ReportPage.test.tsx
```

Expected: FAIL because `data-testid="report-page-shell"` and `data-testid="report-page-table-section"` are not present.

- [ ] **Step 3: Refactor `ReportPage` to compose shared primitives**

In `frontend/src/components/admin/ReportPage.tsx`, add imports:

```tsx
import { PageHeader, PageSection, PageShell } from "@/components/page";
```

Replace the returned JSX with this structure:

```tsx
return (
  <PageShell data-testid="report-page-shell" density="workbench" width="full" className="gap-4">
    <PageHeader
      eyebrow={chapterLabel}
      title={title}
      description={description}
      actions={actions}
      className="items-start"
    />

    {query.isLoading ? (
      <PageSection variant="table" data-testid="report-page-table-section">
        <ContentSkeleton rows={3} showCaption variant="table" className="p-0" />
      </PageSection>
    ) : (
      <PageSection variant="plain" data-testid="report-page-table-section">
        <SimpleDataTable
          columns={columns}
          data={query.data ?? []}
          rowClassName={rowClassName}
          rowKey={rowKey}
          className={cn("bg-canvas", tableClassName)}
        />
      </PageSection>
    )}
  </PageShell>
);
```

Keep the existing `ReportPageProps`, `query`, `chapterLabel = adminPageCopy.reports`, and `cn` import.

- [ ] **Step 4: Run the ReportPage test to verify it passes**

Run:

```bash
cd frontend
npm test -- src/components/admin/__tests__/ReportPage.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Run admin report page tests**

Run:

```bash
cd frontend
npm test -- src/pages/admin/ScoreReportPage.test.tsx src/pages/admin/AbsentCandidatePage.test.tsx
```

Expected: PASS.

- [ ] **Step 6: Commit ReportPage migration**

Run:

```bash
git add frontend/src/components/admin/ReportPage.tsx frontend/src/components/admin/__tests__/ReportPage.test.tsx
git commit -m "统一管理端报表页面骨架"
```

Expected: commit succeeds.

## Task 3: Migrate Candidate Ordinary Pages

**Files:**

- Modify: `frontend/src/pages/LoginPage.tsx`
- Modify: `frontend/src/pages/ExamListPage.tsx`
- Modify: `frontend/src/pages/ExamStartPage.tsx`
- Modify: `frontend/src/pages/ExamResultPage.tsx`
- Modify: `frontend/src/pages/P0Pages.test.tsx`

- [ ] **Step 1: Add failing candidate structure assertions**

In `frontend/src/pages/P0Pages.test.tsx`, add these assertions to the existing candidate page tests or create new tests in the same file:

```tsx
it("candidate login uses the shared auth page header without app navigation", () => {
  renderPage("login", <LoginPage />, {
    candidate: null,
    loginCandidate: vi.fn(),
    logoutCandidate: vi.fn(),
  });

  expect(screen.getByText("CANDIDATE · 登录")).toBeInTheDocument();
  expect(screen.getByRole("heading", { level: 1 })).toHaveClass("font-display", "text-display-lg");
  expect(screen.getByTestId("candidate-login-header")).toBeInTheDocument();
  expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
  expect(screen.queryByRole("contentinfo")).not.toBeInTheDocument();
});

it("candidate exam list uses shared page shell and header", async () => {
  vi.mocked(getActiveExams).mockResolvedValue([exam]);

  renderPage("exams", <ExamListPage />);

  expect(await screen.findByText("EXAMS · 考试")).toBeInTheDocument();
  expect(screen.getByTestId("candidate-exam-list-shell")).toHaveClass("gap-8");
  expect(screen.getByRole("heading", { level: 1, name: "今天有一场考试等着你。" })).toHaveClass(
    "font-display",
    "text-display-lg",
  );
});
```

- [ ] **Step 2: Run candidate page tests to verify they fail**

Run:

```bash
cd frontend
npm test -- src/pages/P0Pages.test.tsx
```

Expected: FAIL on at least one new shared-structure assertion.

- [ ] **Step 3: Migrate `LoginPage` header and form surface**

In `frontend/src/pages/LoginPage.tsx`, add:

```tsx
import { PageHeader, PageSection } from "@/components/page";
```

Replace the existing login header block:

```tsx
<header className="flex flex-col gap-3">
  <ChapterNumber>{candidatePageCopy.login}</ChapterNumber>
  <h1 className="font-display text-display-lg font-semibold leading-[1.12] text-ink">
    进入考试。
  </h1>
  <p className="text-body-lg text-body">请输入姓名和身份证号后六位，进入你的考试与练习。</p>
</header>
```

with:

```tsx
<PageHeader
  data-testid="candidate-login-header"
  eyebrow={candidatePageCopy.login}
  title="进入考试。"
  description="请输入姓名和身份证号后六位，进入你的考试与练习。"
  className="md:flex-col md:items-start md:justify-start"
/>
```

Wrap the complete existing form `Card` subtree with `<PageSection variant="plain" className="max-w-md">` and a matching `</PageSection>`. Keep every existing `Card`, form field, submit button, mutation call, and alert exactly as it is inside that wrapper.

Do not add candidate navigation or footer to `/login`.

- [ ] **Step 4: Migrate `ExamListPage` shell, header, and empty state**

In `frontend/src/pages/ExamListPage.tsx`, add:

```tsx
import { PageHeader, PageShell, PageState } from "@/components/page";
```

Replace the top-level page container:

```tsx
<div data-stagger className="flex flex-col gap-8">
```

with:

```tsx
<PageShell data-testid="candidate-exam-list-shell" density="calm" stagger>
```

Replace the page header with:

```tsx
<PageHeader
  eyebrow={candidatePageCopy.exams}
  title="可参加考试"
  description="选择一场考试，开始前请确认考试规则。"
/>
```

Replace the no-exam empty state with:

```tsx
<PageState
  state="empty"
  eyebrow={candidatePageCopy.empty}
  title="暂无可参加考试。"
  description="当前没有开放给你的考试，请稍后再来查看。"
/>
```

Close the shell with `</PageShell>` instead of `</div>`.

- [ ] **Step 5: Migrate `ExamStartPage` shell, header, sections, and not-started state**

In `frontend/src/pages/ExamStartPage.tsx`, add:

```tsx
import { PageHeader, PageSection, PageShell, PageState } from "@/components/page";
```

Replace the current top-level exam rules page container with:

```tsx
<PageShell density="calm" stagger>
  <PageHeader
    eyebrow={candidatePageCopy.examRules}
    title={exam.title}
    description="开始前请确认考试时间、题量与提交规则。"
  />
</PageShell>
```

Then replace the existing rounded exam-rules section opening tag with `<PageSection variant="panel">` and replace its closing `</section>` with `</PageSection>`. Keep the complete existing section children unchanged.

Replace any page-level `EmptyState` for unavailable exam rules with:

```tsx
<PageState
  state="empty"
  eyebrow={candidatePageCopy.empty}
  title="暂时无法进入考试。"
  description="当前考试尚未开放或不在你的应考名单中。"
/>
```

Keep the existing start button behavior and API calls unchanged.

- [ ] **Step 6: Migrate safe parts of `ExamResultPage`**

In `frontend/src/pages/ExamResultPage.tsx`, add:

```tsx
import { PageHeader, PageSection, PageShell, PageState } from "@/components/page";
```

For loading states, use:

```tsx
<PageState state="loading" rows={4} skeletonVariant="page" />
```

For error or empty states, use:

```tsx
<PageState
  state="error"
  eyebrow={candidatePageCopy.error}
  title="结果加载失败。"
  description="请返回考试列表后重新进入结果页。"
/>
```

Keep the dark score hero card intact. For the ordinary review list, replace the existing section opening tag with `<PageSection variant="plain">` and replace its closing `</section>` with `</PageSection>`. Keep the complete review-list children unchanged.

- [ ] **Step 7: Run candidate page tests**

Run:

```bash
cd frontend
npm test -- src/pages/P0Pages.test.tsx
```

Expected: PASS.

- [ ] **Step 8: Commit candidate ordinary page migration**

Run:

```bash
git add frontend/src/pages/LoginPage.tsx frontend/src/pages/ExamListPage.tsx frontend/src/pages/ExamStartPage.tsx frontend/src/pages/ExamResultPage.tsx frontend/src/pages/P0Pages.test.tsx
git commit -m "统一候选人普通页面骨架"
```

Expected: commit succeeds.

## Task 4: Migrate Admin Ordinary Pages

**Files:**

- Modify: `frontend/src/pages/admin/AdminDashboardPage.tsx`
- Modify: `frontend/src/pages/admin/AdminDashboardPage.test.tsx`
- Modify: `frontend/src/pages/admin/ExamEditPage.tsx`
- Modify: `frontend/src/pages/admin/ExamEditPage.test.tsx`
- Modify: `frontend/src/pages/admin/ExamCandidatesPage.tsx`
- Modify: `frontend/src/pages/admin/ExamCandidatesPage.test.tsx`
- Modify: `frontend/src/pages/admin/QuestionImportPage.tsx`
- Modify: `frontend/src/pages/admin/QuestionImportPage.test.tsx`
- Modify: `frontend/src/pages/admin/CandidateImportPage.tsx`
- Modify: `frontend/src/pages/admin/CandidateImportPage.test.tsx`

- [ ] **Step 1: Add failing admin structure assertions**

In each listed admin test file, add one assertion that the page still renders its semantic eyebrow and that a shared page header H1 class is present.

Example for `frontend/src/pages/admin/AdminDashboardPage.test.tsx`:

```tsx
it("uses shared admin page shell and header", async () => {
  vi.mocked(getAdminQuestions).mockResolvedValue([]);
  vi.mocked(getAdminExams).mockResolvedValue([]);
  vi.mocked(getScoreReport).mockResolvedValue([]);
  vi.mocked(getAbsentCandidates).mockResolvedValue([]);

  renderDashboard();

  expect(screen.getByText("OVERVIEW · 仪表盘")).toBeInTheDocument();
  expect(screen.getByRole("heading", { level: 1, name: "一切就绪。" })).toHaveClass(
    "font-display",
    "text-display-lg",
  );
  expect(await screen.findByTestId("admin-dashboard-shell")).toHaveClass("gap-6");
});
```

Example for `frontend/src/pages/admin/QuestionImportPage.test.tsx`:

```tsx
it("uses shared import page structure", () => {
  renderPage();

  expect(screen.getByText("LIBRARY · 题库")).toBeInTheDocument();
  expect(screen.getByRole("heading", { level: 1, name: "题库导入" })).toHaveClass(
    "font-display",
    "text-display-lg",
  );
  expect(screen.getByTestId("question-import-shell")).toHaveClass("gap-6");
});
```

Use page-specific test ids:

- `admin-dashboard-shell`
- `exam-edit-shell`
- `exam-candidates-shell`
- `question-import-shell`
- `candidate-import-shell`

- [ ] **Step 2: Run admin targeted tests to verify they fail**

Run:

```bash
cd frontend
npm test -- src/pages/admin/AdminDashboardPage.test.tsx src/pages/admin/ExamEditPage.test.tsx src/pages/admin/ExamCandidatesPage.test.tsx src/pages/admin/QuestionImportPage.test.tsx src/pages/admin/CandidateImportPage.test.tsx
```

Expected: FAIL because the shared shell test ids are not present.

- [ ] **Step 3: Migrate `AdminDashboardPage`**

In `frontend/src/pages/admin/AdminDashboardPage.tsx`, add:

```tsx
import { PageHeader, PageSection, PageShell, PageState } from "@/components/page";
```

Replace:

```tsx
<div data-stagger className="flex flex-col gap-8">
```

with:

```tsx
<PageShell data-testid="admin-dashboard-shell" density="workbench" width="full" stagger>
```

Replace the header with:

```tsx
<PageHeader
  eyebrow={adminPageCopy.overview}
  title="一切就绪。"
  description={`最近一次刷新 · ${new Date().toLocaleString("zh-CN")}`}
/>
```

For the activity section, replace the current section opening tag with `<PageSection variant="card">` and replace its closing `</section>` with `</PageSection>`. Keep the activity header, skeleton, list, and empty-state conditional in the same order.

Replace the dashboard empty activity `EmptyState` with:

```tsx
<PageState
  state="empty"
  eyebrow={adminPageCopy.empty}
  title="暂无活动记录。"
  description="当有人交卷或缺席名单产生后，最近活动会显示在这里。"
  className="py-8"
/>
```

Close the shell with `</PageShell>`.

- [ ] **Step 4: Migrate `ExamEditPage`**

In `frontend/src/pages/admin/ExamEditPage.tsx`, add:

```tsx
import { PageHeader, PageSection, PageShell } from "@/components/page";
```

Replace the outer container:

```tsx
<div data-stagger className="flex flex-col gap-8">
```

with:

```tsx
<PageShell data-testid="exam-edit-shell" density="workbench" width="full" stagger>
```

Replace the header with:

```tsx
<PageHeader
  eyebrow={adminPageCopy.exams}
  title={`编辑考试 #${examId ?? "-"}`}
  actions={
    <>
      <Button asChild variant="outline" size="sm">
        <Link to="/admin/exams">
          <X data-icon="inline-start" />
          取消
        </Link>
      </Button>
      <Button
        type="button"
        size="sm"
        disabled={mutation.isPending}
        onClick={form.handleSubmit((values) => mutation.mutate(values))}
      >
        <Save data-icon="inline-start" />
        {mutation.isPending ? "保存中" : "保存配置"}
      </Button>
    </>
  }
/>
```

Replace the form section wrapper opening tag with `<PageSection variant="card" className="grid gap-6 lg:grid-cols-2 lg:p-8">` and replace the matching closing `</section>` with `</PageSection>`.

Keep every form field, validation rule, mutation, and disabled-state expression unchanged.

- [ ] **Step 5: Migrate `ExamCandidatesPage`**

In `frontend/src/pages/admin/ExamCandidatesPage.tsx`, add:

```tsx
import { PageHeader, PageSection, PageShell } from "@/components/page";
```

Replace the outer page container and header with:

```tsx
<PageShell data-testid="exam-candidates-shell" density="workbench" width="full" stagger>
  <PageHeader
    eyebrow={adminPageCopy.candidates}
    title="应考人员名单"
    description="本名单决定谁可以进入这场考试。考试发布后名单冻结，只保留补考授权操作。"
  />
</PageShell>
```

Then replace the current import controls section opening tag with `<PageSection variant="panel">` and replace its closing `</section>` with `</PageSection>`. Replace the current table section opening tag with `<PageSection variant="table">` and replace its closing `</section>` with `</PageSection>`.

Keep import, retake, remove, failure-report, and table behavior unchanged.

- [ ] **Step 6: Migrate import pages**

For `frontend/src/pages/admin/QuestionImportPage.tsx`, add:

```tsx
import { PageHeader, PageSection, PageShell } from "@/components/page";
```

Replace the outer page container and header with:

```tsx
<PageShell data-testid="question-import-shell" density="workbench" width="default" stagger>
  <PageHeader
    eyebrow={adminPageCopy.library}
    title="题库导入"
    description="上传标准 Excel 模板，系统会校验行数据并保存可用题目。"
  />
</PageShell>
```

Then replace the upload form section opening tag with `<PageSection variant="panel">` and its closing `</section>` with `</PageSection>`. Replace the import result section opening tag with `<PageSection variant="card">` and its closing `</section>` with `</PageSection>`.

For `frontend/src/pages/admin/CandidateImportPage.tsx`, add:

```tsx
import { PageHeader, PageSection, PageShell } from "@/components/page";
```

Replace the outer page container and header with:

```tsx
<PageShell data-testid="candidate-import-shell" density="workbench" width="default" stagger>
  <PageHeader
    eyebrow={adminPageCopy.candidates}
    title="应考人员导入"
    description="上传人员 Excel 模板，系统会按当前考试写入应考名单。"
  />
</PageShell>
```

Then replace the upload form section opening tag with `<PageSection variant="panel">` and its closing `</section>` with `</PageSection>`. Replace the import result section opening tag with `<PageSection variant="card">` and its closing `</section>` with `</PageSection>`.

Keep existing field labels, file inputs, download buttons, failure reports, mutation behavior, and notices unchanged.

- [ ] **Step 7: Run admin targeted tests**

Run:

```bash
cd frontend
npm test -- src/pages/admin/AdminDashboardPage.test.tsx src/pages/admin/ExamEditPage.test.tsx src/pages/admin/ExamCandidatesPage.test.tsx src/pages/admin/QuestionImportPage.test.tsx src/pages/admin/CandidateImportPage.test.tsx
```

Expected: PASS.

- [ ] **Step 8: Commit admin ordinary page migration**

Run:

```bash
git add frontend/src/pages/admin/AdminDashboardPage.tsx frontend/src/pages/admin/AdminDashboardPage.test.tsx frontend/src/pages/admin/ExamEditPage.tsx frontend/src/pages/admin/ExamEditPage.test.tsx frontend/src/pages/admin/ExamCandidatesPage.tsx frontend/src/pages/admin/ExamCandidatesPage.test.tsx frontend/src/pages/admin/QuestionImportPage.tsx frontend/src/pages/admin/QuestionImportPage.test.tsx frontend/src/pages/admin/CandidateImportPage.tsx frontend/src/pages/admin/CandidateImportPage.test.tsx
git commit -m "统一管理端普通页面骨架"
```

Expected: commit succeeds.

## Task 5: Align Candidate And Admin Auth Canvases

**Files:**

- Modify: `frontend/src/pages/LoginPage.tsx`
- Modify: `frontend/src/pages/admin/AdminLoginPage.tsx`
- Modify: `frontend/src/pages/admin/AdminLoginPage.test.tsx`
- Modify: `frontend/src/pages/P0Pages.test.tsx`

- [ ] **Step 1: Add auth canvas assertions**

In `frontend/src/pages/admin/AdminLoginPage.test.tsx`, add:

```tsx
it("renders as a clean auth canvas without admin navigation or footer", () => {
  renderPage();

  expect(screen.getByText("ADMIN · 登录")).toBeInTheDocument();
  expect(screen.getByRole("heading", { level: 1, name: "安静地工作。" })).toHaveClass(
    "font-display",
    "text-display-lg",
  );
  expect(screen.getByTestId("admin-login-header")).toBeInTheDocument();
  expect(screen.getByTestId("admin-login-form-section")).toHaveClass("rounded-md");
  expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
  expect(screen.queryByRole("contentinfo")).not.toBeInTheDocument();
});
```

In `frontend/src/pages/P0Pages.test.tsx`, ensure candidate login has the same nav/footer absence assertion:

```tsx
expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
expect(screen.queryByRole("contentinfo")).not.toBeInTheDocument();
```

- [ ] **Step 2: Run auth tests**

Run:

```bash
cd frontend
npm test -- src/pages/admin/AdminLoginPage.test.tsx src/pages/P0Pages.test.tsx
```

Expected: FAIL because `admin-login-header` and `admin-login-form-section` are not present yet.

- [ ] **Step 3: Migrate `AdminLoginPage` header and form surface**

In `frontend/src/pages/admin/AdminLoginPage.tsx`, add:

```tsx
import { PageHeader, PageSection } from "@/components/page";
```

Replace the admin login header with:

```tsx
<PageHeader
  data-testid="admin-login-header"
  eyebrow={adminPageCopy.login}
  title="安静地工作。"
  description="管理员登录后可访问题库、考试配置与所有报表。"
  className="md:flex-col md:items-start md:justify-start"
/>
```

Wrap the complete existing admin login `form` subtree with `<PageSection data-testid="admin-login-form-section" variant="panel" className="max-w-md">` and a matching `</PageSection>`. Keep the current `form` element, field group, submit button, spinner, mutation call, and error alert unchanged inside that wrapper.

Keep the right-side editorial panel and admin login mutation unchanged.

- [ ] **Step 4: Run auth tests**

Run:

```bash
cd frontend
npm test -- src/pages/admin/AdminLoginPage.test.tsx src/pages/P0Pages.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit auth canvas alignment**

Run:

```bash
git add frontend/src/pages/LoginPage.tsx frontend/src/pages/admin/AdminLoginPage.tsx frontend/src/pages/admin/AdminLoginPage.test.tsx frontend/src/pages/P0Pages.test.tsx
git commit -m "统一登录页面认证画布"
```

Expected: commit succeeds.

## Task 6: Audit Focus Mode Without Flattening It

**Files:**

- Modify: `frontend/src/pages/PracticePage.tsx`
- Modify: `frontend/src/pages/ExamTakingPage.tsx`
- Modify: `frontend/src/pages/P0Pages.test.tsx`

- [ ] **Step 1: Add focus-mode regression assertions**

In `frontend/src/pages/P0Pages.test.tsx`, add or extend tests to assert:

```tsx
expect(screen.getByText("PRACTICE · 练习")).toBeInTheDocument();
expect(screen.getByText("EXAMS · 考试")).toBeInTheDocument();
```

For states already covered by existing tests, assert the state eyebrow:

```tsx
expect(screen.getByText("STATE · 未登录")).toBeInTheDocument();
expect(screen.getByText("STATE · 未开始")).toBeInTheDocument();
expect(screen.getByText("STATE · 已提交")).toBeInTheDocument();
```

Do not add tests that require exact pixel positions in Vitest. Browser QA covers fixed right-side navigation.

- [ ] **Step 2: Run focus tests before implementation**

Run:

```bash
cd frontend
npm test -- src/pages/P0Pages.test.tsx
```

Expected: PASS for existing behavior or FAIL only on assertions that depend on new `PageState` usage.

- [ ] **Step 3: Apply safe `PageShell` and `PageState` usage in `PracticePage`**

In `frontend/src/pages/PracticePage.tsx`, add:

```tsx
import { PageShell, PageState } from "@/components/page";
```

Use `PageShell density="focus" width="full"` for the outer successful page rhythm by replacing the outer successful-flow container opening tag with:

```tsx
<PageShell density="focus" width="full" stagger className="relative">
```

Replace the matching closing tag with `</PageShell>`.

Replace only page-level not-logged-in, loading, empty, and error states with `PageState`.

Example:

```tsx
<PageState
  state="notLoggedIn"
  eyebrow={candidatePageCopy.notLoggedIn}
  title="请先登录。"
  description="登录后可以进入练习题库。"
/>
```

Keep question cards, answer option logic, progress controls, fixed desktop navigator, and mobile sheet navigator unchanged.

- [ ] **Step 4: Apply safe `PageShell` and `PageState` usage in `ExamTakingPage`**

In `frontend/src/pages/ExamTakingPage.tsx`, add:

```tsx
import { PageShell, PageState } from "@/components/page";
```

Use `PageShell density="focus" width="full"` for the outer successful-flow container by replacing its opening tag with:

```tsx
<PageShell density="focus" width="full" stagger className="relative">
```

Replace the matching closing tag with `</PageShell>`.

Replace only state surfaces:

```tsx
<PageState
  state="notStarted"
  eyebrow={candidatePageCopy.notStarted}
  title="未开始考试。"
  description="请从考试列表进入并确认考试规则。"
/>
```

```tsx
<PageState
  state="submitted"
  eyebrow={candidatePageCopy.submitted}
  title="考试已提交。"
  description="你可以前往结果页查看本次提交。"
/>
```

Keep autosave, submit, timer, answer selection, fixed desktop navigator, and mobile sheet navigator unchanged.

- [ ] **Step 5: Run focus tests**

Run:

```bash
cd frontend
npm test -- src/pages/P0Pages.test.tsx
```

Expected: PASS.

- [ ] **Step 6: Commit focus-mode audit**

Run:

```bash
git add frontend/src/pages/PracticePage.tsx frontend/src/pages/ExamTakingPage.tsx frontend/src/pages/P0Pages.test.tsx
git commit -m "收敛候选人作答页面状态骨架"
```

Expected: commit succeeds.

## Task 7: Update Design Documentation And Run Full Verification

**Files:**

- Modify: `frontend/DESIGN.md`

- [ ] **Step 1: Update `frontend/DESIGN.md`**

Add this section after `## Component Rules`:

```markdown
## Page Primitives

Use `src/components/page/` for shared page-level structure:

- `PageShell` controls page rhythm, width, density, and stagger entrance.
- `PageHeader` controls page eyebrow, H1, description, and actions.
- `PageSection` controls repeated content surfaces with `plain`, `card`, `panel`, and `table` variants.
- `PageState` wraps `ContentSkeleton` and `EmptyState` for loading, empty, error, and candidate attempt states.
- `PageActions` keeps page-level action buttons wrapping predictably on mobile.

Candidate and admin pages should share these primitives while keeping their navigation models different. Candidate pages keep top navigation. Admin pages keep side rail navigation. Exam-taking and practice pages may use `PageShell density="focus"` and `PageState`, but their question layout, timer, autosave, and navigator remain specialized.
```

Update the `## Layouts` section to say:

```markdown
Ordinary candidate and admin pages should compose `PageShell`, `PageHeader`, `PageSection`, and `PageState` before adding page-specific content. Avoid hand-written page headers unless the page is a specialized focus-mode workflow.
```

- [ ] **Step 2: Run static product-page scan**

Run:

```bash
rg -n "CHAPTER [0-9]|CHAPTER ·" frontend/src/pages frontend/src/components/admin frontend/src/components/page
```

Expected: no product-page matches. Component tests may still use historical example strings outside these product paths.

- [ ] **Step 3: Run format check**

Run:

```bash
cd frontend
npm run format:check
```

Expected: PASS.

- [ ] **Step 4: Run lint**

Run:

```bash
cd frontend
npm run lint
```

Expected: PASS with no errors.

- [ ] **Step 5: Run all tests**

Run:

```bash
cd frontend
npm test
```

Expected: PASS.

- [ ] **Step 6: Run TypeScript**

Run:

```bash
cd frontend
npx tsc --noEmit
```

Expected: PASS.

- [ ] **Step 7: Run production build**

Run:

```bash
cd frontend
npm run build
```

Expected: PASS.

- [ ] **Step 8: Run whitespace diff check**

Run:

```bash
git diff --check
```

Expected: PASS with no output.

- [ ] **Step 9: Run browser QA**

Start the frontend dev server:

```bash
cd frontend
npm run dev -- --port 5174
```

Check backend health:

```bash
curl -s http://localhost:8000/api/health
```

Expected response contains:

```json
{"success":true}
```

Using the Browser plugin, verify these routes:

- `/login`
- `/exams`
- `/practice`
- `/admin/login`
- `/admin/dashboard`
- `/admin/questions/import`
- `/admin/exams`
- `/admin/reports/wrong`

For each route, verify:

- expected page eyebrow is visible
- H1 is visible and not overlapped
- navigation model is unchanged
- console `error`, `warn`, and `warning` logs are empty

For `/admin/questions/import`, verify:

- only the `导入` nav item is active
- `题库` is not active

For `/practice` and an exam-taking route with data available, verify:

- desktop question navigator remains fixed at the side when scrolling
- mobile navigator still opens as a bottom sheet

- [ ] **Step 10: Commit docs and final polish**

Run:

```bash
git add frontend/DESIGN.md frontend/src
git commit -m "完善前端页面一致性规范"
```

Expected: commit succeeds.

## Final Completion Checklist

Before reporting completion:

- [ ] Confirm all seven tasks have been completed or explicitly document any skipped task with reason.
- [ ] Run `git status --short` and confirm only intended files are changed or the tree is clean.
- [ ] Re-run the full verification set from Task 7 if any code changed after the first full verification.
- [ ] Summarize browser QA with exact routes checked and console result.
- [ ] Mention any residual risk, especially if a focus-mode route could not be fully exercised due missing live data.
