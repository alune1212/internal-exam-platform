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
import type { QuestionImportResult } from "@/types/imports";

vi.mock("@/api/imports", () => ({
  downloadImportTemplate: vi.fn(),
  downloadImportFailureReport: vi.fn(),
  importQuestions: vi.fn(),
}));

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

const failedImport: QuestionImportResult = {
  batch_id: 11,
  success_count: 0,
  failed_count: 1,
  failures: [{ row_number: 2, reason: "题干不能为空" }],
};

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
    vi.mocked(importQuestions).mockResolvedValue(failedImport);
  });

  it("renders semantic library copy", () => {
    renderPage();

    expect(screen.getByText("题库导入", { exact: true })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "导入题目" })).toHaveClass(
      "font-display",
      "text-display-lg",
    );
    expect(screen.getByTestId("question-import-shell")).toHaveAttribute("data-width", "standard");
    expect(screen.getByTestId("question-import-shell")).toHaveClass("gap-6");
    expect(screen.getByTestId("import-panel")).toHaveAttribute("data-surface-role", "panel");
    expect(screen.getByText("未选择文件")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "上传并校验题库" })).toBeDisabled();
    expect(screen.queryByText(/QUESTION IMPORT ·/)).not.toBeInTheDocument();
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

  it("keeps the upload action keyboard reachable and exposes pending state", async () => {
    const user = userEvent.setup();
    const pending = deferred<QuestionImportResult>();
    vi.mocked(importQuestions).mockReturnValueOnce(pending.promise);
    const file = new File(["question"], "questions.xlsx", {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    renderPage();

    const fileInput = screen.getByLabelText("选择 Excel 文件");
    await user.upload(fileInput, file);
    expect(fileInput).toHaveAttribute("accept", ".xlsx,.xls");
    await user.click(screen.getByRole("button", { name: "上传并校验题库" }));

    const pendingButton = screen.getByRole("button", { name: "正在导入题库" });
    expect(pendingButton).toHaveAttribute("aria-busy", "true");
    expect(pendingButton).toBeDisabled();

    pending.resolve({
      batch_id: 12,
      success_count: 2,
      failed_count: 0,
      failures: [],
    });
    expect(await screen.findByText("题库导入完成。")).toBeInTheDocument();
    expect(screen.getByTestId("question-import-result")).toHaveAttribute(
      "data-surface-role",
      "summary",
    );
  });

  it("renders a confirmed success without a failure-report action", async () => {
    const user = userEvent.setup();
    vi.mocked(importQuestions).mockResolvedValueOnce({
      batch_id: 13,
      success_count: 3,
      failed_count: 0,
      failures: [],
    });
    const file = new File(["question"], "success.xlsx");
    renderPage();

    await user.upload(screen.getByLabelText("选择 Excel 文件"), file);
    await user.click(screen.getByRole("button", { name: "上传并校验题库" }));

    expect(await screen.findByTestId("question-import-result")).toHaveTextContent(
      "成功 3 行，失败 0 行",
    );
    expect(screen.queryByRole("button", { name: "下载失败明细" })).not.toBeInTheDocument();
  });

  it("shows import errors and keeps long failure reasons wrapped", async () => {
    const user = userEvent.setup();
    const reason = "题目选项内容过长且包含一段用于窄屏换行验证的连续文字";
    vi.mocked(importQuestions).mockResolvedValueOnce({
      batch_id: 14,
      success_count: 1,
      failed_count: 1,
      failures: [{ row_number: 25, reason }],
    });
    const file = new File(["question"], "long-content.xlsx");
    renderPage();

    await user.upload(screen.getByLabelText("选择 Excel 文件"), file);
    await user.click(screen.getByRole("button", { name: "上传并校验题库" }));

    const failure = await screen.findByText(reason);
    expect(failure).toHaveClass("break-words");
    expect(screen.getByText("行 25")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "下载失败明细" })).toBeInTheDocument();
  });

  it("announces upload errors and template download feedback", async () => {
    const user = userEvent.setup();
    vi.mocked(importQuestions).mockRejectedValueOnce(new Error("Excel 格式无效"));
    renderPage();

    await user.click(screen.getByRole("button", { name: "下载题库导入模板" }));
    expect(await screen.findByText("题库导入模板已开始下载。")).toBeInTheDocument();

    const file = new File(["question"], "invalid.xlsx");
    await user.upload(screen.getByLabelText("选择 Excel 文件"), file);
    await user.click(screen.getByRole("button", { name: "上传并校验题库" }));
    expect(await screen.findByText("Excel 格式无效")).toBeInTheDocument();
  });
});
