import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getPracticeQuestions, submitPracticeAnswer } from "@/api/questions";
import { CandidateLayout } from "@/components/layout/CandidateLayout";
import { setCurrentCandidate } from "@/lib/candidateSession";
import { PracticePage } from "@/pages/PracticePage";

vi.mock("@/api/questions", () => ({
  getPracticeQuestions: vi.fn(),
  submitPracticeAnswer: vi.fn(),
}));

const candidate = {
  id: 42,
  token: "candidate-token",
  token_expires_at: "2099-01-01T00:00:00.000Z",
  email: "zhangsan@example.com",
  display_name: "张三",
  status: "active" as const,
};

const question = {
  id: 201,
  question_type: "single" as const,
  stem: "练习题题干",
  score: 2,
  status: "active" as const,
  options: [
    { id: 1, label: "A", content: "选项 A", sort_order: 1 },
    { id: 2, label: "B", content: "选项 B", sort_order: 2 },
  ],
};

function mockMediaQuery(matches: boolean) {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string) => ({
      matches,
      media: query,
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }),
  });
}

function renderPractice(initialEntry = "/practice") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const router = createMemoryRouter(
    [
      {
        path: "/",
        element: <CandidateLayout />,
        children: [
          { path: "practice", element: <PracticePage /> },
          { path: "exams", element: <div>考试列表</div> },
        ],
      },
    ],
    { initialEntries: [initialEntry] },
  );

  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );

  return router;
}

describe("PracticePage presentation boundary", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    Object.defineProperty(window.navigator, "userAgent", {
      value:
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0.0.0 Safari/537.36",
      configurable: true,
    });
    mockMediaQuery(true);
    setCurrentCandidate(candidate);
    vi.mocked(getPracticeQuestions).mockResolvedValue([question]);
    vi.mocked(submitPracticeAnswer).mockResolvedValue({
      practice_answer_id: 1,
      question_id: question.id,
      selected_answer: "A",
      score: 2,
      is_correct: true,
      correct_answer: "A",
      analysis: "解析",
      option_comparison: [],
    });
  });

  it("requests Exam Focus only after the active practice workspace is ready", async () => {
    let resolveQuestions!: (value: (typeof question)[]) => void;
    vi.mocked(getPracticeQuestions).mockReturnValue(
      new Promise((resolve) => {
        resolveQuestions = resolve;
      }),
    );

    renderPractice();

    expect(screen.getByTestId("candidate-layout-frame")).toHaveAttribute(
      "data-candidate-presentation",
      "calm",
    );

    await act(async () => resolveQuestions([question]));
    await waitFor(() =>
      expect(screen.getByTestId("candidate-layout-frame")).toHaveAttribute(
        "data-candidate-presentation",
        "focus",
      ),
    );
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
  });

  it("restores Candidate Calm when the active practice route is left", async () => {
    const router = renderPractice();

    await screen.findByRole("link", { name: "查看错题复习" });
    expect(screen.getByTestId("candidate-layout-frame")).toHaveAttribute(
      "data-candidate-presentation",
      "focus",
    );

    await act(async () => router.navigate("/exams"));

    expect(await screen.findByText("考试列表")).toBeInTheDocument();
    expect(screen.getByTestId("candidate-layout-frame")).toHaveAttribute(
      "data-candidate-presentation",
      "calm",
    );
    expect(screen.getByRole("navigation")).toBeInTheDocument();
  });

  it("keeps the active focus workspace usable with long stems and option content", async () => {
    const longStem =
      "这是一段较长的练习题题干，用于确认题目内容在窄视口中可以自然换行并保持题目操作顺序。";
    const longContent = "这是一个较长的选项内容，用于确认选项不会撑破考试焦点工作区。";
    vi.mocked(getPracticeQuestions).mockResolvedValueOnce([
      {
        ...question,
        stem: longStem,
        options: [{ ...question.options[0], content: longContent }, question.options[1]],
      },
    ]);

    renderPractice();

    expect(await screen.findAllByRole("heading", { name: longStem })).not.toHaveLength(0);
    expect(screen.getAllByText(longContent)).not.toHaveLength(0);
    expect(screen.getByTestId("candidate-layout-frame")).toHaveAttribute(
      "data-candidate-presentation",
      "focus",
    );
  });

  it("communicates pending practice submission and keeps the answer controls disabled", async () => {
    let resolveSubmission!: (value: Awaited<ReturnType<typeof submitPracticeAnswer>>) => void;
    vi.mocked(submitPracticeAnswer).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveSubmission = resolve;
      }),
    );

    const user = userEvent.setup();
    renderPractice();

    await user.click((await screen.findAllByRole("radio", { name: /选项 A：选项 A/ }))[0]);
    await user.click(screen.getAllByRole("button", { name: "提交本题" })[0]);

    await waitFor(() => expect(submitPracticeAnswer).toHaveBeenCalled());
    expect(vi.mocked(submitPracticeAnswer).mock.calls[0][0]).toEqual({
      question_id: question.id,
      selected_answer: "A",
    });
    expect(screen.getAllByRole("button", { name: /提交本题|正在提交/ })[0]).toBeDisabled();
    expect(screen.getAllByRole("radio", { name: /选项 A：选项 A/ })[0]).toBeDisabled();
    await act(async () => {
      resolveSubmission({
        practice_answer_id: 1,
        question_id: question.id,
        selected_answer: "A",
        score: 2,
        is_correct: true,
        correct_answer: "A",
        analysis: "解析",
        option_comparison: [],
      });
    });
  });
});
