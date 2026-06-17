import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type React from "react";
import { Outlet, RouterProvider, createMemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getAttempt, getAttemptResult, saveAttemptAnswers, submitAttempt } from "@/api/attempts";
import { ApiError } from "@/api/client";
import { getActiveExams, startExam } from "@/api/exams";
import { getPracticeQuestions, submitPracticeAnswer } from "@/api/questions";
import type { CandidateSessionContext } from "@/components/layout/CandidateLayout";
import { ExamResultPage } from "@/pages/ExamResultPage";
import { ExamTakingPage } from "@/pages/ExamTakingPage";
import { ExamListPage } from "@/pages/ExamListPage";
import { ExamStartPage } from "@/pages/ExamStartPage";
import { LoginPage } from "@/pages/LoginPage";
import { PracticePage } from "@/pages/PracticePage";
import type { Attempt, AttemptResult } from "@/types/attempt";
import type { Candidate } from "@/types/candidate";
import type { Exam } from "@/types/exam";
import type { PracticeQuestion } from "@/types/question";

vi.mock("@/api/auth", () => ({
  loginCandidate: vi.fn(),
}));

vi.mock("@/api/attempts", () => ({
  getAttempt: vi.fn(),
  getAttemptResult: vi.fn(),
  saveAttemptAnswers: vi.fn(),
  submitAttempt: vi.fn(),
}));

vi.mock("@/api/exams", () => ({
  getActiveExams: vi.fn(),
  startExam: vi.fn(),
}));

vi.mock("@/api/questions", () => ({
  getPracticeQuestions: vi.fn(),
  submitPracticeAnswer: vi.fn(),
}));

const candidate: Candidate = {
  id: 1,
  token: "candidate-token",
  name: "张敏",
  employee_no: "E1001",
  department: "产品部",
  should_attend: true,
  status: "active",
};

const attempt: Attempt = {
  id: 10,
  exam_id: 1,
  candidate_id: 1,
  status: "in_progress",
  started_at: new Date(Date.now() - 60_000).toISOString(),
  duration_minutes: 30,
  ends_at: new Date(Date.now() + 29 * 60_000).toISOString(),
  server_now: new Date().toISOString(),
  score: 0,
  total_score: 4,
  correct_count: 0,
  wrong_count: 0,
  questions: [
    {
      id: 101,
      question_type: "single",
      stem_snapshot: "首都是哪里？",
      options_snapshot: [
        { label: "A", content: "北京", sort_order: 1 },
        { label: "B", content: "上海", sort_order: 2 },
      ],
      score: 2,
      sort_order: 1,
      selected_answer: "A",
    },
  ],
};

