import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  downloadImportFailureReport,
  downloadImportTemplate,
  importQuestions,
} from "@/api/imports";
import { QuestionImportPage } from "@/pages/admin/QuestionImportPage";

vi.mock("@/api/imports", () => ({
  downloadImportTemplate: vi.fn(),
  downloadImportFailureReport: vi.fn(),
  importQuestions: vi.fn(),
}));

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <QuestionImportPage />
    </QueryClientProvider>,
  );
}

describe("QuestionImportPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(downloadImportTemplate).mockResolvedValue(undefined);
    vi.mocked(downloadImportFailureReport).mockResolvedValue(undefined);
    vi.mocked(importQuestions).mockResolvedValue({
      batch_id: 11,
      success_count: 0,
      failed_count: 1,
      failures: [{ row_number: 2, reason: "题干不能为空" }],
    });
  });

  it("renders semantic library copy", () => {
    renderPage();

    expect(screen.getByText("QUESTION IMPORT · 题库导入")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "导入题目" })).toHaveClass(
      "font-display",
      "text-display-lg",
    );
    expect(screen.getByTestId("question-import-shell")).toHaveClass("gap-6");
    expect(screen.getByText("未选择文件")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "上传并校验题库" })).toBeDisabled();
  });

  it("offers failure report download after question import failures", async () => {
    const user = userEvent.setup();
    const file = new File(["x"], "questions.xlsx", {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    renderPage();

    await user.upload(screen.getByLabelText("选择 Excel 文件"), file);
    expect(screen.getByText("questions.xlsx")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "上传并校验题库" }));
    await user.click(await screen.findByRole("button", { name: "下载失败明细" }));

    await waitFor(() => expect(downloadImportFailureReport).toHaveBeenCalledWith(11));
  });
});
