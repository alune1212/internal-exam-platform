import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getAttemptResult } from "@/api/attempts";
import { setCurrentCandidate } from "@/lib/candidateSession";
import { ExamResultPage } from "@/pages/ExamResultPage";
import type { Candidate } from "@/types/candidate";
import type { AttemptResult } from "@/types/attempt";

vi.mock("@/api/attempts", () => ({
  getAttemptResult: vi.fn(),
}));

const candidate: Candidate = {
  id: 7,
  email: "user@example.com",
  display_name: "测试用户",
  status: "active",
  token: "candidate-token",
  token_expires_at: "2099-01-01T00:00:00.000Z",
};

const result: AttemptResult = {
  attempt_id: 42,
  score: 80,
  total_score: 100,
  pass_score: 60,
  is_passed: true,
  show_answer_after_submit: true,
  correct_count: 1,
  wrong_count: 1,
  questions: [
    {
      attempt_question_id: 101,
      stem_snapshot: "第一道题的题干。",
      selected_answer: "A",
      correct_answer_snapshot: "A",
      analysis_snapshot: "第一题解析。",
      is_correct: true,
      score_awarded: 40,
      score: 40,
    },
    {
      attempt_question_id: 102,
      stem_snapshot: "第二道题的题干。",
      selected_answer: "B",
      correct_answer_snapshot: "C",
      analysis_snapshot: "第二题解析。",
      is_correct: false,
      score_awarded: 0,
      score: 60,
    },
  ],
};

function renderPage(entry = "/exams/1/result?attemptId=42") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[entry]}>
        <ExamResultPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ExamResultPage V2 Candidate Calm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.sessionStorage.clear();
    window.localStorage.clear();
    setCurrentCandidate(candidate);
    vi.mocked(getAttemptResult).mockResolvedValue(result);
  });

  it("renders the ordered summary, context, filters, and snapshot review", async () => {
    renderPage();

    expect(await screen.findByText("考试已交卷。")).toBeInTheDocument();
    expect(screen.getByTestId("result-summary")).toHaveAttribute("data-surface-owner", "summary");
    expect(screen.getAllByTestId("result-summary")).toHaveLength(1);
    expect(screen.getByText("80")).toBeInTheDocument();
    expect(screen.getByText("已通过")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "本次作答" })).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "答题回顾" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: "第 01 题" })).toBeInTheDocument();
    expect(screen.getAllByText("正确答案")).toHaveLength(2);
    expect(screen.getByText("第一题解析。")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "返回考试列表" })).toHaveAttribute("href", "/exams");

    const headings = screen.getAllByRole("heading");
    expect(headings.map((heading) => heading.tagName)).toEqual([
      "H1",
      "H2",
      "H2",
      "H2",
      "H3",
      "H3",
    ]);
  });

  it("keeps result filters accessible and preserves question order when narrowed", async () => {
    const user = userEvent.setup();
    renderPage();

    const allButton = await screen.findByRole("button", { name: /全部/ });
    const wrongButton = screen.getByRole("button", { name: /只看错题/ });
    expect(allButton).toHaveAttribute("aria-pressed", "true");
    expect(wrongButton).toHaveAttribute("aria-pressed", "false");

    await user.click(wrongButton);

    expect(allButton).toHaveAttribute("aria-pressed", "false");
    expect(wrongButton).toHaveAttribute("aria-pressed", "true");
    expect(screen.queryByRole("heading", { name: "第 01 题" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "第 02 题" })).toBeInTheDocument();
    expect(screen.getByText("第二道题的题干。")).toBeInTheDocument();
  });

  it("keeps the release gate closed when answer details are unavailable", async () => {
    vi.mocked(getAttemptResult).mockResolvedValueOnce({
      ...result,
      show_answer_after_submit: false,
      questions: [],
    });
    renderPage();

    expect(await screen.findByText("答案与解析尚未发布。")).toBeInTheDocument();
    expect(screen.getByTestId("result-release-gate")).toBeInTheDocument();
    expect(screen.queryByTestId("result-review")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /只看错题/ })).not.toBeInTheDocument();
    expect(screen.queryByText("正确答案")).not.toBeInTheDocument();
  });

  it("covers loading and recoverable error states without placeholder score truth", async () => {
    vi.mocked(getAttemptResult).mockReturnValueOnce(new Promise<AttemptResult>(() => {}));
    renderPage();
    expect(await screen.findByRole("status")).toHaveAttribute("aria-busy", "true");
    expect(screen.queryByText("考试已交卷。")).not.toBeInTheDocument();
    expect(screen.queryByText("80")).not.toBeInTheDocument();

    vi.clearAllMocks();
    vi.mocked(getAttemptResult).mockRejectedValueOnce(new Error("result unavailable"));
    renderPage();
    expect(await screen.findByRole("heading", { name: "答卷加载失败。" })).toBeInTheDocument();
    expect(screen.queryByText("考试已交卷。")).not.toBeInTheDocument();
  });

  it("wraps long result content without adding a competing surface", async () => {
    vi.mocked(getAttemptResult).mockResolvedValueOnce({
      ...result,
      questions: [
        {
          ...result.questions[0],
          stem_snapshot:
            "这是一段很长的中文题干以及unbroken-result-identifier-2026，应该保持在结果阅读区域内。",
          selected_answer: "A-very-long-unbroken-selected-answer-identifier",
          analysis_snapshot: "这是很长的解析文本，用于验证窄屏下仍然可以换行。",
        },
      ],
    });
    renderPage();

    const question = await screen.findByRole("heading", { name: "第 01 题" });
    expect(question).toHaveClass("min-w-0", "break-words");
    expect(screen.getByText(/unbroken-result-identifier-2026/)).toHaveClass("break-words");
    expect(screen.getByTestId("result-review")).not.toHaveAttribute("data-surface-owner");
  });
});