const result: AttemptResult = {
  attempt_id: 10,
  score: 2,
  total_score: 4,
  show_answer_after_submit: true,
  correct_count: 1,
  wrong_count: 1,
  questions: [
    {
      attempt_question_id: 101,
      stem_snapshot: "首都是哪里？",
      selected_answer: "A",
      correct_answer_snapshot: "A",
      analysis_snapshot: "北京是首都。",
      is_correct: true,
      score_awarded: 2,
      score: 2,
    },
  ],
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

const secondExam: Exam = {
  ...exam,
  id: 2,
  title: "第二次内部考试",
};

const practiceQuestions: PracticeQuestion[] = [
  {
    id: 201,
    question_type: "single",
    stem: "练习题题干",
    score: 2,
    status: "active",
    options: [
      { id: 1, label: "A", content: "选项 A", sort_order: 1 },
      { id: 2, label: "B", content: "选项 B", sort_order: 2 },
    ],
  },
];

function renderPage(
  path: string,
  element: React.ReactElement,
  context?: CandidateSessionContext,
  initialEntry = path,
) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const router = createMemoryRouter(
    [
      {
        path: "/",
        element: <Outlet context={context ?? null} />,
        children: [{ path, element }],
      },
    ],
    { initialEntries: [`/${initialEntry}`] },
  );

  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("P0 pages", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getAttempt).mockResolvedValue(attempt);
    vi.mocked(getAttemptResult).mockResolvedValue(result);
    vi.mocked(getActiveExams).mockResolvedValue([exam]);
    vi.mocked(getPracticeQuestions).mockResolvedValue(practiceQuestions);
    vi.mocked(submitPracticeAnswer).mockResolvedValue({
      question_id: 201,
      selected_answer: "A",
      correct_answer: "A",
      is_correct: true,
      score_awarded: 2,
      score: 2,
      analysis: "解析",
    });
    vi.mocked(saveAttemptAnswers).mockResolvedValue({ saved_count: 1, saved_at: "2026-06-14" });
    vi.mocked(submitAttempt).mockResolvedValue(result);
    vi.mocked(startExam).mockResolvedValue({ attempt_id: 10 } as Awaited<
      ReturnType<typeof startExam>
    >);
  });

  it("renders the Phase 5 login chapter and bilingual name label", () => {
    renderPage("login", <LoginPage />, {
      candidate: null,
      loginCandidate: vi.fn(),
      logoutCandidate: vi.fn(),
    });

    expect(screen.getByText("CHAPTER 01 · WELCOME")).toBeInTheDocument();
    expect(screen.getByText(/报上姓名/)).toBeInTheDocument();
    expect(screen.getByText(/姓名 ·/)).toBeInTheDocument();
  });

  it("renders the exam taking page with focus-mode progress and option cards", async () => {
    renderPage(
      "exams/:examId/taking",
      <ExamTakingPage />,
      undefined,
      "exams/1/taking?attemptId=10",
    );

    expect((await screen.findAllByText(/Q\s*01\s*\/\s*01/)).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("radio", { name: /选项 A：北京/ }).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/CHAPTER 01 · 单选 · 2 分/).length).toBeGreaterThan(0);
  });

  it("uses submit as the final-question primary action", async () => {
    const user = userEvent.setup();
    vi.mocked(submitAttempt).mockReturnValue(new Promise(() => {}));

    renderPage(
      "exams/:examId/taking",
      <ExamTakingPage />,
      undefined,
      "exams/1/taking?attemptId=10",
    );

    await screen.findAllByRole("radio", { name: /选项 A：北京/ });

    const submitButtons = screen.getAllByRole("button", { name: "提交试卷" });
    expect(submitButtons.length).toBeGreaterThan(0);
    submitButtons.forEach((button) => expect(button).toBeEnabled());

    await user.click(submitButtons[0]);

    await waitFor(() => expect(submitAttempt).toHaveBeenCalledWith("10", "manual"));
  });

  it("waits for queued autosave before final exam submit and ignores duplicate submits", async () => {
    const user = userEvent.setup();
    let resolveFirstSave: (value: { saved_count: number; saved_at: string }) => void = () => {};
    const firstSave = new Promise<{ saved_count: number; saved_at: string }>((resolve) => {
      resolveFirstSave = resolve;
    });
    vi.mocked(saveAttemptAnswers)
      .mockImplementationOnce(() => firstSave)
      .mockResolvedValue({ saved_count: 1, saved_at: "2026-06-14" });
    vi.mocked(submitAttempt).mockReturnValue(new Promise(() => {}));

    renderPage(
      "exams/:examId/taking",
      <ExamTakingPage />,
      undefined,
      "exams/1/taking?attemptId=10",
    );

    const optionB = await screen.findAllByRole("radio", { name: /选项 B：上海/ });
    await user.click(optionB[0]);

    await waitFor(() => expect(saveAttemptAnswers).toHaveBeenCalledTimes(1));
    const submitButton = screen.getByRole("button", { name: /提前交卷/ });
    await user.click(submitButton);
    await user.click(submitButton);

    expect(submitAttempt).not.toHaveBeenCalled();
    expect(saveAttemptAnswers).toHaveBeenCalledTimes(1);

    resolveFirstSave({ saved_count: 1, saved_at: "2026-06-14" });

    await waitFor(() => expect(submitAttempt).toHaveBeenCalledTimes(1));
    expect(submitAttempt).toHaveBeenCalledWith("10", "manual");
    expect(saveAttemptAnswers).toHaveBeenLastCalledWith("10", [
      { attempt_question_id: 101, selected_answer: "B" },
    ]);
  });

  it("selects the current exam option with an A-D keyboard shortcut", async () => {
    const user = userEvent.setup();

    renderPage(
      "exams/:examId/taking",
      <ExamTakingPage />,
      undefined,
      "exams/1/taking?attemptId=10",
    );

    await screen.findAllByRole("radio", { name: /选项 B：上海/ });
    await user.keyboard("b");

    await waitFor(() =>
      expect(saveAttemptAnswers).toHaveBeenCalledWith("10", [
        { attempt_question_id: 101, selected_answer: "B" },
      ]),
    );
  });

  it("renders the exam result page black-card result copy and filter controls", async () => {
    renderPage(
      "exams/:examId/result",
      <ExamResultPage />,
      undefined,
      "exams/1/result?attemptId=10",
    );

    expect(await screen.findByText("考试结束。")).toBeInTheDocument();
    expect(screen.getByText("YOUR SCORE · 你的分数")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /只看错题/ })).toBeInTheDocument();
  });

  it("hides correct answer and analysis when the exam disables review", async () => {
    vi.mocked(getAttemptResult).mockResolvedValue({
      ...result,
      show_answer_after_submit: false,
      questions: [
        {
          ...result.questions[0],
          correct_answer_snapshot: null,
          analysis_snapshot: null,
        },
      ],
    });

    renderPage(
      "exams/:examId/result",
      <ExamResultPage />,
      undefined,
      "exams/1/result?attemptId=10",
    );

    expect(await screen.findByText("答题结果")).toBeInTheDocument();
    expect(screen.queryByText("正确答案")).not.toBeInTheDocument();
    expect(screen.queryByText("北京是首都。")).not.toBeInTheDocument();
  });

  it("renders the practice focus page with submit affordance", async () => {
    renderPage("practice", <PracticePage />, {
      candidate,
      loginCandidate: vi.fn(),
      logoutCandidate: vi.fn(),
    });

    expect(await screen.findByText(/刷一遍/)).toBeInTheDocument();
    expect(await screen.findByText(/记一遍/)).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "提交本题" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("radio", { name: /选项 A：选项 A/ }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("region", { name: "题号导航" })[0].parentElement).toHaveClass(
      "lg:sticky",
      "lg:top-24",
    );
  });

  it("submits practice answers without candidate_id in the request payload", async () => {
    const user = userEvent.setup();
    renderPage("practice", <PracticePage />, {
      candidate,
      loginCandidate: vi.fn(),
      logoutCandidate: vi.fn(),
    });

    const optionA = await screen.findAllByRole("radio", { name: /选项 A：选项 A/ });
    await user.click(optionA[0]);
    await user.click(screen.getAllByRole("button", { name: "提交本题" })[0]);

    await waitFor(() => expect(submitPracticeAnswer).toHaveBeenCalled());
    expect(vi.mocked(submitPracticeAnswer).mock.calls[0][0]).toEqual({
      question_id: 201,
      selected_answer: "A",
    });
  });

  it("shows practice loading state before empty copy while questions are loading", async () => {
    vi.mocked(getPracticeQuestions).mockReturnValue(new Promise(() => {}));

    renderPage("practice", <PracticePage />, {
      candidate,
      loginCandidate: vi.fn(),
      logoutCandidate: vi.fn(),
    });

    expect(await screen.findByRole("status")).toBeInTheDocument();
    expect(screen.queryByText("暂无题目")).not.toBeInTheDocument();
  });

  it("renders the exam list heading and question count from the active exam rule", async () => {
    vi.mocked(getActiveExams).mockResolvedValue([exam]);

    renderPage("exams", <ExamListPage />);

    expect(await screen.findByText("今天有一场考试等着你。")).toBeInTheDocument();
    const questionCounts = screen.getAllByText("50");
    expect(questionCounts.length).toBeGreaterThan(0);
    expect(screen.getAllByText("100").length).toBeGreaterThan(0);
  });

  it("shows not-started and ended availability states in the exam list", async () => {
    vi.mocked(getActiveExams).mockResolvedValue([
      {
        ...exam,
        id: 3,
        title: "稍后开放",
        available_from: new Date(Date.now() + 60_000).toISOString(),
      },
      {
        ...exam,
        id: 4,
        title: "已经结束",
        available_until: new Date(Date.now() - 60_000).toISOString(),
      },
    ]);

    renderPage("exams", <ExamListPage />);

    expect(await screen.findByText("稍后开放")).toBeInTheDocument();
    expect(screen.getByText("未开始")).toBeInTheDocument();
    expect(screen.getByText("已结束")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "不可进入" }).length).toBe(2);
  });

  it("links in-progress exams directly to the existing attempt", async () => {
    vi.mocked(getActiveExams).mockResolvedValue([
      {
        ...exam,
        latest_attempt_id: 10,
        latest_attempt_status: "in_progress",
      },
    ]);

    renderPage("exams", <ExamListPage />);

    expect(await screen.findByRole("link", { name: /继续考试/ })).toHaveAttribute(
      "href",
      "/exams/1/taking?attemptId=10",
    );
  });

  it("pluralizes the exam list heading based on the number of active exams", async () => {
    vi.mocked(getActiveExams).mockResolvedValue([exam, secondExam]);

    renderPage("exams", <ExamListPage />);

    expect(await screen.findByText("今天有 2 场考试等着你。")).toBeInTheDocument();
  });

  it("falls back to the empty-state heading when there are no active exams", async () => {
    vi.mocked(getActiveExams).mockResolvedValue([]);

    renderPage("exams", <ExamListPage />);

    expect(await screen.findByText("今天暂无考试安排。")).toBeInTheDocument();
    expect(screen.getByText("暂无可参加考试。")).toBeInTheDocument();
  });

  it("shows the actual API error when starting an exam fails", async () => {
    const user = userEvent.setup();
    vi.mocked(startExam).mockRejectedValueOnce(
      new ApiError("考生已有进行中的考试记录 #9", 409, "考生已有进行中的考试记录 #9"),
    );

    renderPage("exams/:examId/start", <ExamStartPage />, {
      candidate,
      loginCandidate: vi.fn(),
      logoutCandidate: vi.fn(),
    });

    const startButton = await screen.findByRole("button", { name: /开始考试/ });
    await user.click(startButton);

    expect(await screen.findByText("考生已有进行中的考试记录 #9")).toBeInTheDocument();
    expect(screen.queryByText("请确认考试仍处于发布状态。")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "继续考试" })).toBeInTheDocument();
  });

  it("does not offer continue action after the exam was already submitted", async () => {
    const user = userEvent.setup();
    vi.mocked(startExam).mockRejectedValueOnce(
      new ApiError("考试记录 #10 已提交", 409, "考试记录 #10 已提交"),
    );

    renderPage("exams/:examId/start", <ExamStartPage />, {
      candidate,
      loginCandidate: vi.fn(),
      logoutCandidate: vi.fn(),
    });

    const startButton = await screen.findByRole("button", { name: /开始考试/ });
    await user.click(startButton);

    expect(await screen.findByText("考试记录 #10 已提交")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "继续考试" })).not.toBeInTheDocument();
  });

  it("blocks submitted attempts from re-entering the taking page", async () => {
    vi.mocked(getAttempt).mockResolvedValue({ ...attempt, status: "submitted" });
    const router = createMemoryRouter(
      [
        { path: "/exams/:examId/taking", element: <ExamTakingPage /> },
        { path: "/exams/:examId/result", element: <div>结果页</div> },
      ],
      { initialEntries: ["/exams/1/taking?attemptId=10"] },
    );

    render(
      <QueryClientProvider
        client={
          new QueryClient({
            defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
          })
        }
      >
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("考试已提交。")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "查看成绩" })).toHaveAttribute(
      "href",
      "/exams/1/result?attemptId=10",
    );
    expect(screen.queryByRole("button", { name: "提交试卷" })).not.toBeInTheDocument();
  });

  it("falls back to a generic message when the start-exam error has no detail", async () => {
    const user = userEvent.setup();
    vi.mocked(startExam).mockRejectedValueOnce(new Error("network down"));

    renderPage("exams/:examId/start", <ExamStartPage />, {
      candidate,
      loginCandidate: vi.fn(),
      logoutCandidate: vi.fn(),
    });

    const startButton = await screen.findByRole("button", { name: /开始考试/ });
    await user.click(startButton);

    expect(await screen.findByText("network down")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "继续考试" })).not.toBeInTheDocument();
  });
});
