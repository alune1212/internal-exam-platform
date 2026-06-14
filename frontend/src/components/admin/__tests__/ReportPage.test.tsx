import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ColumnDef } from "@tanstack/react-table";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

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
        title="个人成绩"
        chapterLabel="CHAPTER 04 · REPORTS"
        description="每次考试的提交结果"
        queryKey="score-report"
        queryFn={queryFn}
        columns={columns}
      />,
    );

    expect(screen.getByText("CHAPTER 04 · REPORTS")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "个人成绩" })).toBeInTheDocument();
    expect(screen.getByText("每次考试的提交结果")).toBeInTheDocument();
  });

  it("calls queryFn with the expected queryKey and renders the rows", async () => {
    renderWithClient(
      <ReportPage
        title="题目正确率"
        queryKey="question-accuracy"
        queryFn={queryFn}
        columns={columns}
      />,
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
