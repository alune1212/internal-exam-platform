import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ColumnDef } from "@tanstack/react-table";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

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

const renderWithClient = (ui: ReactNode) => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
};

describe("ReportPage", () => {
  it("renders the chapter header, italic h1, and description", () => {
    renderWithClient(
      <ReportPage
        title="成绩册"
        chapterLabel="REPORTS · 报表"
        description="每次考试的提交结果"
        queryKey="score-report"
        queryFn={queryFn}
        columns={columns}
      />,
    );

    expect(screen.getByText("REPORTS · 报表")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "成绩册" })).toBeInTheDocument();
    expect(screen.getByText("每次考试的提交结果")).toBeInTheDocument();
  });

  it("uses shared page shell and section structure", async () => {
    renderWithClient(
      <ReportPage
        title="成绩册"
        chapterLabel="REPORTS · 报表"
        queryKey="score-report"
        queryFn={queryFn}
        columns={columns}
      />,
    );

    expect(screen.getByText("REPORTS · 报表")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "成绩册" })).toHaveClass(
      "font-display",
      "text-display-lg",
    );
    expect(screen.getByTestId("report-page-shell")).toHaveClass("gap-6");
    expect(screen.getByTestId("report-page-shell")).toHaveAttribute("data-stagger");
    expect(screen.getByTestId("report-page-table-section")).toHaveClass(
      "rounded-lg",
      "shadow-card",
    );
  });

  it("uses semantic reports copy by default", () => {
    renderWithClient(
      <ReportPage
        title="题目表现"
        queryKey="question-accuracy"
        queryFn={queryFn}
        columns={columns}
      />,
    );

    expect(screen.getByText("REPORTS · 报表")).toBeInTheDocument();
  });

  it("calls queryFn with the expected queryKey and renders the rows", async () => {
    renderWithClient(
      <ReportPage
        title="题目表现"
        queryKey="question-accuracy"
        queryFn={queryFn}
        columns={columns}
      />,
    );

    await waitFor(() => expect(screen.getByText("first")).toBeInTheDocument());
    expect(screen.getByText("second")).toBeInTheDocument();
    expect(screen.getByTestId("report-page-table-section")).toHaveClass(
      "rounded-lg",
      "shadow-card",
    );
  });

  it("renders an optional actions node", () => {
    renderWithClient(
      <ReportPage
        title="错题回看"
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

  it("can show prerequisite loading without starting the report query", () => {
    const disabledQueryFn = vi.fn(queryFn);

    renderWithClient(
      <ReportPage
        title="成绩册"
        queryKey={["score-report", "exams-loading"]}
        queryFn={disabledQueryFn}
        queryEnabled={false}
        isLoading
        columns={columns}
      />,
    );

    expect(screen.getByText(/LOADING · 加载中/i)).toBeInTheDocument();
    expect(disabledQueryFn).not.toHaveBeenCalled();
  });

  it("renders query failures as an error state instead of an empty table", async () => {
    renderWithClient(
      <ReportPage
        title="成绩册"
        queryKey="score-report"
        queryFn={async () => {
          throw new Error("report unavailable");
        }}
        columns={columns}
      />,
    );

    expect(await screen.findByRole("heading", { name: "报表加载失败。" })).toBeInTheDocument();
    expect(screen.queryByText("暂无数据")).not.toBeInTheDocument();
  });

  it("recovers from a first-load error after an explicit retry", async () => {
    const retryableQuery = vi
      .fn<() => Promise<Row[]>>()
      .mockRejectedValueOnce(new Error("temporary outage"))
      .mockResolvedValueOnce([{ id: 3, label: "recovered row" }]);

    renderWithClient(
      <ReportPage
        title="成绩册"
        queryKey="score-report-retry"
        queryFn={retryableQuery}
        columns={columns}
      />,
    );

    expect(await screen.findByRole("heading", { name: "报表加载失败。" })).toBeInTheDocument();
    screen.getByRole("button", { name: "重试" }).click();
    expect(await screen.findByText("recovered row")).toBeInTheDocument();
    expect(retryableQuery).toHaveBeenCalledTimes(2);
  });

  it("keeps stale table data visible when a background refetch fails", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    client.setQueryData(["score-report-stale"], [{ id: 1, label: "cached row" }]);

    render(
      <QueryClientProvider client={client}>
        <ReportPage
          title="成绩册"
          queryKey={["score-report-stale"]}
          queryFn={async () => {
            throw new Error("background refresh failed");
          }}
          columns={columns}
        />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("cached row")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "报表加载失败。" })).not.toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByTestId("page-stale-warning")).toHaveTextContent(
        "当前显示上一次成功的数据。",
      ),
    );
  });
});
