import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import { getExamWorkspace } from "@/api/exams";
import { adminKeys } from "@/lib/queryKeys";
import { ExamWorkspacePage } from "@/pages/admin/ExamWorkspacePage";
import type { ExamWorkspaceRead } from "@/types/exam";

vi.mock("@/api/exams", () => ({
  getExamWorkspace: vi.fn(),
}));

const exam = {
  id: 1,
  title: "安全知识竞赛",
  description: null,
  duration_minutes: 60,
  question_rule: {},
  status: "active",
  show_answer_after_submit: true,
  available_from: "2026-07-21T08:00:00Z",
  available_until: "2026-07-21T10:00:00Z",
};

const workspace: ExamWorkspaceRead = {
  observed_at: "2026-07-21T08:30:00Z",
  exam,
  readiness: null,
  roster_summary: { total_count: 12, active_count: 10, pending_count: 2, inactive_count: 0 },
  invitation_summary: { not_sent_count: 1, sent_count: 10, failed_count: 1, in_flight_count: 0 },
  attendance_summary: { not_started_count: 4, in_progress_count: 2, submitted_count: 6 },
  attempt_summary: {
    in_progress_count: 2,
    submitted_count: 5,
    auto_submitted_count: 1,
    voided_count: 1,
  },
  incident_summary: { voided_count: 1, unused_retake_count: 2 },
  next_action: "send_invitations",
  next_action_reason: "仍有 1 条邀请未发送。",
};

