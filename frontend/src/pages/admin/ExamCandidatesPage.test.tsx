import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  createRetakeGrant,
  getAdminExams,
  getExamCandidates,
  getExamIncidents,
  importExamCandidates,
} from "@/api/exams";
import { downloadImportFailureReport } from "@/api/imports";
import { ExamCandidatesPage } from "@/pages/admin/ExamCandidatesPage";

vi.mock("@/api/exams", () => ({
  getAdminExams: vi.fn(),
  getExamCandidates: vi.fn(),
  getExamIncidents: vi.fn(),
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
    vi.mocked(getExamIncidents).mockResolvedValue([]);
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

  it("renders semantic roster copy", async () => {
    renderPage();

    expect(await screen.findByText("ROSTER · 应考名单")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "名单与授权" })).toHaveClass(
      "font-display",
      "text-display-lg",
    );
    expect(screen.getByTestId("exam-candidates-shell")).toHaveClass("gap-6");
  });

  it("blocks candidate mutations while the exam state is unresolved", async () => {
    vi.mocked(getAdminExams).mockReturnValue(
      new Promise<Awaited<ReturnType<typeof getAdminExams>>>(() => {}),
    );

    renderPage();

    expect(await screen.findByText("正在确认考试状态，暂不能修改应考名单。")).toBeInTheDocument();
    expect(screen.getByLabelText("选择 Excel 文件")).toBeDisabled();
    expect(screen.getByRole("button", { name: "选择文件" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "上传应考名单" })).toBeDisabled();
    expect(getExamCandidates).not.toHaveBeenCalled();
  });

  it("renders an explicit error when the exam state cannot load", async () => {
    vi.mocked(getAdminExams).mockRejectedValueOnce(new Error("exam unavailable"));

    renderPage();

    expect(await screen.findByRole("heading", { name: "考试状态加载失败。" })).toBeInTheDocument();
    expect(screen.getByLabelText("选择 Excel 文件")).toBeDisabled();
    expect(screen.getByRole("button", { name: "选择文件" })).toBeDisabled();
    expect(getExamCandidates).not.toHaveBeenCalled();
  });

  it("renders candidate list errors without falling back to an empty table", async () => {
    vi.mocked(getExamCandidates).mockRejectedValueOnce(new Error("candidate list unavailable"));

    renderPage();

    expect(await screen.findByRole("heading", { name: "名单加载失败。" })).toBeInTheDocument();
    expect(screen.queryByText("暂无应考名单人员")).not.toBeInTheDocument();
  });

  it("lists scoped candidates and can grant retake", async () => {
    const user = userEvent.setup();

    renderPage();

    expect(await screen.findByText("张三")).toBeInTheDocument();
    expect(screen.getByText("88 / 100")).toBeInTheDocument();
    expect(screen.getByText("#1 · INITIAL · 首次考试")).toBeInTheDocument();
    expect(screen.queryByText("#1 initial")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "授权补考" }));

    await waitFor(() => expect(createRetakeGrant).toHaveBeenCalledWith("1", 1));
  });

  it("shows retained incident outcomes without treating them as normal results", async () => {
    vi.mocked(getExamIncidents).mockResolvedValueOnce([
      {
        attempt_id: 12,
        exam_id: 1,
        candidate_id: 1,
        prior_status: "submitted",
        status: "voided",
        voided_at: "2026-07-21T08:00:00Z",
        voided_by: "primary-operator",
        reason: "办公室网络中断",
        attempt_no: 1,
        retake_granted: true,
      },
    ]);

    renderPage();

    expect(await screen.findByText("办公室网络中断")).toBeInTheDocument();
    expect(screen.getByText("已授权补考")).toBeInTheDocument();
    expect(screen.getByText(/不计入正常成绩/)).toBeInTheDocument();
  });

  it("uploads candidates into the exam scope", async () => {
    const user = userEvent.setup();
    const file = new File(["x"], "candidates.xlsx", {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });

    renderPage();

    const fileInput = await screen.findByLabelText("选择 Excel 文件");
    await waitFor(() => expect(fileInput).toBeEnabled());
    await user.upload(fileInput, file);
    expect(screen.getByText("candidates.xlsx")).toBeInTheDocument();
    const uploadButton = screen.getByRole("button", { name: "上传应考名单" });
    await waitFor(() => expect(uploadButton).toBeEnabled());
    await user.click(uploadButton);

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

    const fileInput = await screen.findByLabelText("选择 Excel 文件");
    await waitFor(() => expect(fileInput).toBeEnabled());
    await user.upload(fileInput, file);
    const uploadButton = screen.getByRole("button", { name: "上传应考名单" });
    await waitFor(() => expect(uploadButton).toBeEnabled());
    await user.click(uploadButton);
    await user.click(await screen.findByRole("button", { name: "下载失败明细" }));

    expect(downloadImportFailureReport).toHaveBeenCalledWith(9);
  });
});
