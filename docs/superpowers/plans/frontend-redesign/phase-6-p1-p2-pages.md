# Phase 6: P1 & P2 Pages — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite 14 pages (6 P1 + 3 non-report P2 + 4 report P2 + 1 admin login) with standard Academic Editorial visual fidelity, plus 3 admin components (MetricCard, ReportPage rewrite, SimpleDataTable rewrite with mobile card renderer) and one `useMediaQuery` hook.

**Architecture:** All P1/P2 pages reuse the chapter-header + italic-h1 + 米色卡 pattern established in P0. The 4 reports share the rewritten `ReportPage` container. Tables use the rewritten `SimpleDataTable` which branches between desktop table and mobile card list based on a `useMediaQuery` hook. Admin login has a special desktop layout: 50/50 split with a full-black right column overlaid by an 8% white radial dot pattern. The 4 report pages use `meta.mobilePriority` to decide which columns appear on phones.

**Tech Stack:** All previous (React 19, Tailwind 3.4, TanStack Query, TanStack Table 8.21, React Hook Form + Zod, lucide-react, Radix Slot) + Vitest + Testing Library for new component tests. No new dependencies.

---

## Working Directory

All paths in this plan are relative to `frontend/` unless explicitly noted. Run `cd frontend &&` before every npm command shown.

---

## Pre-flight: Verify Phase 1–5 are in place

This plan assumes prior phases have shipped. Confirm before starting:

- Phase 1: `frontend/src/index.css` defines the full token set; `tailwind.config.ts` exposes the new utility classes; `frontend/src/lib/design-tokens.ts` exports named constants.
- Phase 2: `frontend/src/components/ui/button.tsx` is pill-shaped with variants `default | outline | ghost | link`; `card.tsx` provides `Card | CardHeader | CardContent | CardDescription | CardTitle`; `input.tsx` / `label.tsx` are restyled; `table.tsx` is the new no-zebra variant.
- Phase 3: `frontend/src/components/editorial/` directory contains `ChapterNumber.tsx`, `Wordmark.tsx`, `StatusPill.tsx`, `EmptyState.tsx`, `NamePlate.tsx`. (Used by pages below.)
- Phase 4: `frontend/src/components/layout/` contains `TopNav.tsx`, `Footer.tsx`, `CandidateLayout.tsx`, `AdminLayout.tsx`, `AdminSideRail.tsx`. AdminLayout uses AdminSideRail.
- Phase 5: P0 pages (`LoginPage`, `ExamTakingPage`, `ExamResultPage`, `PracticePage`) already use the chapter + italic h1 pattern.

If any phase is missing, STOP and run that plan first.

---

## File map (13 pages + 3 components + 1 test hook)

New / rewritten files:

- `frontend/src/lib/useMediaQuery.ts` — new, media-query hook used by SimpleDataTable + ReportPage + ranking cards
- `frontend/src/components/admin/MetricCard.tsx` — new
- `frontend/src/components/admin/SimpleDataTable.tsx` — rewrite (add mobile card renderer)
- `frontend/src/components/admin/ReportPage.tsx` — rewrite (add chapter + italic h1 + description)
- `frontend/src/pages/ExamListPage.tsx` — rewrite (P1)
- `frontend/src/pages/ExamStartPage.tsx` — rewrite (P1)
- `frontend/src/pages/RankingPage.tsx` — rewrite (P1)
- `frontend/src/pages/admin/AdminLoginPage.tsx` — rewrite (P1, full black right column desktop layout)
- `frontend/src/pages/admin/AdminDashboardPage.tsx` — rewrite (P1, 4 MetricCards)
- `frontend/src/pages/admin/ExamEditPage.tsx` — rewrite (P1)
- `frontend/src/pages/admin/QuestionImportPage.tsx` — rewrite (P1)
- `frontend/src/pages/admin/QuestionListPage.tsx` — rewrite (P2, table page)
- `frontend/src/pages/admin/ExamListPage.tsx` — rewrite (P2 admin, table page)
- `frontend/src/pages/admin/CandidateImportPage.tsx` — rewrite (P2, import form)
- `frontend/src/pages/admin/ScoreReportPage.tsx` — minimal (already uses ReportPage; only add mobilePriority meta to columns)
- `frontend/src/pages/admin/QuestionAccuracyPage.tsx` — minimal
- `frontend/src/pages/admin/WrongQuestionPage.tsx` — minimal
- `frontend/src/pages/admin/AbsentCandidatePage.tsx` — minimal

Test files (Vitest + Testing Library):

- `frontend/src/components/admin/__tests__/MetricCard.test.tsx`
- `frontend/src/components/admin/__tests__/SimpleDataTable.test.tsx`
- `frontend/src/components/admin/__tests__/ReportPage.test.tsx`

Note: pages are verified by `npm run build` + `npx tsc --noEmit` + `npm run lint`. They contain heavy routing and TanStack Query hooks which are out of scope for unit tests; the plan enforces type-level guarantees by reusing `api/*` and `types/*` (which already have correct types).

---

## Task 1: Add `useMediaQuery` hook

**Files:**
- Create: `frontend/src/lib/useMediaQuery.ts`

- [ ] **Step 1: Create the hook file**

```ts
import { useEffect, useState } from "react";

export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState<boolean>(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return false;
    }
    return window.matchMedia(query).matches;
  });

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return;
    }
    const list = window.matchMedia(query);
    const onChange = (event: MediaQueryListEvent) => {
      setMatches(event.matches);
    };
    setMatches(list.matches);
    list.addEventListener("change", onChange);
    return () => list.removeEventListener("change", onChange);
  }, [query]);

  return matches;
}

export const MD = {
  md: "(min-width: 768px)",
  lg: "(min-width: 1024px)",
} as const;
```

- [ ] **Step 2: Verify TypeScript**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no new errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/useMediaQuery.ts
git commit -m "feat(frontend): 新增 useMediaQuery 媒体查询 hook"
```

---

## Task 2: Implement `MetricCard` component (TDD)

**Files:**
- Create: `frontend/src/components/admin/__tests__/MetricCard.test.tsx`
- Create: `frontend/src/components/admin/MetricCard.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/admin/__tests__/MetricCard.test.tsx`:

```tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { MetricCard } from "../MetricCard";