function renderPage(
  queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } }),
) {
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/admin/exams/1"]}>
        <Routes>
          <Route path="/admin/exams/:examId" element={<ExamWorkspacePage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return queryClient;
}

describe("ExamWorkspacePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getExamWorkspace).mockResolvedValue(workspace);
  });

  it("renders an explicit loading state before the aggregate arrives", async () => {
    vi.mocked(getExamWorkspace).mockReturnValue(new Promise(() => undefined));

    renderPage();

    expect(await screen.findByText("加载中...", { exact: true })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveAttribute("aria-busy", "true");
    expect(screen.queryByText("安全知识竞赛")).not.toBeInTheDocument();
  });

  it("offers retry and distinguishes a missing exam from an empty workspace", async () => {
    const user = userEvent.setup();
    vi.mocked(getExamWorkspace)
      .mockRejectedValueOnce(new ApiError("exam missing", 404))
      .mockResolvedValueOnce(workspace);

    renderPage();

    expect(await screen.findByRole("heading", { name: "未找到考试。" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "重试" }));

    expect(
      await screen.findByRole("heading", { name: /考试工作台 · 安全知识竞赛/ }),
    ).toBeInTheDocument();
    expect(getExamWorkspace).toHaveBeenCalledTimes(2);
  });

  it("shows a recoverable server error instead of an empty summary", async () => {
    vi.mocked(getExamWorkspace).mockRejectedValueOnce(new Error("workspace unavailable"));

    renderPage();

    expect(
      await screen.findByRole("heading", { name: "考试工作台加载失败。" }),
    ).toBeInTheDocument();
    expect(screen.getByText("workspace unavailable")).toBeInTheDocument();
    expect(screen.queryByText("名单总数")).not.toBeInTheDocument();
  });

  it("keeps the last successful summaries visible when a background refresh fails", async () => {
    vi.mocked(getExamWorkspace)
      .mockResolvedValueOnce(workspace)
      .mockRejectedValueOnce(new Error("temporary refresh failure"));
    const queryClient = renderPage();

    expect(await screen.findByText("名单总数")).toBeInTheDocument();
    await queryClient.refetchQueries({ queryKey: adminKeys.examWorkspace("1") });

    expect(await screen.findByText("工作台刷新失败", { exact: true })).toBeInTheDocument();
    expect(screen.getByText("名单总数")).toBeInTheDocument();
    expect(screen.getByTestId("exam-workspace-shell").querySelector("time")).toHaveAttribute(
      "data-observed-at",
      workspace.observed_at,
    );
    expect(screen.getByText(/发送邀请：/)).toBeInTheDocument();
    expect(screen.getByTestId("page-stale-warning")).toHaveTextContent("temporary refresh failure");
    expect(screen.getByRole("button", { name: "重试" })).toBeInTheDocument();
    expect(screen.getByTestId("page-stale-warning")).toHaveTextContent("上次成功更新于");
  });

  it("renders privacy-bounded summaries, observation time, and the server advisory reason", async () => {
    renderPage();

    expect(
      await screen.findByRole("heading", { name: /考试工作台 · 安全知识竞赛/ }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("exam-workspace-shell")).toHaveAttribute("data-density", "workbench");
    expect(
      screen
        .getByRole("heading", { level: 1, name: /考试工作台 · 安全知识竞赛/ })
        .compareDocumentPosition(
          screen.getByRole("heading", { level: 2, name: "发布预检与生命周期" }),
        ),
    ).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    expect(screen.getByText("数据观测时间：")).toBeInTheDocument();
    expect(screen.getByTestId("exam-workspace-shell").querySelector("time")).toHaveAttribute(
      "data-observed-at",
      workspace.observed_at,
    );
    expect(screen.getByText("下一步建议")).toBeInTheDocument();
    expect(screen.getByText(/发送邀请：/)).toBeInTheDocument();
    expect(screen.getByText(/仍有 1 条邀请未发送/)).toBeInTheDocument();
    expect(screen.getByText("名单总数")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("失败邀请")).toBeInTheDocument();
    expect(screen.getByText("正常提交")).toBeInTheDocument();
    expect(screen.getByText("未使用补考授权")).toBeInTheDocument();
    expect(screen.queryByText("张三")).not.toBeInTheDocument();
  });

  it("links the advisory action and all existing scoped operation surfaces", async () => {
    renderPage();

    await screen.findByRole("heading", { name: /考试工作台 · 安全知识竞赛/ });
    expect(screen.getByRole("link", { name: /^发送邀请/ })).toHaveAttribute(
      "href",
      "/admin/exams/1/candidates#invitation-actions",
    );
    expect(screen.getByRole("link", { name: "发布 / 编排" })).toHaveAttribute(
      "href",
      "/admin/exams/1/edit#publish",
    );
    expect(screen.getByRole("link", { name: "名单" })).toHaveAttribute(
      "href",
      "/admin/exams/1/candidates",
    );
    expect(screen.getAllByRole("link", { name: "邀请投递" })).not.toHaveLength(0);
    screen.getAllByRole("link", { name: "邀请投递" }).forEach((link) => {
      expect(link).toHaveAttribute("href", "/admin/exams/1/candidates#invitation-actions");
    });
    const contextNav = screen.getByTestId("exam-context-nav");
    expect(within(contextNav).getByRole("link", { name: "考试工作台" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(within(contextNav).getByRole("link", { name: "考试编排" })).toHaveAttribute(
      "href",
      "/admin/exams/1/edit",
    );
    expect(within(contextNav).getByRole("link", { name: "名单与授权" })).toHaveAttribute(
      "href",
      "/admin/exams/1/candidates",
    );
    expect(within(contextNav).getByRole("link", { name: "成绩册" })).toHaveAttribute(
      "href",
      "/admin/reports/scores?exam_id=1",
    );
    expect(screen.getByRole("link", { name: "事故记录" })).toHaveAttribute(
      "href",
      "/admin/exams/1/candidates#incident-title",
    );
    expect(screen.getByRole("link", { name: "成绩结果" })).toHaveAttribute(
      "href",
      "/admin/reports/scores?exam_id=1",
    );
    expect(screen.getByRole("link", { name: "归档 / 编排" })).toHaveAttribute(
      "href",
      "/admin/exams/1/edit#archive",
    );
  });

  it("polls active workspaces at fifteen seconds and stops for archived data", async () => {
    const queryClient = renderPage();

    await screen.findByRole("heading", { name: /考试工作台 · 安全知识竞赛/ });
    const query = queryClient.getQueryCache().find({ queryKey: adminKeys.examWorkspace("1") });
    expect(query).toBeDefined();
    if (!query) return;
    const refetchInterval = (
      query.options as {
        refetchInterval?: (currentQuery: typeof query) => number | false;
      }
    ).refetchInterval;
    expect(refetchInterval?.(query)).toBe(15_000);

    queryClient.setQueryData(adminKeys.examWorkspace("1"), {
      ...workspace,
      exam: { ...workspace.exam, status: "archived" },
      next_action: "complete",
    } satisfies ExamWorkspaceRead);
    await waitFor(() => expect(refetchInterval?.(query)).toBe(false));
  });

  it("keeps operation links wrapped for narrow admin layouts", async () => {
    renderPage();

    await screen.findByRole("heading", { name: /考试工作台 · 安全知识竞赛/ });
    expect(screen.getByRole("group", { name: "考试操作页面" })).toHaveClass("flex-wrap");
    expect(screen.getAllByRole("link").length).toBeGreaterThanOrEqual(8);
  });

  it("wraps a long exam title in the workbench heading", async () => {
    const longTitle = "安全生产专项考试安全生产专项考试安全生产专项考试安全生产专项考试";
    vi.mocked(getExamWorkspace).mockResolvedValueOnce({
      ...workspace,
      exam: { ...workspace.exam, title: longTitle },
    });

    renderPage();

    expect(await screen.findByRole("heading", { name: `考试工作台 · ${longTitle}` })).toHaveClass(
      "min-w-0",
      "break-words",
    );
  });
});
