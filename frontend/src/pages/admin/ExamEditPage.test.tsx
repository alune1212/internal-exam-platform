import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  getAdminExams,
  getPublicationReadiness,
  publishAdminExam,
  releaseResultDetails,
  updateAdminExam,
} from "@/api/exams";
import { ExamEditPage } from "@/pages/admin/ExamEditPage";
import type { Exam } from "@/types/exam";

vi.mock("@/api/exams", () => ({
  getAdminExams: vi.fn(),
  getPublicationReadiness: vi.fn(),
  publishAdminExam: vi.fn(),
  releaseResultDetails: vi.fn(),
  updateAdminExam: vi.fn(),
}));

const fixedRule = {
  question_count: 50,
  total_score: 100,
  pass_score: 60,
  mode: "fixed_paper",
  type_counts: { single: 30, multiple: 10, judge: 10 },
};

const exam: Exam = {
  id: 1,
  title: "安全知识竞赛",
  description: null,
  duration_minutes: 60,
  question_rule: fixedRule,
  status: "draft",
  show_answer_after_submit: true,
};

const readyForPublication = {
  exam_id: 1,
  ready: true,
  prospective_pool_count: 50,
  roster_count: 20,
  blockers: [],
  warnings: [{ code: "window_note", message: "请核对考试开放时间" }],
  fingerprint: "readiness-fingerprint",
};

function renderExamEditPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const router = createMemoryRouter(
    [{ path: "/admin/exams/:examId/edit", element: <ExamEditPage /> }],
    { initialEntries: ["/admin/exams/1/edit"] },
  );

  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("ExamEditPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getAdminExams).mockResolvedValue([exam]);
    vi.mocked(getPublicationReadiness).mockResolvedValue(readyForPublication);
    vi.mocked(publishAdminExam).mockResolvedValue({ ...exam, status: "active" });
    vi.mocked(releaseResultDetails).mockResolvedValue({
      exam_id: 1,
      released_at: "2026-07-21T08:00:00Z",
      released_by: "primary-operator",
    });
    vi.mocked(updateAdminExam).mockResolvedValue(exam);
  });

  it("renders semantic exams copy", async () => {
    renderExamEditPage();

    expect(await screen.findByText("考试", { exact: true })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "编排考试 #1" })).toHaveClass(
      "font-display",
      "text-display-lg",
    );
    expect(screen.getByTestId("exam-edit-shell")).toHaveClass("gap-6");
  });

  it("exposes the current exam context and keeps configuration active", async () => {
    renderExamEditPage();

    const contextNav = await screen.findByTestId("exam-context-nav");
    await waitFor(() =>
      expect(within(contextNav).getByTestId("exam-context-identity")).toHaveTextContent(
        "安全知识竞赛",
      ),
    );
    expect(within(contextNav).getByRole("link", { name: "考试编排" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(within(contextNav).getByRole("link", { name: "考试工作台" })).toHaveAttribute(
      "href",
      "/admin/exams/1",
    );
    expect(within(contextNav).getByRole("link", { name: "名单与授权" })).toHaveAttribute(
      "href",
      "/admin/exams/1/candidates",
    );
  });

  it("blocks the form and save action while the target exam is loading", async () => {
    vi.mocked(getAdminExams).mockReturnValue(
      new Promise<Awaited<ReturnType<typeof getAdminExams>>>(() => {}),
    );

    renderExamEditPage();

    expect(await screen.findByText("加载中...", { exact: true })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /保存配置/ })).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/考试名称/)).not.toBeInTheDocument();
  });

  it("renders an error state when the target exam query fails", async () => {
    vi.mocked(getAdminExams).mockRejectedValueOnce(new Error("exam unavailable"));

    renderExamEditPage();

    expect(await screen.findByRole("heading", { name: "考试编排加载失败。" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /保存配置/ })).not.toBeInTheDocument();
  });

  it("renders a missing state when the target exam is not found", async () => {
    vi.mocked(getAdminExams).mockResolvedValueOnce([]);

    renderExamEditPage();

    expect(await screen.findByRole("heading", { name: "未找到考试。" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /保存配置/ })).not.toBeInTheDocument();
  });

  it("loads the current exam and saves the fixed 50-question rule", async () => {
    const user = userEvent.setup();

    renderExamEditPage();

    expect(await screen.findByDisplayValue("安全知识竞赛")).toBeInTheDocument();
    expect(screen.getByDisplayValue("60")).toBeInTheDocument();
    expect(screen.getByDisplayValue(/"question_count": 50/)).toBeInTheDocument();
    expect(screen.getByLabelText(/状态/)).toHaveRole("combobox");
    expect(screen.queryByRole("option", { name: /已发布/ })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /保存配置/ }));

    await waitFor(() => expect(updateAdminExam).toHaveBeenCalledTimes(1));
    expect(updateAdminExam).toHaveBeenCalledWith("1", {
      title: "安全知识竞赛",
      duration_minutes: 60,
      status: "draft",
      available_from: null,
      available_until: null,
      question_rule: fixedRule,
    });
  });

  it("distinguishes publication blockers from warnings and fails closed", async () => {
    vi.mocked(getPublicationReadiness).mockResolvedValueOnce({
      ...readyForPublication,
      ready: false,
      blockers: [{ code: "empty_roster", message: "应考名单不能为空" }],
    });

    renderExamEditPage();

    expect(await screen.findByRole("heading", { name: "发布预检" })).toBeInTheDocument();
    expect(await screen.findByLabelText("发布阻断项")).toHaveTextContent("应考名单不能为空");
    expect(screen.getByLabelText("发布警告")).toHaveTextContent("请核对考试开放时间");
    expect(screen.getByRole("button", { name: "确认发布" })).toBeDisabled();
  });

  it("requires the exact title and uses the authoritative publish endpoint", async () => {
    const user = userEvent.setup();
    renderExamEditPage();

    const confirmation = await screen.findByLabelText(/输入完整考试名称确认发布/);
    const publishButton = screen.getByRole("button", { name: "确认发布" });
    expect(publishButton).toBeDisabled();

    await user.type(confirmation, "安全知识");
    expect(publishButton).toBeDisabled();
    await user.type(confirmation, "竞赛");
    expect(publishButton).toBeEnabled();
    await user.click(publishButton);

    await waitFor(() => expect(publishAdminExam).toHaveBeenCalledWith("1", "安全知识竞赛"));
    expect(updateAdminExam).not.toHaveBeenCalledWith(
      "1",
      expect.objectContaining({ status: "active" }),
    );
  });

  it("saves available window fields", async () => {
    const user = userEvent.setup();

    renderExamEditPage();

    await user.type(await screen.findByLabelText(/开放开始时间/), "2026-06-20T09:00");
    await user.type(screen.getByLabelText(/开放结束时间/), "2026-06-20T10:00");
    await user.click(screen.getByRole("button", { name: /保存配置/ }));

    await waitFor(() => expect(updateAdminExam).toHaveBeenCalledTimes(1));
    expect(updateAdminExam).toHaveBeenCalledWith(
      "1",
      expect.objectContaining({
        available_from: expect.stringContaining("2026-06-20"),
        available_until: expect.stringContaining("2026-06-20"),
      }),
    );
  });

  it("freezes duration and question rule after publishing", async () => {
    const user = userEvent.setup();
    vi.mocked(getAdminExams).mockResolvedValue([{ ...exam, status: "active" }]);

    renderExamEditPage();

    expect(await screen.findByDisplayValue("安全知识竞赛")).toBeInTheDocument();
    expect(screen.getByDisplayValue("60")).toBeDisabled();
    expect(screen.getByDisplayValue(/"question_count": 50/)).toBeDisabled();
    expect(
      screen.getByText("考试已发布，题池、时长、抽题规则和应考名单已冻结。"),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /保存配置/ }));

    await waitFor(() => expect(updateAdminExam).toHaveBeenCalledTimes(1));
    expect(updateAdminExam).toHaveBeenCalledWith("1", {
      title: "安全知识竞赛",
      status: "active",
      available_from: null,
      available_until: null,
    });
  });

  it("requires the exact title for one-time answer detail release", async () => {
    const user = userEvent.setup();
    vi.mocked(getAdminExams).mockResolvedValue([{ ...exam, status: "active" }]);

    renderExamEditPage();

    const confirmation = await screen.findByLabelText(/输入完整考试名称确认发布/);
    const releaseButton = screen.getByRole("button", { name: "发布答案与解析" });
    expect(releaseButton).toBeDisabled();
    await user.type(confirmation, exam.title);
    expect(releaseButton).toBeEnabled();
    await user.click(releaseButton);

    await waitFor(() => expect(releaseResultDetails).toHaveBeenCalledWith("1", "安全知识竞赛"));
  });

  it("shows irreversible release metadata after details are published", async () => {
    vi.mocked(getAdminExams).mockResolvedValue([
      {
        ...exam,
        status: "active",
        result_details_released_at: "2026-07-21T08:00:00Z",
        result_details_released_by: "primary-operator",
      },
    ]);

    renderExamEditPage();

    expect(await screen.findByText(/primary-operator/)).toBeInTheDocument();
    expect(screen.getByText(/不可撤销或重复/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "发布答案与解析" })).not.toBeInTheDocument();
  });
});
