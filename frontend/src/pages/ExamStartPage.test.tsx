import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Outlet, RouterProvider, createMemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getActiveExams, startExam } from "@/api/exams";
import type { CandidateSessionContext } from "@/components/layout/CandidateLayout";
import { ExamStartPage } from "@/pages/ExamStartPage";
import type { Candidate } from "@/types/candidate";
import type { Exam } from "@/types/exam";

vi.mock("@/api/exams", () => ({
  getActiveExams: vi.fn(),
  startExam: vi.fn(),
}));

const candidate: Candidate = {
  id: 42,
  token: "candidate-token",
  token_expires_at: "2099-01-01T00:00:00.000Z",
  email: "zhangsan@example.com",
  display_name: "张三",
  status: "active",
};

const exam: Exam = {
  id: 1,
  title: "内部考试",
  description: "考试说明",
  duration_minutes: 30,
  question_rule: {
    question_count: 50,
    total_score: 100,
    pass_score: 60,
    mode: "fixed_paper",
    type_counts: { single: 30, multiple: 10, judge: 10 },
  },
  status: "published",
  show_answer_after_submit: true,
  available_from: null,
  available_until: null,
};

const queryKey = ["candidate", candidate.id, "active-exams"];

function createQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function renderExamStart(
  queryClient = createQueryClient(),
  context: CandidateSessionContext = {
    candidate,
    loginCandidate: vi.fn(),
    logoutCandidate: vi.fn(),
  },
) {
  const router = createMemoryRouter(
    [
      {
        path: "/",
        element: <Outlet context={context} />,
        children: [
          { path: "exams/:examId/start", element: <ExamStartPage /> },
          { path: "exams", element: <div>考试列表</div> },
          { path: "login", element: <div>邮箱登录</div> },
        ],
      },
    ],
    { initialEntries: ["/exams/1/start"] },
  );

  return {
    queryClient,
    router,
    ...render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    ),
  };
}

describe("ExamStartPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(startExam).mockReset();
  });

  it("recovers from a first-load error without losing safe navigation", async () => {
    vi.mocked(getActiveExams)
      .mockRejectedValueOnce(new Error("temporary outage"))
      .mockResolvedValueOnce([exam]);

    renderExamStart();

    expect(await screen.findByRole("heading", { name: "考试说明加载失败。" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "返回受邀考试" })).toBeInTheDocument();

    await userEvent.setup().click(screen.getByRole("button", { name: "重试" }));

    expect(await screen.findByRole("heading", { name: "阅读规则，开始作答" })).toBeInTheDocument();
    await waitFor(() => expect(getActiveExams).toHaveBeenCalledTimes(2));
  });

  it("keeps cached exam rules visible when a background refresh fails", async () => {
    const queryClient = createQueryClient();
    queryClient.setQueryData(queryKey, [exam], {
      updatedAt: Date.parse("2026-08-14T01:02:03.000Z"),
    });
    vi.mocked(getActiveExams)
      .mockRejectedValueOnce(new Error("background refresh failed"))
      .mockResolvedValueOnce([exam]);

    renderExamStart(queryClient);

    expect(await screen.findByTestId("page-stale-warning")).toHaveTextContent(
      "当前显示上一次成功的数据。",
    );
    expect(screen.getByTestId("page-stale-warning")).toHaveTextContent("上次成功更新于");
    expect(screen.getByRole("heading", { name: "阅读规则，开始作答" })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "阅读规则，开始作答" }).closest("[data-density]"),
    ).toHaveAttribute("data-density", "calm");
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByText("考试中答案会自动保存，但倒计时不会暂停。")).toBeInTheDocument();

    await userEvent.setup().click(screen.getByRole("button", { name: "重试" }));

    await waitFor(() => expect(screen.queryByTestId("page-stale-warning")).not.toBeInTheDocument());
    expect(getActiveExams).toHaveBeenCalledTimes(2);
  });

  it("renders the calm loading state while eligibility is pending", async () => {
    vi.mocked(getActiveExams).mockReturnValue(new Promise(() => {}));

    renderExamStart();

    expect(await screen.findByRole("status")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "阅读规则，开始作答" })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "阅读规则，开始作答" }).closest("[data-width]"),
    ).toHaveAttribute("data-width", "reading");
  });

  it("keeps long exam context readable without changing the start action", async () => {
    const longExam = {
      ...exam,
      title: "内部考试说明与应考规则的长标题用于确认页面可以自然换行",
    };
    vi.mocked(getActiveExams).mockResolvedValue([longExam]);

    renderExamStart();

    expect(await screen.findByText(longExam.title)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /开始考试/ })).toBeEnabled();
  });

  it("communicates a pending attempt start while preserving the request payload", async () => {
    vi.mocked(getActiveExams).mockResolvedValue([exam]);
    vi.mocked(startExam).mockReturnValue(new Promise(() => {}));

    renderExamStart();

    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: /开始考试/ }));

    expect(screen.getByRole("button", { name: "正在开始" })).toBeDisabled();
    expect(startExam).toHaveBeenCalledWith("1");
  });

  it("keeps the invitation return target for unauthenticated candidates", () => {
    renderExamStart(createQueryClient(), {
      candidate: null,
      loginCandidate: vi.fn(),
      logoutCandidate: vi.fn(),
    });

    expect(screen.getByRole("link", { name: "先登录" })).toHaveAttribute(
      "href",
      "/login?returnTo=%2Fexams%2F1%2Fstart",
    );
    expect(getActiveExams).not.toHaveBeenCalled();
  });
});
