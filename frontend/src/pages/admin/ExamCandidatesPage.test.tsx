import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  createRetakeGrant,
  getAdminExams,
  getExamCandidates,
  importExamCandidates,
} from "@/api/exams";
import { downloadImportFailureReport } from "@/api/imports";
import { ExamCandidatesPage } from "@/pages/admin/ExamCandidatesPage";

vi.mock("@/api/exams", () => ({
  getAdminExams: vi.fn(),
  getExamCandidates: vi.fn(),
  importExamCandidates: vi.fn(),
  createRetakeGrant: vi.fn(),
}));

vi.mock("@/api/imports", () => ({
  downloadImportTemplate: vi.fn(),
  downloadImportFailureReport: vi.fn(),
}));

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const router = createMemoryRouter(
    [{ path: "/admin/exams/:examId/candidates", element: <ExamCandidatesPage /> }],
    { initialEntries: ["/admin/exams/1/candidates"] },
  );

  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("ExamCandidatesPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getAdminExams).mockResolvedValue([
      {
        id: 1,
        title: "安全知识竞赛",
        description: null,
        duration_minutes: 60,
        question_rule: {},
        status: "draft",
        show_answer_after_submit: true,
      },
    ]);
    vi.mocked(getExamCandidates).mockResolvedValue([
      {
        candidate_id: 1,
        candidate_name: "张三",
        employee_no: "E001",
        department: "安全部",
        should_attend: true,
        candidate_status: "active",
        latest_attempt_status: "submitted",
        latest_score: 88,
        latest_total_score: 100,
        attempt_no: 1,
        attempt_kind: "initial",
        has_unused_retake_grant: false,
      },
    ]);
    vi.mocked(importExamCandidates).mockResolvedValue({
      batch_id: 7,
      success_count: 1,
      failed_count: 0,
      failures: [],
    });
    vi.mocked(createRetakeGrant).mockResolvedValue({
      candidate_id: 1,
      candidate_name: "张三",
      employee_no: "E001",
      department: "安全部",
      should_attend: true,
      candidate_status: "active",
      latest_attempt_status: "submitted",
      latest_score: 88,
      latest_total_score: 100,
      attempt_no: 1,
      attempt_kind: "initial",
      has_unused_retake_grant: true,
    });
  });

  it("renders semantic candidate copy", async () => {
    renderPage();

    expect(await screen.findByText("CANDIDATES · 应考人员")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "应考人员名单" })).toHaveClass(
      "font-display",
      "text-display-lg",
    );
    expect(screen.getByTestId("exam-candidates-shell")).toHaveClass("gap-6");
  });

  it("lists scoped candidates and can grant retake", async () => {
    const user = userEvent.setup();

    renderPage();

    expect(await screen.findByText("张三")).toBeInTheDocument();
    expect(screen.getByText("88 / 100")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "授权补考" }));

    await waitFor(() => expect(createRetakeGrant).toHaveBeenCalledWith("1", 1));
  });

  it("uploads candidates into the exam scope", async () => {
    const user = userEvent.setup();
    const file = new File(["x"], "candidates.xlsx", {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });

    renderPage();

    await user.upload(await screen.findByLabelText("选择 Excel 文件"), file);
    await user.click(screen.getByRole("button", { name: "上传应考人员" }));

    await waitFor(() => expect(importExamCandidates).toHaveBeenCalledWith("1", file));
    expect(await screen.findByText(/成功/)).toBeInTheDocument();
  });

  it("offers failure report download after scoped candidate import failures", async () => {
    const user = userEvent.setup();
    const file = new File(["x"], "candidates.xlsx", {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    vi.mocked(importExamCandidates).mockResolvedValueOnce({
      batch_id: 9,
      success_count: 0,
      failed_count: 1,
      failures: [{ row_number: 2, reason: "姓名不能为空" }],
    });

    renderPage();

    await user.upload(await screen.findByLabelText("选择 Excel 文件"), file);
    await user.click(screen.getByRole("button", { name: "上传应考人员" }));
    await user.click(await screen.findByRole("button", { name: "下载失败明细" }));

    expect(downloadImportFailureReport).toHaveBeenCalledWith(9);
  });
});
