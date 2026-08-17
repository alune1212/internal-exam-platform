import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
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
import {
  getExamInvitationStatus,
  resendFailedExamInvitations,
  sendExamInvitations,
} from "@/api/invitations";
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

vi.mock("@/api/invitations", () => ({
  addExamRosterRow: vi.fn(),
  getExamInvitationStatus: vi.fn(),
  removeExamRosterRow: vi.fn(),
  resendFailedExamInvitations: vi.fn(),
  sendExamInvitations: vi.fn(),
  updateExamRosterRow: vi.fn(),
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
        roster_email: "zhangsan@example.com",
        roster_name: "张三",
        department: "安全部",
        account_status: "active",
        invitation_status: "not_sent",
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
      roster_email: "zhangsan@example.com",
      roster_name: "张三",
      department: "安全部",
      account_status: "active",
      invitation_status: "not_sent",
      latest_attempt_status: "submitted",
      latest_score: 88,
      latest_total_score: 100,
      attempt_no: 1,
      attempt_kind: "initial",
      has_unused_retake_grant: true,
    });
    vi.mocked(sendExamInvitations).mockResolvedValue({ accepted_count: 1, rejected_count: 0 });
    vi.mocked(getExamInvitationStatus).mockResolvedValue({
      exam_id: 1,
      rows: [],
    });
    vi.mocked(resendFailedExamInvitations).mockResolvedValue({
      accepted_count: 1,
      rejected_count: 0,
    });
  });

  it("renders semantic roster copy", async () => {
    renderPage();

    expect(await screen.findByText("应考名单", { exact: true })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "名单与授权" })).toHaveClass(
      "font-display",
      "text-display-lg",
    );
    expect(screen.getByTestId("exam-candidates-shell")).toHaveClass("gap-6");
    expect(screen.getByTestId("exam-candidates-shell")).toHaveAttribute(
      "data-density",
      "workbench",
    );
    expect(
      screen
        .getByRole("heading", { level: 1, name: "名单与授权" })
        .compareDocumentPosition(screen.getByRole("heading", { level: 2, name: "作废与补考结果" })),
    ).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
  });

  it("exposes the current exam context and keeps the roster destination active", async () => {
    renderPage();

    const contextNav = await screen.findByTestId("exam-context-nav");
    await waitFor(() =>
      expect(within(contextNav).getByTestId("exam-context-identity")).toHaveTextContent(
        "安全知识竞赛",
      ),
    );
    expect(within(contextNav).getByRole("link", { name: "名单与授权" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(within(contextNav).getByRole("link", { name: "邀请投递" })).toHaveAttribute(
      "href",
      "/admin/exams/1/candidates#invitation-actions",
    );
    expect(within(contextNav).getByRole("link", { name: "错题回看" })).toHaveAttribute(
      "href",
      "/admin/reports/wrong?exam_id=1",
    );
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
    expect(screen.getByText("#1 · 首次考试", { exact: true })).toBeInTheDocument();
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

  it("keeps the draft roster editable and exposes explicit initial invitation send only after publication", async () => {
    const user = userEvent.setup();
    vi.mocked(getAdminExams).mockResolvedValue([
      {
        id: 1,
        title: "安全知识竞赛",
        description: null,
        duration_minutes: 60,
        question_rule: {},
        status: "active",
        show_answer_after_submit: true,
      },
    ]);
    renderPage();

    await screen.findByText("张三");
    expect(await screen.findByRole("button", { name: "初次发送邀请" })).toBeEnabled();
    expect(screen.queryByText("已发送")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "初次发送邀请" }));
    await waitFor(() => expect(sendExamInvitations).toHaveBeenCalledWith("1"));
    expect(await screen.findByText(/初次邀请已接受 1 条/)).toBeInTheDocument();
  });

  it("resends failed recipients only and never offers a resend for sent rows", async () => {
    const user = userEvent.setup();
    vi.mocked(getExamCandidates).mockResolvedValueOnce([
      {
        candidate_id: 1,
        roster_email: "zhangsan@example.com",
        roster_name: "张三",
        account_status: "active",
        invitation_status: "failed",
        invitation_error_class: "transient",
        latest_attempt_status: "submitted",
        latest_score: 88,
        latest_total_score: 100,
        attempt_no: 1,
        attempt_kind: "initial",
        has_unused_retake_grant: false,
      },
    ]);
    vi.mocked(getAdminExams).mockResolvedValue([
      {
        id: 1,
        title: "安全知识竞赛",
        description: null,
        duration_minutes: 60,
        question_rule: {},
        status: "active",
        show_answer_after_submit: true,
      },
    ]);
    renderPage();

    expect(await screen.findByText("邮件服务暂时不可用")).toBeInTheDocument();
    expect(screen.queryByText("transient")).not.toBeInTheDocument();
    await user.click(await screen.findByRole("button", { name: "仅重发失败项" }));
    await waitFor(() => expect(resendFailedExamInvitations).toHaveBeenCalledWith("1"));
    expect(await screen.findByText(/失败重发已接受 1 条/)).toBeInTheDocument();
  });

  it("refreshes final invitation state after a slow background delivery", async () => {
    const user = userEvent.setup();
    vi.mocked(getAdminExams).mockResolvedValue([
      {
        id: 1,
        title: "安全知识竞赛",
        description: null,
        duration_minutes: 60,
        question_rule: {},
        status: "active",
        show_answer_after_submit: true,
      },
    ]);
    vi.mocked(getExamCandidates).mockResolvedValueOnce([
      {
        candidate_id: 1,
        roster_email: "zhangsan@example.com",
        roster_name: "张三",
        account_status: "active",
        invitation_status: "not_sent",
        invitation_claimed_at: "2026-08-11T08:00:00Z",
        has_unused_retake_grant: false,
      },
    ]);
    vi.mocked(getExamInvitationStatus).mockResolvedValueOnce({
      exam_id: 1,
      rows: [
        {
          candidate_id: 1,
          roster_email: "zhangsan@example.com",
          roster_name: "张三",
          account_status: "active",
          invitation_status: "sent",
          invitation_claimed_at: null,
          invitation_sent_at: "2026-08-11T08:00:20Z",
          has_unused_retake_grant: false,
        },
      ],
    });

    renderPage();

    expect(await screen.findByText("发送中")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "初次发送邀请" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "刷新邀请状态" }));
    expect(await screen.findByText("已发送")).toBeInTheDocument();
    expect(getExamInvitationStatus).toHaveBeenCalledTimes(1);
  });

  it("wraps a long roster name instead of widening the data region", async () => {
    const longName = "张三张三张三张三张三张三张三张三张三张三";
    vi.mocked(getExamCandidates).mockResolvedValueOnce([
      {
        candidate_id: 1,
        roster_email: "zhangsan@example.com",
        roster_name: longName,
        department: "安全部",
        account_status: "active",
        invitation_status: "not_sent",
        latest_attempt_status: "submitted",
        latest_score: 88,
        latest_total_score: 100,
        attempt_no: 1,
        attempt_kind: "initial",
        has_unused_retake_grant: false,
      },
    ]);

    renderPage();

    expect(await screen.findByText(longName)).toHaveClass("min-w-0", "break-words");
  });
});
