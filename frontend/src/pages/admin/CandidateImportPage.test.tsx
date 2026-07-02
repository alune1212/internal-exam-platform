import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { downloadImportFailureReport, importCandidates } from "@/api/imports";
import { CandidateImportPage } from "@/pages/admin/CandidateImportPage";

vi.mock("@/api/imports", () => ({
  downloadImportFailureReport: vi.fn(),
  importCandidates: vi.fn(),
}));

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/admin/exams/7/candidates/import"]}>
        <Routes>
          <Route path="/admin/exams/:examId/candidates/import" element={<CandidateImportPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("CandidateImportPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(downloadImportFailureReport).mockResolvedValue(undefined);
    vi.mocked(importCandidates).mockResolvedValue({
      batch_id: 12,
      success_count: 1,
      failed_count: 1,
      failures: [{ row_number: 3, reason: "姓名不能为空" }],
    });
  });

  it("renders semantic roster copy", () => {
    renderPage();

    expect(screen.getByText("ROSTER · 应考名单")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "应考名单导入" })).toHaveClass(
      "font-display",
      "text-display-lg",
    );
    expect(screen.getByTestId("candidate-import-shell")).toHaveClass("gap-6");
    expect(screen.getByText("未选择文件")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "上传应考名单" })).toBeDisabled();
  });

  it("imports candidates for the current exam and offers failure report download", async () => {
    const user = userEvent.setup();
    const file = new File(["x"], "candidates.xlsx", {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    renderPage();

    await user.upload(screen.getByLabelText("选择 Excel 文件"), file);
    expect(screen.getByText("candidates.xlsx")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "上传应考名单" }));

    await waitFor(() => expect(importCandidates).toHaveBeenCalledWith("7", file));
    expect(await screen.findByRole("status")).toHaveTextContent("应考名单导入完成。");
    expect(screen.getByText("行 3 · 姓名不能为空")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "下载失败明细" }));

    await waitFor(() => expect(downloadImportFailureReport).toHaveBeenCalledWith(12));
  });
});
