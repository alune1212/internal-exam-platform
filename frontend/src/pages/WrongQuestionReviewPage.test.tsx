import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Outlet, RouterProvider, createMemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getWrongPracticeQuestions } from "@/api/questions";
import type { CandidateSessionContext } from "@/components/layout/CandidateLayout";
import { WrongQuestionReviewPage } from "@/pages/WrongQuestionReviewPage";
import type { Candidate } from "@/types/candidate";
import type { PracticeWrongQuestion } from "@/types/question";

vi.mock("@/api/questions", () => ({
  getWrongPracticeQuestions: vi.fn(),
}));

const candidate: Candidate = {
  id: 42,
  token: "candidate-token",
  token_expires_at: "2099-01-01T00:00:00.000Z",
  email: "zhangsan@example.com",
  display_name: "张三",
  status: "active",
};

const wrongQuestion: PracticeWrongQuestion = {
  question_id: 201,
  question_type: "single",
  stem: "一段足够长的错题题干，用于确认复习页面在窄视口中可以自然换行，而不是把内容撑出页面。",
  category_1: "安全",
  category_2: "账号",
  status: "active",
  correct_answer: "A",
  analysis: "请结合题干和选项逐项核对，完成本题的复习。",
  incorrect_count: 2,
  total_attempts: 4,
  mastered: false,
  latest_practiced_at: "2026-08-14T08:00:00Z",
  history: [],
  options: [
    { label: "A", content: "正确选项", selected: false, correct: true },
    { label: "B", content: "其他选项", selected: true, correct: false },
  ],
};

function createQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function renderReview(
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
          { path: "practice/wrong-questions", element: <WrongQuestionReviewPage /> },
          { path: "practice", element: <div>练习页</div> },
        ],
      },
    ],
    { initialEntries: ["/practice/wrong-questions"] },
  );

  render(
    <QueryClientProvider client={createQueryClient()}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );

  return router;
}

describe("WrongQuestionReviewPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getWrongPracticeQuestions).mockResolvedValue([wrongQuestion]);
  });

  it("renders the ready review list with semantic calm framing and wrapped long content", async () => {
    renderReview();

    expect(await screen.findByRole("heading", { name: "错题复习" })).toBeInTheDocument();
    expect(screen.getByTestId("wrong-review-shell")).toHaveAttribute("data-density", "calm");
    expect(screen.getByTestId("wrong-review-shell")).toHaveAttribute("data-width", "wide");
    expect(await screen.findAllByRole("heading", { name: wrongQuestion.stem })).not.toHaveLength(0);
    expect(screen.getAllByRole("heading", { name: wrongQuestion.stem })[0]).toHaveClass(
      "break-words",
    );
    expect(screen.getAllByText("待巩固")).not.toHaveLength(0);
    expect(screen.getByRole("link", { name: "再次练习" })).toHaveAttribute(
      "href",
      "/practice?questionId=201",
    );
  });

  it("shows a calm loading state before the wrong-question response resolves", async () => {
    vi.mocked(getWrongPracticeQuestions).mockReturnValue(new Promise(() => {}));

    renderReview();

    expect(await screen.findByRole("status")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "筛选错题" })).toBeInTheDocument();
    expect(screen.queryByText(wrongQuestion.stem)).not.toBeInTheDocument();
  });

  it("renders explicit empty and error recovery states", async () => {
    vi.mocked(getWrongPracticeQuestions).mockResolvedValueOnce([]);
    renderReview();

    expect(await screen.findByRole("heading", { name: "当前筛选下没有错题" })).toBeInTheDocument();

    cleanup();
    vi.mocked(getWrongPracticeQuestions).mockClear();
    vi.mocked(getWrongPracticeQuestions)
      .mockRejectedValueOnce(new Error("temporary outage"))
      .mockResolvedValueOnce([wrongQuestion]);
    renderReview();

    expect(await screen.findByRole("heading", { name: "错题记录加载失败。" })).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("button", { name: "重试" }));
    await waitFor(() => expect(getWrongPracticeQuestions).toHaveBeenCalledTimes(2));
    expect(await screen.findByRole("heading", { name: wrongQuestion.stem })).toBeInTheDocument();
  });

  it("keeps filters and candidate-scoped API parameters intact", async () => {
    const user = userEvent.setup();
    renderReview();

    await screen.findByRole("heading", { name: wrongQuestion.stem });
    await user.type(screen.getByLabelText("一级分类"), "安全");
    await user.selectOptions(screen.getByLabelText("掌握状态"), "mastered");

    await waitFor(() =>
      expect(getWrongPracticeQuestions).toHaveBeenLastCalledWith({
        category_1: "安全",
        category_2: undefined,
        mastered: true,
      }),
    );
  });
});