describe("MetricCard", () => {
  it("renders the italic-caps label and value", () => {
    render(<MetricCard label="QUESTIONS · 题库" value={42} />);
    expect(screen.getByText("QUESTIONS · 题库")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("renders an optional unit next to the value", () => {
    render(<MetricCard label="QUESTIONS · 题库" value={42} unit="题" />);
    expect(screen.getByText("题")).toBeInTheDocument();
  });

  it("applies success tone color to the value", () => {
    render(<MetricCard label="EXAMS LIVE · 进行中" value={3} tone="success" />);
    const valueEl = screen.getByText("3");
    expect(valueEl.className).toContain("text-success");
  });

  it("applies warning tone color to the value", () => {
    render(<MetricCard label="ABSENT · 未参加" value={5} tone="warning" />);
    const valueEl = screen.getByText("5");
    expect(valueEl.className).toContain("text-warning");
  });

  it("uses default ink tone when tone prop is omitted", () => {
    render(<MetricCard label="SUBMITTED · 已提交" value={7} />);
    const valueEl = screen.getByText("7");
    expect(valueEl.className).toContain("text-ink");
  });

  it("renders an optional caption", () => {
    render(<MetricCard label="QUESTIONS · 题库" value={42} caption="最近更新 2 分钟前" />);
    expect(screen.getByText("最近更新 2 分钟前")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the test and watch it fail**

```bash
cd frontend && npx vitest run src/components/admin/__tests__/MetricCard.test.tsx
```

Expected: tests fail because `MetricCard.tsx` does not exist.

- [ ] **Step 3: Implement the component**

Create `frontend/src/components/admin/MetricCard.tsx`:

```tsx
import { cn } from "@/lib/utils";

type MetricTone = "default" | "success" | "warning";

interface MetricCardProps {
  label: string;
  value: string | number;
  unit?: string;
  tone?: MetricTone;
  caption?: string;
}

const TONE_CLASS: Record<MetricTone, string> = {
  default: "text-ink",
  success: "text-success",
  warning: "text-warning",
};

export function MetricCard({ label, value, unit, tone = "default", caption }: MetricCardProps) {
  return (
    <div className="rounded-lg border border-hairline bg-canvas p-[18px] shadow-card">
      <p className="text-caption font-body font-medium uppercase tracking-[0.16em] text-muted">
        {label}
      </p>
      <p className="mt-3 flex items-baseline gap-1 font-display text-[32px] font-semibold leading-none tracking-[-0.04em] lg:text-[40px]">
        <span className={cn(TONE_CLASS[tone])}>{value}</span>
        {unit ? <span className="text-body text-base text-muted">{unit}</span> : null}
      </p>
      {caption ? <p className="mt-3 text-caption text-muted">{caption}</p> : null}
    </div>
  );
}
```

- [ ] **Step 4: Run the test and watch it pass**

```bash
cd frontend && npx vitest run src/components/admin/__tests__/MetricCard.test.tsx
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/admin/MetricCard.tsx frontend/src/components/admin/__tests__/MetricCard.test.tsx
git commit -m "feat(admin): 实现 MetricCard 组件含 success/warning tone 颜色语义"
```

---

## Task 3: Rewrite `SimpleDataTable` with mobile card renderer (TDD)

**Files:**
- Create: `frontend/src/components/admin/__tests__/SimpleDataTable.test.tsx`
- Modify: `frontend/src/components/admin/SimpleDataTable.tsx` (full rewrite)

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/admin/__tests__/SimpleDataTable.test.tsx`:

```tsx
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import type { ColumnDef } from "@tanstack/react-table";

import { SimpleDataTable } from "../SimpleDataTable";

type Row = { id: number; name: string; score: number };

const columns: ColumnDef<Row>[] = [
  {
    accessorKey: "id",
    header: "ID",
    meta: { mobilePriority: false },
  },
  {
    accessorKey: "name",
    header: "NAME",
  },
  {
    accessorKey: "score",
    header: "SCORE",
    meta: { mobilePriority: "primary" },
  },
];

const rows: Row[] = [
  { id: 1, name: "Ada", score: 98 },
  { id: 2, name: "Linus", score: 72 },
];

const setMatchMedia = (matches: boolean) => {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string) => ({
      get matches() {
        return query.includes("768") ? matches : true;
      },
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }),
  });
};

describe("SimpleDataTable", () => {
  beforeEach(() => setMatchMedia(true));
  afterEach(() => vi.restoreAllMocks());

  it("renders a desktop table with thead and tbody", () => {
    render(<SimpleDataTable columns={columns} data={rows} />);
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByText("NAME")).toBeInTheDocument();
    expect(screen.getByText("Ada")).toBeInTheDocument();
  });

  it("renders the empty state when data is empty", () => {
    render(<SimpleDataTable columns={columns} data={[]} />);
    expect(screen.getByText("暂无数据")).toBeInTheDocument();
  });

  it("renders a card list on mobile (matches=false) and hides low-priority columns", () => {
    setMatchMedia(false);
    render(<SimpleDataTable columns={columns} data={rows} />);
    // No table element on mobile
    expect(screen.queryByRole("table")).toBeNull();
    // Both rows should be present
    const cards = screen.getAllByTestId("mobile-row-card");
    expect(cards).toHaveLength(2);
    // mobilePriority: false on "id" should be hidden
    const adaCard = cards[0]!;
    expect(within(adaCard).queryByText("1")).toBeNull();
    // mobilePriority: "primary" on "score" should still be visible
    expect(within(adaCard).getByText("98")).toBeInTheDocument();
    // name (no meta) should be visible
    expect(within(adaCard).getByText("Ada")).toBeInTheDocument();
  });

  it("respects a custom emptyText", () => {
    render(<SimpleDataTable columns={columns} data={[]} emptyText="空空如也" />);
    expect(screen.getByText("空空如也")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the test and watch it fail**

```bash
cd frontend && npx vitest run src/components/admin/__tests__/SimpleDataTable.test.tsx
```

Expected: tests fail because the current `SimpleDataTable` has no mobile renderer and no `data-testid="mobile-row-card"`.

- [ ] **Step 3: Rewrite the component**

Overwrite `frontend/src/components/admin/SimpleDataTable.tsx`:

```tsx
import { useMemo, type ReactNode } from "react";
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
  type Row,
} from "@tanstack/react-table";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { MD, useMediaQuery } from "@/lib/useMediaQuery";
import { cn } from "@/lib/utils";

type MobilePriority = "primary" | "secondary" | false;

declare module "@tanstack/react-table" {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  interface ColumnMeta<TData extends RowData, TValue> {
    mobilePriority?: MobilePriority;
    mobileLabel?: string;
  }
}

type SimpleDataTableProps<TData> = {
  columns: ColumnDef<TData>[];
  data: TData[];
  emptyText?: string;
  rowKey?: (row: TData) => string | number;
  rowClassName?: (row: TData) => string | undefined;
  mobileRowClassName?: (row: TData) => string | undefined;
  renderMobileRow?: (row: Row<TData>) => ReactNode;
};

function defaultMobileCardClassName(): string {
  return "rounded-lg border border-hairline bg-canvas p-4 shadow-card";
}

function defaultMobileRow<TData>(row: Row<TData>): ReactNode {
  const visibleColumns = row.getVisibleCells().filter((cell) => {
    const priority = cell.column.columnDef.meta?.mobilePriority;
    return priority !== false;
  });
  return (
    <>
      {visibleColumns.map((cell) => {
        const label = cell.column.columnDef.meta?.mobileLabel ?? cell.column.id;
        const priority = cell.column.columnDef.meta?.mobilePriority;
        const renderValue = cell.column.columnDef.cell
          ? flexRender(cell.column.columnDef.cell, cell.getContext())
          : String(cell.getValue() ?? "");
        return (
          <div
            key={cell.id}
            className={cn(
              "flex items-baseline justify-between gap-3 py-1 text-body",
              priority === "primary" && "font-display text-lg font-semibold text-ink",
            )}
          >
            <span className="text-caption uppercase tracking-[0.16em] text-muted">
              {label}
            </span>
            <span className="text-right">{renderValue}</span>
          </div>
        );
      })}
    </>
  );
}

export function SimpleDataTable<TData>({
  columns,
  data,
  emptyText = "暂无数据",
  rowKey,
  rowClassName,
  mobileRowClassName,
  renderMobileRow,
}: SimpleDataTableProps<TData>) {
  const isDesktop = useMediaQuery(MD.md);
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getRowId: (row, index) =>
      rowKey ? String(rowKey(row)) : String((row as { id?: number | string }).id ?? index),
  });

  const tableRows = table.getRowModel().rows;
  const isEmpty = tableRows.length === 0;

  const renderRow = renderMobileRow ?? defaultMobileRow;
  const mobileNodes = useMemo(
    () =>
      isEmpty
        ? []
        : tableRows.map((row) => (
            <div
              key={row.id}
              data-testid="mobile-row-card"
              className={cn(
                defaultMobileCardClassName(),
                mobileRowClassName?.(row.original) ?? "",
              )}
            >
              {renderRow(row)}
            </div>
          )),
    [isEmpty, tableRows, renderRow, mobileRowClassName],
  );

  if (isEmpty) {
    if (isDesktop) {
      return (
        <Table>
          <TableBody>
            <TableRow>
              <TableCell colSpan={columns.length} className="h-24 text-center text-muted">
                {emptyText}
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      );
    }
    return (
      <div className="rounded-lg border border-hairline bg-canvas p-6 text-center text-muted">
        {emptyText}
      </div>
    );
  }

  if (!isDesktop) {
    return <div className="flex flex-col gap-3">{mobileNodes}</div>;
  }

  return (
    <Table>
      <TableHeader>
        {table.getHeaderGroups().map((headerGroup) => (
          <TableRow key={headerGroup.id}>
            {headerGroup.headers.map((header) => (
              <TableHead key={header.id}>
                {header.isPlaceholder
                  ? null
                  : flexRender(header.column.columnDef.header, header.getContext())}
              </TableHead>
            ))}
          </TableRow>
        ))}
      </TableHeader>
      <TableBody>
        {tableRows.map((row) => (
          <TableRow key={row.id} className={rowClassName?.(row.original)}>
            {row.getVisibleCells().map((cell) => (
              <TableCell key={cell.id}>
                {flexRender(cell.column.columnDef.cell, cell.getContext())}
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
```

- [ ] **Step 4: Run the test and watch it pass**

```bash
cd frontend && npx vitest run src/components/admin/__tests__/SimpleDataTable.test.tsx
```

Expected: 4 passed.

- [ ] **Step 5: Type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no new errors. If `ColumnMeta` declaration merging conflicts with existing types, change to `interface ColumnMeta<TData, TValue>` as already shown.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/admin/SimpleDataTable.tsx frontend/src/components/admin/__tests__/SimpleDataTable.test.tsx
git commit -m "refactor(admin): SimpleDataTable 增加 mobile card renderer 与 columnVisibility"
```

---

## Task 4: Rewrite `ReportPage` container (TDD)

**Files:**
- Create: `frontend/src/components/admin/__tests__/ReportPage.test.tsx`
- Modify: `frontend/src/components/admin/ReportPage.tsx` (full rewrite)

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/admin/__tests__/ReportPage.test.tsx`:

```tsx
import { describe, expect, it } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ColumnDef } from "@tanstack/react-table";

import { ReportPage } from "../ReportPage";

type Row = { id: number; label: string };

const columns: ColumnDef<Row>[] = [
  { accessorKey: "id", header: "ID" },
  { accessorKey: "label", header: "LABEL" },
];

const queryFn = async (): Promise<Row[]> => [
  { id: 1, label: "first" },
  { id: 2, label: "second" },
];

const renderWithClient = (ui: React.ReactNode) => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
};

describe("ReportPage", () => {
  it("renders the chapter header, italic h1, and description", () => {
    renderWithClient(
      <ReportPage title="个人成绩" chapterLabel="CHAPTER 04 · REPORTS" description="每次考试的提交结果" queryKey="score-report" queryFn={queryFn} columns={columns} />,
    );
    expect(screen.getByText("CHAPTER 04 · REPORTS")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "个人成绩" })).toBeInTheDocument();
    expect(screen.getByText("每次考试的提交结果")).toBeInTheDocument();
  });

  it("calls queryFn with the expected queryKey and renders the rows", async () => {
    renderWithClient(
      <ReportPage title="题目正确率" queryKey="question-accuracy" queryFn={queryFn} columns={columns} />,
    );
    await waitFor(() => expect(screen.getByText("first")).toBeInTheDocument());
    expect(screen.getByText("second")).toBeInTheDocument();
  });

  it("renders an optional actions node", () => {
    renderWithClient(
      <ReportPage
        title="错题排行"
        queryKey="wrong-questions"
        queryFn={queryFn}
        columns={columns}
        actions={<button>导出 CSV</button>}
      />,
    );
    expect(screen.getByRole("button", { name: "导出 CSV" })).toBeInTheDocument();
  });

  it("shows a loading state while the query is pending", () => {
    const slowFn = () => new Promise<Row[]>(() => undefined);
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <ReportPage title="未参加人员" queryKey="absent" queryFn={slowFn} columns={columns} />
      </QueryClientProvider>,
    );
    expect(screen.getByText(/LOADING · 加载中/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the test and watch it fail**

```bash
cd frontend && npx vitest run src/components/admin/__tests__/ReportPage.test.tsx
```

Expected: tests fail; the current `ReportPage` does not render chapter labels, italic h1, description, or loading state.

- [ ] **Step 3: Rewrite the container**

Overwrite `frontend/src/components/admin/ReportPage.tsx`:

```tsx
import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";

import { SimpleDataTable } from "@/components/admin/SimpleDataTable";
import { ChapterNumber } from "@/components/editorial/ChapterNumber";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface ReportPageProps<TData> {
  title: string;
  queryKey: string;
  queryFn: () => Promise<TData[]>;
  columns: ColumnDef<TData>[];
  actions?: ReactNode;
  chapterLabel?: string;
  description?: string;
  rowKey?: (row: TData) => string | number;
  rowClassName?: (row: TData) => string | undefined;
  className?: string;
}

export function ReportPage<TData>({
  title,
  queryKey,
  queryFn,
  columns,
  actions,
  chapterLabel = "CHAPTER · REPORTS",
  description,
  rowKey,
  rowClassName,
  className,
}: ReportPageProps<TData>) {
  const { data = [], isLoading } = useQuery({ queryKey: [queryKey], queryFn });

  return (
    <section className={cn("flex flex-col gap-8", className)}>
      <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="flex flex-col gap-3">
          <ChapterNumber>{chapterLabel}</ChapterNumber>
          <h1 className="font-display text-[28px] font-semibold italic tracking-[-0.04em] text-ink lg:text-[40px]">
            {title}
          </h1>
          {description ? <p className="max-w-2xl text-body-lg text-body">{description}</p> : null}
        </div>
        {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
      </header>

      {isLoading ? (
        <div className="flex flex-col gap-3" aria-busy="true">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <p className="text-caption uppercase tracking-[0.16em] text-muted">
            LOADING · 加载中…
          </p>
        </div>
      ) : (
        <SimpleDataTable columns={columns} data={data} rowKey={rowKey} rowClassName={rowClassName} />
      )}
    </section>
  );
}
```

- [ ] **Step 4: Run the test and watch it pass**

```bash
cd frontend && npx vitest run src/components/admin/__tests__/ReportPage.test.tsx
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/admin/ReportPage.tsx frontend/src/components/admin/__tests__/ReportPage.test.tsx
git commit -m "refactor(admin): ReportPage 增加 chapter 头/italic h1/描述/loading"
```

---

## Task 5: Rewrite `ExamListPage` (candidate, P1)

**Files:**
- Modify: `frontend/src/pages/ExamListPage.tsx` (full rewrite)

- [ ] **Step 1: Rewrite the page**

Overwrite `frontend/src/pages/ExamListPage.tsx`:

```tsx
import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, Clock, FileText, Hash } from "lucide-react";
import { Link } from "react-router-dom";

import { getActiveExams } from "@/api/exams";
import { Button } from "@/components/ui/button";
import { ChapterNumber } from "@/components/editorial/ChapterNumber";
import { EmptyState } from "@/components/editorial/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import type { Exam } from "@/types/exam";

function ExamCard({ exam }: { exam: Exam }) {
  const isLive = exam.status === "active" || exam.status === "live";
  const totalQuestions = Array.isArray(exam.question_rule?.counts)
    ? (exam.question_rule.counts as number[]).reduce((a, b) => a + b, 0)
    : null;
  const startsAt =
    typeof exam.question_rule?.starts_at === "string"
      ? (exam.question_rule.starts_at as string)
      : null;
  return (
    <article className="flex flex-col gap-5 rounded-lg border border-hairline bg-canvas p-6 shadow-card lg:p-7">
      <p className="text-caption font-body font-medium uppercase italic tracking-[0.18em] text-muted">
        {isLive ? "LIVE · 进行中" : "DRAFT · 未开始"}
      </p>
      <h2 className="font-display text-[22px] font-semibold tracking-[-0.04em] text-ink lg:text-[24px]">
        {exam.title}
      </h2>
      <dl className="grid grid-cols-3 gap-3 border-y border-hairline-soft py-3 text-caption text-muted">
        <div className="flex flex-col gap-1">
          <dt className="flex items-center gap-1 uppercase tracking-[0.16em]">
            <Clock className="h-3 w-3" /> 时长
          </dt>
          <dd className="font-mono text-base text-ink">{exam.duration_minutes} 分钟</dd>
        </div>
        <div className="flex flex-col gap-1">
          <dt className="flex items-center gap-1 uppercase tracking-[0.16em]">
            <FileText className="h-3 w-3" /> 题数
          </dt>
          <dd className="font-mono text-base text-ink">
            {totalQuestions ?? "—"}
          </dd>
        </div>
        <div className="flex flex-col gap-1">
          <dt className="flex items-center gap-1 uppercase tracking-[0.16em]">
            <Hash className="h-3 w-3" /> 总分
          </dt>
          <dd className="font-mono text-base text-ink">
            {typeof exam.question_rule?.total_score === "number"
              ? (exam.question_rule.total_score as number)
              : "—"}
          </dd>
        </div>
      </dl>
      <div className="flex items-center justify-between gap-3">
        <p className="text-caption italic text-muted">
          {startsAt ? `开始时间 · ${startsAt}` : "随时开考"}
        </p>
        <Button asChild size="sm">
          <Link to={`/exams/${exam.id}/start`}>
            {isLive ? "进入考试" : "查看说明"}
            <ArrowUpRight data-icon="inline-end" />
          </Link>
        </Button>
      </div>
    </article>
  );
}

export function ExamListPage() {
  const { data = [], isLoading } = useQuery({
    queryKey: ["active-exams"],
    queryFn: getActiveExams,
  });

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-3">
        <ChapterNumber>CHAPTER 02 · EXAMS</ChapterNumber>
        <h1 className="font-display text-[28px] font-semibold italic tracking-[-0.04em] text-ink lg:text-[40px]">
          今天有三场考试等着你。
        </h1>
      </header>

      {isLoading ? (
        <div className="grid gap-5 md:grid-cols-2" aria-busy="true">
          <Skeleton className="h-[220px] w-full" />
          <Skeleton className="h-[220px] w-full" />
        </div>
      ) : data.length ? (
        <div className="grid gap-5 md:grid-cols-2">
          {data.map((exam) => (
            <ExamCard key={exam.id} exam={exam} />
          ))}
        </div>
      ) : (
        <EmptyState
          chapterLabel="CHAPTER 02 · EXAMS"
          title="暂无可参加考试。"
          description="管理员发布 active 考试后会显示在这里。"
        />
      )}
    </div>
  );
}
```

- [ ] **Step 2: Type-check and lint**

```bash
cd frontend && npx tsc --noEmit && npm run lint
```

Expected: 0 errors, 0 warnings (or only pre-existing warnings).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/ExamListPage.tsx
git commit -m "feat(pages): 重写 ExamListPage 加 chapter 头与考试卡 2 列网格"
```

---

## Task 6: Rewrite `ExamStartPage` (P1)

**Files:**
- Modify: `frontend/src/pages/ExamStartPage.tsx` (full rewrite)

- [ ] **Step 1: Rewrite the page**

Overwrite `frontend/src/pages/ExamStartPage.tsx`:

```tsx
import { useMutation } from "@tanstack/react-query";
import { ArrowRight, ClipboardCheck } from "lucide-react";
import { Link, useNavigate, useOutletContext, useParams } from "react-router-dom";

import { startExam } from "@/api/exams";
import type { CandidateSessionContext } from "@/components/layout/CandidateLayout";
import { Button } from "@/components/ui/button";
import { ChapterNumber } from "@/components/editorial/ChapterNumber";
import { NamePlate } from "@/components/editorial/NamePlate";
import type { Candidate } from "@/types/candidate";

const RULES: { text: string }[] = [
  { text: "考试中答案会自动暂存，但倒计时不会暂停。" },
  { text: "可以提前交卷，到时间系统会自动提交。" },
  { text: "提交后自动判分，并按配置展示答案与排名。" },
  { text: "系统会在开始时生成题目快照，后续题库修改不影响本次结果。" },
];

export function ExamStartPage() {
  const { examId = "1" } = useParams();
  const navigate = useNavigate();
  const { candidate } = useOutletContext<CandidateSessionContext>();
  const mutation = useMutation({
    mutationFn: () => startExam(examId, candidate?.id ?? 0),
    onSuccess: (result) => {
      navigate(`/exams/${examId}/taking?attemptId=${result.attempt_id}`);
    },
  });

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-8">
      <header className="flex flex-col gap-3">
        <ChapterNumber>CHAPTER 02 · EXAMS</ChapterNumber>
        <h1 className="font-display text-[28px] font-semibold italic tracking-[-0.04em] text-ink lg:text-[40px]">
          坐下来，开始考试。
        </h1>
        <p className="text-body-lg text-body">
          仔细阅读下面的规则，然后开始倒计时。开始后系统会立即生成题目快照。
        </p>
      </header>

      <section className="rounded-lg border border-hairline bg-surface-card p-6 lg:p-8">
        <ol className="flex flex-col gap-3 text-body italic text-ink">
          {RULES.map((rule, index) => (
            <li key={rule.text} className="flex gap-3">
              <span className="font-mono text-caption uppercase tracking-[0.16em] text-muted">
                {String(index + 1).padStart(2, "0")}
              </span>
              <span>{rule.text}</span>
            </li>
          ))}
        </ol>
      </section>

      {candidate ? (
        <div className="flex flex-col gap-3 rounded-lg border border-hairline bg-canvas p-5">
          <p className="text-caption uppercase tracking-[0.16em] text-muted">当前考试人</p>
          <NamePlate candidate={candidate as Candidate} />
        </div>
      ) : null}

      <div className="flex flex-col gap-3">
        {candidate ? (
          <Button
            type="button"
            size="lg"
            disabled={mutation.isPending}
            onClick={() => mutation.mutate()}
            className="self-start"
          >
            <ClipboardCheck data-icon="inline-start" />
            {mutation.isPending ? "正在开始…" : "开始考试"}
            <ArrowRight data-icon="inline-end" />
          </Button>
        ) : (
          <Button asChild size="lg" className="self-start">
            <Link to="/login">
              先登录考试人
              <ArrowRight data-icon="inline-end" />
            </Link>
          </Button>
        )}
        {mutation.isError ? (
          <p className="text-caption text-error" role="alert">
            开始考试失败，请确认考试仍处于发布状态。
          </p>
        ) : null}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no new errors. The `Candidate` type lives at `frontend/src/types/candidate.ts`; verify import path matches.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/ExamStartPage.tsx
git commit -m "feat(pages): 重写 ExamStartPage 加 chapter 头与米色规则卡"
```

---

## Task 7: Rewrite `RankingPage` (P1)

**Files:**
- Modify: `frontend/src/pages/RankingPage.tsx` (full rewrite)

- [ ] **Step 1: Rewrite the page**

Overwrite `frontend/src/pages/RankingPage.tsx`:

```tsx
import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { useParams } from "react-router-dom";

import { getExamRanking } from "@/api/exams";
import { SimpleDataTable } from "@/components/admin/SimpleDataTable";
import { ChapterNumber } from "@/components/editorial/ChapterNumber";
import { EmptyState } from "@/components/editorial/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import type { RankingRow } from "@/types/exam";

const columns: ColumnDef<RankingRow>[] = [
  {
    accessorKey: "rank",
    header: "RANK",
    cell: ({ row }) => (
      <span className="font-mono text-sm tabular-nums">
        {String(row.original.rank).padStart(2, "0")}
      </span>
    ),
    meta: { mobilePriority: "primary", mobileLabel: "RANK" },
  },
  {
    accessorKey: "candidate_name",
    header: "NAME",
    cell: ({ row }) => <span className="font-medium">{row.original.candidate_name}</span>,
    meta: { mobilePriority: "primary", mobileLabel: "NAME" },
  },
  {
    accessorKey: "department",
    header: "DEPT",
    cell: ({ row }) => row.original.department ?? "—",
    meta: { mobileLabel: "DEPT" },
  },
  {
    accessorKey: "score",
    header: "SCORE",
    cell: ({ row }) => (
      <span className="font-mono text-sm tabular-nums">
        {row.original.score} / {row.original.total_score}
      </span>
    ),
    meta: { mobilePriority: "primary", mobileLabel: "SCORE" },
  },
  {
    accessorKey: "total_score",
    header: "TOTAL",
    cell: ({ row }) => (
      <span className="font-mono text-sm tabular-nums">{row.original.total_score}</span>
    ),
    meta: { mobilePriority: false },
  },
];

const rowClassName = (row: RankingRow) => {
  if (row.rank === 1) return "bg-ink text-white hover:bg-ink";
  if (row.rank === 2 || row.rank === 3) return "bg-canvas";
  return undefined;
};

const mobileRowClassName = (row: RankingRow) => {
  if (row.rank === 1) return "border-l-4 border-ink bg-ink text-white";
  if (row.rank === 2) return "border-l-4 border-surface-card bg-surface-card";
  if (row.rank === 3) return "border-l-4 border-ink bg-canvas";
  return "border-l-4 border-hairline bg-canvas";
};

export function RankingPage() {
  const { examId = "1" } = useParams();
  const { data = [], isLoading } = useQuery({
    queryKey: ["ranking", examId],
    queryFn: () => getExamRanking(examId),
  });

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-3">
        <ChapterNumber>CHAPTER 03 · RESULTS</ChapterNumber>
        <h1 className="font-display text-[28px] font-semibold italic tracking-[-0.04em] text-ink lg:text-[40px]">
          谁在这场考试里名列前茅。
        </h1>
      </header>

      {isLoading ? (
        <div className="flex flex-col gap-2" aria-busy="true">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      ) : data.length ? (
        <SimpleDataTable
          columns={columns}
          data={data}
          rowKey={(row) => row.rank}
          rowClassName={rowClassName}
          mobileRowClassName={mobileRowClassName}
        />
      ) : (
        <EmptyState
          chapterLabel="CHAPTER 03 · RESULTS"
          title="还没有人交卷。"
          description="第一位交卷者将出现在这里。"
        />
      )}
      <p className="text-caption italic text-muted">
        第 1 名整行加黑；2-3 名白底；4+ 名白底 hairline 分割。手机端用左侧色条表达同样差异。
      </p>
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 0 errors. The page now uses `mobileRowClassName` to apply rank-specific Tailwind classes to the mobile card, which is the spec-faithful way to render the left color bar.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/RankingPage.tsx
git commit -m "feat(pages): 重写 RankingPage 加 chapter 头/排名配色/手机 card 左侧色条"
```

---

## Task 8: Rewrite `AdminLoginPage` (P1, full black right column desktop layout)

**Files:**
- Modify: `frontend/src/pages/admin/AdminLoginPage.tsx` (full rewrite)

- [ ] **Step 1: Rewrite the page**

Overwrite `frontend/src/pages/admin/AdminLoginPage.tsx`:

```tsx
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { ShieldCheck } from "lucide-react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";

import { loginAdmin } from "@/api/auth";
import { Button } from "@/components/ui/button";
import { ChapterNumber } from "@/components/editorial/ChapterNumber";
import { Wordmark } from "@/components/editorial/Wordmark";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const schema = z.object({
  username: z.string().min(1, "请输入管理员账号"),
  password: z.string().min(1, "请输入密码"),
});

type AdminLoginForm = z.infer<typeof schema>;

export function AdminLoginPage() {
  const navigate = useNavigate();
  const form = useForm<AdminLoginForm>({
    resolver: zodResolver(schema),
    defaultValues: { username: "", password: "" },
  });
  const mutation = useMutation({
    mutationFn: loginAdmin,
    onSuccess: () => navigate("/admin/dashboard"),
  });

  return (
    <main className="grid min-h-screen grid-cols-1 lg:grid-cols-2">
      {/* Left: form column */}
      <section className="flex flex-col gap-10 px-6 py-10 lg:px-16 lg:py-16">
        <Wordmark tone="dark" subtitle="— admin console" />
        <div className="flex flex-1 flex-col justify-center gap-8">
          <header className="flex flex-col gap-3">
            <ChapterNumber>CHAPTER 00 · ADMIN</ChapterNumber>
            <h1 className="font-display text-[40px] font-semibold italic tracking-[-0.04em] text-ink lg:text-[64px]">
              安静地工作。
            </h1>
            <p className="text-body-lg text-body">
              管理员登录后可访问题库、考试配置与所有报表。
            </p>
          </header>

          <form
            className="flex max-w-md flex-col gap-4 rounded-lg border border-hairline bg-surface-card p-6 lg:p-8"
            onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
          >
            <div className="flex flex-col gap-2">
              <Label htmlFor="username">账号 · Username</Label>
              <Input id="username" autoComplete="username" {...form.register("username")} />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="password">密码 · Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                {...form.register("password")}
              />
            </div>
            <Button type="submit" size="lg" disabled={mutation.isPending}>
              <ShieldCheck data-icon="inline-start" />
              登录管理后台
            </Button>
            {mutation.isError ? (
              <p className="text-caption text-error" role="alert">
                账号或密码不正确。
              </p>
            ) : null}
          </form>
        </div>
      </section>

      {/* Right: dark column with 8% alpha radial dot pattern */}
      <aside
        aria-hidden="true"
        className="relative hidden bg-footer lg:block"
        style={{
          backgroundImage:
            "radial-gradient(rgba(255,255,255,0.08) 1px, transparent 1px)",
          backgroundSize: "24px 24px",
        }}
      >
        <div className="absolute inset-0 flex flex-col items-start justify-end gap-3 p-16 text-footer-soft">
          <p className="text-caption uppercase tracking-[0.18em]">ADMIN CONSOLE</p>
          <p className="max-w-sm font-display text-[28px] font-semibold italic tracking-[-0.04em] text-white">
            所有考试、题库、报表 — 一处掌控。
          </p>
        </div>
      </aside>
    </main>
  );
}
```

- [ ] **Step 2: Type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no new errors. `Wordmark` from Phase 3 must accept `tone` (`"dark" | "light"`) and `subtitle` props. If `Wordmark` does not yet have these props, the build will surface a TS error — STOP and add them per Phase 3 spec before continuing.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/admin/AdminLoginPage.tsx
git commit -m "feat(admin): 重写登录页加桌面端全黑右列 + 0.08 alpha 白色点阵"
```

---

## Task 9: Rewrite `AdminDashboardPage` (P1, 4 MetricCards + activity list)

**Files:**
- Modify: `frontend/src/pages/admin/AdminDashboardPage.tsx` (full rewrite)

- [ ] **Step 1: Rewrite the page**

Overwrite `frontend/src/pages/admin/AdminDashboardPage.tsx`:

```tsx
import { useQuery } from "@tanstack/react-query";

import { getAdminExams } from "@/api/exams";
import { getAdminQuestions } from "@/api/questions";
import { getAbsentCandidates, getScoreReport } from "@/api/reports";
import { MetricCard } from "@/components/admin/MetricCard";
import { ChapterNumber } from "@/components/editorial/ChapterNumber";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

type ActivityTone = "success" | "warning" | "error";

interface ActivityItem {
  id: string;
  title: string;
  caption: string;
  when: string;
  tone: ActivityTone;
}

const TONE_DOT: Record<ActivityTone, string> = {
  success: "bg-success",
  warning: "bg-warning",
  error: "bg-error",
};

function ActivityRow({ item }: { item: ActivityItem }) {
  return (
    <li className="flex items-center gap-4 border-b border-hairline-soft py-3 last:border-b-0">
      <span className={cn("h-1.5 w-1.5 rounded-pill", TONE_DOT[item.tone])} aria-hidden="true" />
      <div className="flex flex-1 flex-col gap-1">
        <span className="text-body font-medium text-ink">{item.title}</span>
        <span className="text-caption italic text-muted">{item.caption}</span>
      </div>
      <span className="text-caption text-muted">{item.when}</span>
    </li>
  );
}

export function AdminDashboardPage() {
  const questions = useQuery({ queryKey: ["admin-questions"], queryFn: getAdminQuestions });
  const exams = useQuery({ queryKey: ["admin-exams"], queryFn: getAdminExams });
  const scores = useQuery({ queryKey: ["score-report"], queryFn: getScoreReport });
  const absent = useQuery({ queryKey: ["absent-candidates"], queryFn: getAbsentCandidates });

  const liveExams = (exams.data ?? []).filter(
    (e) => e.status === "active" || e.status === "live",
  ).length;

  const activity: ActivityItem[] = [
    ...(scores.data ?? []).slice(0, 5).map((s) => ({
      id: `score-${s.candidate_name}-${s.exam_title}`,
      title: `${s.candidate_name} 提交了 ${s.exam_title}`,
      caption: `得分 ${s.score} / ${s.total_score}`,
      when: s.submitted_at ?? "—",
      tone: "success" as const,
    })),
    ...(absent.data ?? []).slice(0, 5).map((a) => ({
      id: `absent-${a.candidate_id}-${a.exam_group ?? ""}`,
      title: `${a.name} 尚未参加考试`,
      caption: a.exam_group ?? a.department ?? "—",
      when: "未到",
      tone: "warning" as const,
    })),
  ];

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-3">
        <ChapterNumber>CHAPTER 01 · OVERVIEW</ChapterNumber>
        <h1 className="font-display text-[28px] font-semibold italic tracking-[-0.04em] text-ink lg:text-[40px]">
          一切就绪。
        </h1>
        <p className="text-body-lg text-body">最近一次刷新 · {new Date().toLocaleString("zh-CN")}</p>
      </header>

      <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="QUESTIONS · 题库"
          value={questions.data?.length ?? 0}
          unit="题"
          caption="所有状态的题目合计"
        />
        <MetricCard
          label="EXAMS LIVE · 进行中"
          value={liveExams}
          unit="场"
          tone="success"
          caption="status 为 active / live"
        />
        <MetricCard
          label="SUBMITTED · 已提交"
          value={scores.data?.length ?? 0}
          unit="次"
          caption="所有考试累计提交次数"
        />
        <MetricCard
          label="ABSENT · 未参加"
          value={absent.data?.length ?? 0}
          unit="人"
          tone="warning"
          caption="应考但未提交人员"
        />
      </section>

      <section className="flex flex-col gap-4 rounded-lg border border-hairline bg-canvas p-6 shadow-card lg:p-7">
        <header className="flex flex-col gap-1">
          <p className="text-caption uppercase tracking-[0.16em] text-muted">ACTIVITY · 最近活动</p>
          <h2 className="font-display text-[20px] font-semibold tracking-[-0.04em] text-ink">
            提交与缺席
          </h2>
        </header>
        {questions.isLoading || exams.isLoading || scores.isLoading || absent.isLoading ? (
          <div className="flex flex-col gap-2" aria-busy="true">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : activity.length ? (
          <ul className="flex flex-col">
            {activity.map((item) => (
              <ActivityRow key={item.id} item={item} />
            ))}
          </ul>
        ) : (
          <p className="text-caption italic text-muted">暂无活动记录。</p>
        )}
      </section>
    </div>
  );
}
```

- [ ] **Step 2: Type-check and lint**

```bash
cd frontend && npx tsc --noEmit && npm run lint
```

Expected: 0 errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/admin/AdminDashboardPage.tsx
git commit -m "feat(admin): 重写仪表盘加 4 MetricCard 与最近活动列表"
```

---

## Task 10: Rewrite `ExamEditPage` (P1, with JSON editor + candidate strip)

**Files:**
- Modify: `frontend/src/pages/admin/ExamEditPage.tsx` (full rewrite)

- [ ] **Step 1: Rewrite the page**

Overwrite `frontend/src/pages/admin/ExamEditPage.tsx`:

```tsx
import { zodResolver } from "@hookform/resolvers/zod";
import { ChevronDown, Save, X } from "lucide-react";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { Link, useParams } from "react-router-dom";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { ChapterNumber } from "@/components/editorial/ChapterNumber";
import { StatusPill } from "@/components/editorial/StatusPill";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

const STATUS_OPTIONS = [
  { value: "draft", label: "DRAFT · 草稿" },
  { value: "active", label: "LIVE · 进行中" },
  { value: "archived", label: "ENDED · 已结束" },
] as const;

const schema = z.object({
  title: z.string().min(1, "请输入考试名称"),
  duration_minutes: z.coerce.number().int().min(1, "时长必须 ≥ 1 分钟"),
  status: z.enum(["draft", "active", "archived"]),
  question_rule_json: z.string().min(2, "抽题规则不能为空"),
});

type ExamEditForm = z.infer<typeof schema>;

function StatusDropdown({
  value,
  onChange,
}: {
  value: ExamEditForm["status"];
  onChange: (next: ExamEditForm["status"]) => void;
}) {
  const [open, setOpen] = useState(false);
  const current = STATUS_OPTIONS.find((s) => s.value === value) ?? STATUS_OPTIONS[0]!;
  return (
    <div className="relative">
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((prev) => !prev)}
        className="flex h-11 w-full items-center justify-between gap-2 rounded-md border border-hairline bg-canvas px-4 text-body text-ink hover:border-ink"
      >
        <span className="flex items-center gap-2">
          <StatusPill status={current.value} />
          {current.label}
        </span>
        <ChevronDown className="h-4 w-4 text-muted" data-icon="inline-end" />
      </button>
      {open ? (
        <ul
          role="listbox"
          className="absolute z-20 mt-1 w-full overflow-hidden rounded-md border border-hairline bg-surface-elev shadow-pop"
        >
          {STATUS_OPTIONS.map((option) => (
            <li key={option.value}>
              <button
                type="button"
                role="option"
                aria-selected={option.value === value}
                onClick={() => {
                  onChange(option.value);
                  setOpen(false);
                }}
                className={cn(
                  "flex w-full items-center gap-2 px-4 py-2 text-left text-body hover:bg-surface-card",
                  option.value === value && "bg-surface-card",
                )}
              >
                <StatusPill status={option.value} />
                {option.label}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

export function ExamEditPage() {
  const { examId } = useParams();
  const form = useForm<ExamEditForm>({
    resolver: zodResolver(schema),
    defaultValues: {
      title: "临时考试",
      duration_minutes: 60,
      status: "draft",
      question_rule_json: JSON.stringify(
        { counts: [5, 5, 2], total_score: 100 },
        null,
        2,
      ),
    },
  });

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="flex flex-col gap-3">
          <ChapterNumber>CHAPTER 02 · EXAMS</ChapterNumber>
          <h1 className="font-display text-[28px] font-semibold italic tracking-[-0.04em] text-ink lg:text-[40px]">
            编辑考试 #{examId ?? "—"}
          </h1>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="outline" size="sm">
            <Link to="/admin/exams">
              <X data-icon="inline-start" />
              取消
            </Link>
          </Button>
          <Button
            type="button"
            size="sm"
            onClick={form.handleSubmit(() => undefined)}
          >
            <Save data-icon="inline-start" />
            保存配置
          </Button>
        </div>
      </header>

      <section className="grid gap-6 rounded-lg border border-hairline bg-canvas p-6 shadow-card lg:grid-cols-2 lg:p-8">
        <div className="flex flex-col gap-2">
          <Label htmlFor="title">考试名称 · Title</Label>
          <Input id="title" {...form.register("title")} />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="duration_minutes">时长（分钟）· Duration</Label>
          <Input
            id="duration_minutes"
            type="number"
            min={1}
            {...form.register("duration_minutes", { valueAsNumber: true })}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="status">状态 · Status</Label>
          <Controller
            control={form.control}
            name="status"
            render={({ field }) => (
              <StatusDropdown value={field.value} onChange={field.onChange} />
            )}
          />
        </div>
        <div className="flex flex-col gap-2 lg:col-span-2">
          <Label htmlFor="question_rule_json">抽题规则 · JSON</Label>
          <textarea
            id="question_rule_json"
            rows={8}
            spellCheck={false}
            className="w-full resize-y rounded-md border border-hairline bg-footer p-4 font-mono text-[12px] leading-relaxed text-footer-soft focus:border-ink focus:outline-none"
            {...form.register("question_rule_json")}
          />
        </div>
        <div className="flex flex-col gap-3 rounded-md bg-surface-card p-4 lg:col-span-2 md:flex-row md:items-center md:justify-between">
          <div className="flex flex-col gap-1">
            <span className="text-caption uppercase tracking-[0.16em] text-muted">CANDIDATES</span>
            <span className="text-body text-ink">应考人员 · 在此页维护本场名单</span>
          </div>
          <Button asChild variant="outline" size="sm">
            <Link to={`/admin/exams/${examId ?? "1"}/candidates`}>管理应考</Link>
          </Button>
        </div>
      </section>
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 0 errors. `StatusPill` from Phase 3 must accept the values `"draft" | "active" | "live" | "ended" | "archived"`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/admin/ExamEditPage.tsx
git commit -m "feat(admin): 重写考试编辑页加 chapter 头/状态 dropdown/JSON 编辑器"
```

---

## Task 11: Rewrite `QuestionImportPage` (P1)

**Files:**
- Modify: `frontend/src/pages/admin/QuestionImportPage.tsx` (full rewrite)

- [ ] **Step 1: Rewrite the page**

Overwrite `frontend/src/pages/admin/QuestionImportPage.tsx`:

```tsx
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FileUp } from "lucide-react";

import { importQuestions } from "@/api/imports";
import { Button } from "@/components/ui/button";
import { ChapterNumber } from "@/components/editorial/ChapterNumber";
import { Input } from "@/components/ui/input";
import type { ImportFailure } from "@/types/imports";

export function QuestionImportPage() {
  const [file, setFile] = useState<File | null>(null);
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: importQuestions,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-questions"] });
    },
  });

  return (
    <div className="flex max-w-3xl flex-col gap-8">
      <header className="flex flex-col gap-3">
        <ChapterNumber>CHAPTER 03 · LIBRARY</ChapterNumber>
        <h1 className="font-display text-[28px] font-semibold tracking-[-0.04em] text-ink lg:text-[40px]">
          题库导入
        </h1>
        <p className="text-body-lg text-body">
          仅支持标准 Excel（.xlsx / .xls），不解析 Word。导入前请先下载模板，按列填写题目。
        </p>
      </header>

      <section className="flex flex-col gap-5 rounded-lg border border-hairline bg-surface-card p-6 lg:p-8">
        <p className="text-caption italic text-muted">
          模板格式见 docs/imports/questions.md · Template format lives in the docs.
        </p>

        <Input
          type="file"
          accept=".xlsx,.xls"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          aria-label="选择 Excel 文件"
        />

        <Button
          type="button"
          size="lg"
          className="self-start"
          disabled={!file || mutation.isPending}
          onClick={() => file && mutation.mutate(file)}
        >
          <FileUp data-icon="inline-start" />
          {mutation.isPending ? "正在导入…" : "上传并校验"}
        </Button>
      </section>

      {mutation.data ? (
        <section className="flex flex-col gap-3 rounded-lg border border-hairline bg-canvas p-6 shadow-card">
          <p className="text-body text-ink">
            成功 <span className="font-mono">{mutation.data.success_count}</span> 行，
            失败 <span className="font-mono text-error">{mutation.data.failed_count}</span> 行
          </p>
          {mutation.data.failures.length ? (
            <ul className="flex flex-col gap-1 border-t border-hairline-soft pt-3 text-caption text-muted">
              {mutation.data.failures.map((failure: ImportFailure) => (
                <li key={failure.row_number} className="font-mono">
                  行 {failure.row_number} · {failure.reason}
                </li>
              ))}
            </ul>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
```

- [ ] **Step 2: Type-check and lint**

```bash
cd frontend && npx tsc --noEmit && npm run lint
```

Expected: 0 errors. The plan keeps the implementation API-free: the template is referenced via a text caption pointing to `docs/imports/questions.md` rather than a backend link, since the current backend has no template-download endpoint.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/admin/QuestionImportPage.tsx
git commit -m "feat(admin): 重写题库导入页加 chapter 头与结果明细"
```

---

## Task 12: Rewrite `QuestionListPage` (admin, P2)

**Files:**
- Modify: `frontend/src/pages/admin/QuestionListPage.tsx` (full rewrite)

- [ ] **Step 1: Rewrite the page**

Overwrite `frontend/src/pages/admin/QuestionListPage.tsx`:

```tsx
import type { ColumnDef } from "@tanstack/react-table";
import { ArrowUpRight } from "lucide-react";
import { Link } from "react-router-dom";

import { getAdminQuestions } from "@/api/questions";
import { ReportPage } from "@/components/admin/ReportPage";
import { Button } from "@/components/ui/button";
import type { Question } from "@/types/question";

const columns: ColumnDef<Question>[] = [
  {
    accessorKey: "id",
    header: "ID",
    cell: ({ row }) => <span className="font-mono text-sm">{row.original.id}</span>,
    meta: { mobilePriority: false },
  },
  {
    accessorKey: "question_type",
    header: "TYPE",
    meta: { mobileLabel: "TYPE" },
  },
  {
    accessorKey: "stem",
    header: "STEM",
    cell: ({ row }) => (
      <span className="line-clamp-1 max-w-md">{row.original.stem}</span>
    ),
    meta: { mobilePriority: "primary", mobileLabel: "STEM" },
  },
  {
    accessorKey: "score",
    header: "SCORE",
    cell: ({ row }) => (
      <span className="font-mono text-sm tabular-nums">{row.original.score}</span>
    ),
    meta: { mobileLabel: "SCORE" },
  },
  {
    accessorKey: "status",
    header: "STATUS",
    meta: { mobileLabel: "STATUS" },
  },
];

export function QuestionListPage() {
  return (
    <ReportPage
      title="题库管理"
      chapterLabel="CHAPTER 03 · LIBRARY"
      description="所有题目的列表与状态。点击右上「导入题库」批量上传 Excel。"
      queryKey="admin-questions"
      queryFn={getAdminQuestions}
      columns={columns}
      actions={
        <Button asChild size="sm">
          <Link to="/admin/questions/import">
            导入题库
            <ArrowUpRight data-icon="inline-end" />
          </Link>
        </Button>
      }
    />
  );
}
```

- [ ] **Step 2: Type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 0 errors. `ReportPage` already supports `chapterLabel` / `description` / `actions` per Task 4.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/admin/QuestionListPage.tsx
git commit -m "feat(admin): 重写题库列表页加 chapter 头/导入按钮/手机 card list"
```

---

## Task 13: Rewrite admin `ExamListPage` (P2)

**Files:**
- Modify: `frontend/src/pages/admin/ExamListPage.tsx` (full rewrite)

- [ ] **Step 1: Rewrite the page**

Overwrite `frontend/src/pages/admin/ExamListPage.tsx`:

```tsx
import type { ColumnDef } from "@tanstack/react-table";
import { ArrowUpRight } from "lucide-react";
import { Link } from "react-router-dom";

import { getAdminExams } from "@/api/exams";
import { ReportPage } from "@/components/admin/ReportPage";
import { Button } from "@/components/ui/button";
import { StatusPill } from "@/components/editorial/StatusPill";
import type { Exam } from "@/types/exam";

const columns: ColumnDef<Exam>[] = [
  {
    accessorKey: "id",
    header: "ID",
    cell: ({ row }) => <span className="font-mono text-sm">{row.original.id}</span>,
    meta: { mobilePriority: false },
  },
  {
    accessorKey: "title",
    header: "TITLE",
    cell: ({ row }) => (
      <Link
        to={`/admin/exams/${row.original.id}/edit`}
        className="font-medium text-ink underline-offset-4 hover:underline"
      >
        {row.original.title}
      </Link>
    ),
    meta: { mobilePriority: "primary", mobileLabel: "TITLE" },
  },
  {
    accessorKey: "duration_minutes",
    header: "DURATION",
    cell: ({ row }) => (
      <span className="font-mono text-sm tabular-nums">{row.original.duration_minutes} 分</span>
    ),
    meta: { mobileLabel: "DURATION" },
  },
  {
    accessorKey: "status",
    header: "STATUS",
    cell: ({ row }) => <StatusPill status={row.original.status} />,
    meta: { mobilePriority: "primary", mobileLabel: "STATUS" },
  },
];

export function AdminExamListPage() {
  return (
    <ReportPage
      title="考试配置"
      chapterLabel="CHAPTER 02 · EXAMS"
      description="所有考试的配置入口。点击考试名进入编辑页。"
      queryKey="admin-exams"
      queryFn={getAdminExams}
      columns={columns}
      actions={
        <Button asChild size="sm">
          <Link to="/admin/exams/1/edit">
            新建考试
            <ArrowUpRight data-icon="inline-end" />
          </Link>
        </Button>
      }
    />
  );
}
```

- [ ] **Step 2: Type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/admin/ExamListPage.tsx
git commit -m "feat(admin): 重写考试配置列表加 chapter 头/状态印章/手机 card list"
```

---

## Task 14: Rewrite `CandidateImportPage` (P2, same form as QuestionImportPage)

**Files:**
- Modify: `frontend/src/pages/admin/CandidateImportPage.tsx` (full rewrite)

- [ ] **Step 1: Rewrite the page**

Overwrite `frontend/src/pages/admin/CandidateImportPage.tsx`:

```tsx
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FileUp } from "lucide-react";
import { useParams } from "react-router-dom";

import { importCandidates } from "@/api/imports";
import { Button } from "@/components/ui/button";
import { ChapterNumber } from "@/components/editorial/ChapterNumber";
import { Input } from "@/components/ui/input";
import type { ImportFailure } from "@/types/imports";

export function CandidateImportPage() {
  const { examId = "1" } = useParams();
  const [file, setFile] = useState<File | null>(null);
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (selected: File) => importCandidates(examId, selected),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["absent-candidates"] });
    },
  });

  return (
    <div className="flex max-w-3xl flex-col gap-8">
      <header className="flex flex-col gap-3">
        <ChapterNumber>CHAPTER 02 · EXAMS</ChapterNumber>
        <h1 className="font-display text-[28px] font-semibold tracking-[-0.04em] text-ink lg:text-[40px]">
          应考人员导入
        </h1>
        <p className="text-body-lg text-body">
          未参加人员名单 = 应考人员 − 已提交考试人员。导入前请按模板填写。
        </p>
      </header>

      <section className="flex flex-col gap-5 rounded-lg border border-hairline bg-surface-card p-6 lg:p-8">
        <Input
          type="file"
          accept=".xlsx,.xls"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          aria-label="选择 Excel 文件"
        />
        <Button
          type="button"
          size="lg"
          className="self-start"
          disabled={!file || mutation.isPending}
          onClick={() => file && mutation.mutate(file)}
        >
          <FileUp data-icon="inline-start" />
          {mutation.isPending ? "正在导入…" : "上传应考人员"}
        </Button>
      </section>

      {mutation.data ? (
        <section className="flex flex-col gap-3 rounded-lg border border-hairline bg-canvas p-6 shadow-card">
          <p className="text-body text-ink">
            成功 <span className="font-mono">{mutation.data.success_count}</span> 行，
            失败 <span className="font-mono text-error">{mutation.data.failed_count}</span> 行
          </p>
          {mutation.data.failures.length ? (
            <ul className="flex flex-col gap-1 border-t border-hairline-soft pt-3 text-caption text-muted">
              {mutation.data.failures.map((failure: ImportFailure) => (
                <li key={failure.row_number} className="font-mono">
                  行 {failure.row_number} · {failure.reason}
                </li>
              ))}
            </ul>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/admin/CandidateImportPage.tsx
git commit -m "feat(admin): 重写应考名单导入页加 chapter 头与结果明细"
```

---

## Task 15: Batch-rewrite the 4 report pages (P2, add `meta.mobilePriority`)

**Files:**
- Modify: `frontend/src/pages/admin/ScoreReportPage.tsx`
- Modify: `frontend/src/pages/admin/QuestionAccuracyPage.tsx`
- Modify: `frontend/src/pages/admin/WrongQuestionPage.tsx`
- Modify: `frontend/src/pages/admin/AbsentCandidatePage.tsx`

- [ ] **Step 1: Rewrite `ScoreReportPage.tsx`**

Overwrite `frontend/src/pages/admin/ScoreReportPage.tsx`:

```tsx
import type { ColumnDef } from "@tanstack/react-table";

import { getScoreReport } from "@/api/reports";
import { ReportPage } from "@/components/admin/ReportPage";
import type { ScoreReportRow } from "@/types/report";

const columns: ColumnDef<ScoreReportRow>[] = [
  {
    accessorKey: "candidate_name",
    header: "NAME",
    cell: ({ row }) => <span className="font-medium">{row.original.candidate_name}</span>,
    meta: { mobilePriority: "primary", mobileLabel: "NAME" },
  },
  {
    accessorKey: "employee_no",
    header: "EMP NO",
    cell: ({ row }) => <span className="font-mono text-sm">{row.original.employee_no ?? "—"}</span>,
    meta: { mobileLabel: "EMP NO" },
  },
  {
    accessorKey: "department",
    header: "DEPT",
    cell: ({ row }) => row.original.department ?? "—",
    meta: { mobileLabel: "DEPT" },
  },
  {
    accessorKey: "exam_title",
    header: "EXAM",
    meta: { mobileLabel: "EXAM" },
  },
  {
    accessorKey: "score",
    header: "SCORE",
    cell: ({ row }) => (
      <span className="font-mono text-sm tabular-nums">
        {row.original.score} / {row.original.total_score}
      </span>
    ),
    meta: { mobilePriority: "primary", mobileLabel: "SCORE" },
  },
  {
    accessorKey: "total_score",
    header: "TOTAL",
    cell: ({ row }) => (
      <span className="font-mono text-sm tabular-nums">{row.original.total_score}</span>
    ),
    meta: { mobilePriority: false },
  },
];

export function ScoreReportPage() {
  return (
    <ReportPage
      title="个人成绩"
      chapterLabel="CHAPTER 04 · REPORTS"
      description="每次考试的个人提交结果。"
      queryKey="score-report"
      queryFn={getScoreReport}
      columns={columns}
    />
  );
}
```

- [ ] **Step 2: Rewrite `QuestionAccuracyPage.tsx`**

Overwrite `frontend/src/pages/admin/QuestionAccuracyPage.tsx`:

```tsx
import type { ColumnDef } from "@tanstack/react-table";

import { getQuestionAccuracy } from "@/api/reports";
import { ReportPage } from "@/components/admin/ReportPage";
import type { QuestionAccuracyRow } from "@/types/report";

const columns: ColumnDef<QuestionAccuracyRow>[] = [
  {
    accessorKey: "question_id",
    header: "QID",
    cell: ({ row }) => <span className="font-mono text-sm">{row.original.question_id}</span>,
    meta: { mobileLabel: "QID" },
  },
  {
    accessorKey: "stem",
    header: "STEM",
    cell: ({ row }) => <span className="line-clamp-1 max-w-md">{row.original.stem}</span>,
    meta: { mobilePriority: "primary", mobileLabel: "STEM" },
  },
  {
    accessorKey: "correct_count",
    header: "CORRECT",
    cell: ({ row }) => (
      <span className="font-mono text-sm tabular-nums">{row.original.correct_count}</span>
    ),
    meta: { mobileLabel: "CORRECT" },
  },
  {
    accessorKey: "total_count",
    header: "TOTAL",
    cell: ({ row }) => (
      <span className="font-mono text-sm tabular-nums">{row.original.total_count}</span>
    ),
    meta: { mobileLabel: "TOTAL" },
  },
  {
    accessorKey: "accuracy_rate",
    header: "RATE",
    cell: ({ row }) => {
      const rate = row.original.accuracy_rate;
      const pct = rate > 1 ? rate : rate * 100;
      return (
        <span className="font-mono text-sm tabular-nums">
          {pct.toFixed(pct >= 100 ? 0 : 1)}%
        </span>
      );
    },
    meta: { mobilePriority: "primary", mobileLabel: "RATE" },
  },
];

export function QuestionAccuracyPage() {
  return (
    <ReportPage
      title="题目正确率"
      chapterLabel="CHAPTER 04 · REPORTS"
      description="每道题被答对的比率。数字越高表示越简单。"
      queryKey="question-accuracy"
      queryFn={getQuestionAccuracy}
      columns={columns}
    />
  );
}
```

- [ ] **Step 3: Rewrite `WrongQuestionPage.tsx`**

Overwrite `frontend/src/pages/admin/WrongQuestionPage.tsx`:

```tsx
import type { ColumnDef } from "@tanstack/react-table";

import { getWrongQuestions } from "@/api/reports";
import { ReportPage } from "@/components/admin/ReportPage";
import type { WrongQuestionRow } from "@/types/report";

const columns: ColumnDef<WrongQuestionRow>[] = [
  {
    accessorKey: "question_id",
    header: "QID",
    cell: ({ row }) => <span className="font-mono text-sm">{row.original.question_id}</span>,
    meta: { mobileLabel: "QID" },
  },
  {
    accessorKey: "stem",
    header: "STEM",
    cell: ({ row }) => <span className="line-clamp-1 max-w-md">{row.original.stem}</span>,
    meta: { mobilePriority: "primary", mobileLabel: "STEM" },
  },
  {
    accessorKey: "wrong_count",
    header: "WRONG",
    cell: ({ row }) => (
      <span className="font-mono text-sm tabular-nums text-error">{row.original.wrong_count}</span>
    ),
    meta: { mobilePriority: "primary", mobileLabel: "WRONG" },
  },
  {
    accessorKey: "category_1",
    header: "CAT 1",
    cell: ({ row }) => row.original.category_1 ?? "—",
    meta: { mobileLabel: "CAT 1" },
  },
  {
    accessorKey: "category_2",
    header: "CAT 2",
    cell: ({ row }) => row.original.category_2 ?? "—",
    meta: { mobileLabel: "CAT 2" },
  },
];

export function WrongQuestionPage() {
  return (
    <ReportPage
      title="错题排行"
      chapterLabel="CHAPTER 04 · REPORTS"
      description="答错次数最多的题目。优先用于复盘与培训。"
      queryKey="wrong-questions"
      queryFn={getWrongQuestions}
      columns={columns}
    />
  );
}
```

- [ ] **Step 4: Rewrite `AbsentCandidatePage.tsx`**

Overwrite `frontend/src/pages/admin/AbsentCandidatePage.tsx`:

```tsx
import type { ColumnDef } from "@tanstack/react-table";

import { getAbsentCandidates } from "@/api/reports";
import { ReportPage } from "@/components/admin/ReportPage";
import type { AbsentCandidateRow } from "@/types/report";

const columns: ColumnDef<AbsentCandidateRow>[] = [
  {
    accessorKey: "candidate_id",
    header: "CID",
    cell: ({ row }) => <span className="font-mono text-sm">{row.original.candidate_id}</span>,
    meta: { mobilePriority: false },
  },
  {
    accessorKey: "name",
    header: "NAME",
    cell: ({ row }) => <span className="font-medium">{row.original.name}</span>,
    meta: { mobilePriority: "primary", mobileLabel: "NAME" },
  },
  {
    accessorKey: "employee_no",
    header: "EMP NO",
    cell: ({ row }) => <span className="font-mono text-sm">{row.original.employee_no ?? "—"}</span>,
    meta: { mobileLabel: "EMP NO" },
  },
  {
    accessorKey: "department",
    header: "DEPT",
    cell: ({ row }) => row.original.department ?? "—",
    meta: { mobileLabel: "DEPT" },
  },
  {
    accessorKey: "exam_group",
    header: "GROUP",
    cell: ({ row }) => row.original.exam_group ?? "—",
    meta: { mobilePriority: "primary", mobileLabel: "GROUP" },
  },
];

export function AbsentCandidatePage() {
  return (
    <ReportPage
      title="未参加人员"
      chapterLabel="CHAPTER 04 · REPORTS"
      description="应考但未提交考试的人员列表。需补考时使用。"
      queryKey="absent-candidates"
      queryFn={getAbsentCandidates}
      columns={columns}
    />
  );
}
```

- [ ] **Step 5: Type-check and lint**

```bash
cd frontend && npx tsc --noEmit && npm run lint
```

Expected: 0 errors, 0 warnings.

- [ ] **Step 6: Verify all 4 reports use the new chapter/description pattern visually**

```bash
cd frontend && grep -l "ReportPage" src/pages/admin/*.tsx
```

Expected: 4 lines (ScoreReportPage, QuestionAccuracyPage, WrongQuestionPage, AbsentCandidatePage).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/admin/ScoreReportPage.tsx frontend/src/pages/admin/QuestionAccuracyPage.tsx frontend/src/pages/admin/WrongQuestionPage.tsx frontend/src/pages/admin/AbsentCandidatePage.tsx
git commit -m "feat(admin): 4 报表页接入 ReportPage 容器 + mobilePriority 标记"
```

---

## Task 16: End-to-end verification

**Files:**
- None (verification only)

- [ ] **Step 1: Type-check the whole frontend**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 2: Run all unit tests**

```bash
cd frontend && npx vitest run
```

Expected: all tests pass (including the 14 tests added in Tasks 2–4 plus the 0 from Task 1 hook and any pre-existing tests).

- [ ] **Step 3: Lint**

```bash
cd frontend && npm run lint
```

Expected: 0 warnings.

- [ ] **Step 4: Format check**

```bash
cd frontend && npm run format:check
```

Expected: 0 diff. If there are diffs, run `npm run format` once and re-check.

- [ ] **Step 5: Production build**

```bash
cd frontend && npm run build
```

Expected: build succeeds.

- [ ] **Step 6: Smoke-verify route reachability**

Start the dev server in background and curl the new pages to confirm none 500:

```bash
cd frontend && (npm run dev &) && sleep 6 && for path in /exams /exams/1/start /exams/1/ranking /admin/login /admin/dashboard /admin/exams/1/edit /admin/questions/import /admin/questions /admin/exams /admin/exams/1/candidates /admin/reports/scores /admin/reports/questions /admin/reports/wrong /admin/reports/absent; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:5173$path")
  echo "$path → $code"
done
```

Expected: all 200 (or 304). Then `pkill -f "vite"`.

- [ ] **Step 7: Optional — Playwright screenshot of key pages**

If Playwright is installed, navigate to `/exams`, `/exams/1/ranking`, `/admin/dashboard`, `/admin/reports/scores` at desktop (1280×800) and mobile (390×844) and capture screenshots. Verify the visual:

- ExamListPage: 2-column grid on desktop, 1-column on mobile
- RankingPage: rank 1 row inverted (black bg, white text)
- AdminDashboard: 4 MetricCards in a row at lg breakpoint
- ScoreReportPage: 5 columns on desktop; on mobile, only NAME / SCORE visible

- [ ] **Step 8: Commit verification (no changes expected)**

```bash
git status
```

Expected: clean working tree.

If any step fails, fix the offending page and re-run from that step.

---

## Done criteria (Phase 6 complete when)

- All 14 pages (`pages/ExamListPage.tsx`, `pages/ExamStartPage.tsx`, `pages/RankingPage.tsx`, `pages/admin/AdminLoginPage.tsx`, `pages/admin/AdminDashboardPage.tsx`, `pages/admin/ExamEditPage.tsx`, `pages/admin/QuestionImportPage.tsx`, `pages/admin/QuestionListPage.tsx`, `pages/admin/ExamListPage.tsx`, `pages/admin/CandidateImportPage.tsx`, `pages/admin/ScoreReportPage.tsx`, `pages/admin/QuestionAccuracyPage.tsx`, `pages/admin/WrongQuestionPage.tsx`, `pages/admin/AbsentCandidatePage.tsx`) follow the chapter + italic h1 + 米色卡 pattern.
- `components/admin/MetricCard.tsx` exists with `tone` prop, covered by 6 unit tests.
- `components/admin/SimpleDataTable.tsx` branches between desktop table and mobile card list, with `meta.mobilePriority` and `meta.mobileLabel`, covered by 4 unit tests.
- `components/admin/ReportPage.tsx` renders chapter + italic h1 + description + optional `actions`, with loading state, covered by 4 unit tests.
- `lib/useMediaQuery.ts` exists with `MD.md` / `MD.lg` constants.
- All 14 new Vitest tests pass.
- `npx tsc --noEmit` passes.
- `npm run lint` passes (0 warnings).
- `npm run format:check` passes (0 diff).
- `npm run build` succeeds.
- All API calls (`getActiveExams`, `getExamRanking`, `startExam`, `getAdminExams`, `getAdminQuestions`, `getScoreReport`, `getQuestionAccuracy`, `getWrongQuestions`, `getAbsentCandidates`, `importQuestions`, `importCandidates`, `loginAdmin`) are unchanged in their argument and return types.

---

## Out of scope for Phase 6 (deferred)

These items are mentioned in the design spec but explicitly NOT part of Phase 6:

- Phase 7 work: empty/loading states on every page (we add `EmptyState` to 3 pages and `Skeleton` to 2, but the full Phase 7 audit is a separate plan).
- Dark mode (whole spec excludes it).
- RankingPage's `mobileRowClassName` returns the rank-based color bar classes. If a future page needs a different left-side decoration (e.g. gradient or pattern), add a `meta.barColor` hook or a more flexible `renderMobileRow` callback.
- Real-time metric updates on the dashboard (numbers update only on mount + invalidate).
- Polishing Wordmark to accept `tone` and `subtitle` props — that is a Phase 3 deliverable; if missing, Tasks 5, 6, 8, 11, 14 will TS-error and must be deferred until Phase 3 lands.
- Admin layout / side-rail rewire: this plan assumes Phase 4's `AdminLayout` + `AdminSideRail` are in place. If the side rail needs a change to surface all 10 admin pages, that is a Phase 4 follow-up; Phase 6 does not touch the layout.
