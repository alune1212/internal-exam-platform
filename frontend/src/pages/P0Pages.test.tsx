import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type React from "react";
import { Outlet, RouterProvider, createMemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getAttempt, getAttemptResult, saveAttemptAnswers, submitAttempt } from "@/api/attempts";
import { ApiError } from "@/api/client";
import { getActiveExams, startExam } from "@/api/exams";
import { getPracticeQuestions, submitPracticeAnswer } from "@/api/questions";
import type { CandidateSessionContext } from "@/components/layout/CandidateLayout";
import { clearCurrentCandidate, setCurrentCandidate } from "@/lib/candidateSession";
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
    window.localStorage.clear();
    window.sessionStorage.clear();
    clearCurrentCandidate();
    vi.mocked(getAttempt).mockResolvedValue(attempt);
    vi.mocked(getAttemptResult).mockResolvedValue(result);
    vi.mocked(getActiveExams).mockResolvedValue([exam]);
    vi.mocked(getPracticeQuestions).mockResolvedValue(practiceQuestions);
    vi.mocked(submitPracticeAnswer).mockResolvedValue({
      question_id: 201,
      selected_answer: "A",
      score: 2,
    });
    vi.mocked(saveAttemptAnswers).mockResolvedValue({ saved_count: 1, saved_at: "2026-06-14" });
    vi.mocked(submitAttempt).mockResolvedValue(result);
    vi.mocked(startExam).mockResolvedValue({ attempt_id: 10 } as Awaited<
      ReturnType<typeof startExam>
    >);
  });

  it("renders the clean candidate login copy and name field", () => {
    renderPage("login", <LoginPage />, {
      candidate: null,
      loginCandidate: vi.fn(),
      logoutCandidate: vi.fn(),
    });

    expect(screen.getByTestId("candidate-login-header")).toBeInTheDocument();
    expect(screen.getByText("EXAM TAKER · 登录")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "入场核验" })).toHaveClass(
      "font-display",
      "text-display-lg",
    );
    expect(screen.getByLabelText("姓名")).toBeInTheDocument();
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
    expect(screen.queryByRole("contentinfo")).not.toBeInTheDocument();
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
    expect(screen.getAllByText(/QUESTION 01 · 单选 · 2 分/).length).toBeGreaterThan(0);
  });

  it("shows exam-taking loading before rendering the focus mode", async () => {
    vi.mocked(getAttempt).mockReturnValue(new Promise<Attempt>(() => {}));

    renderPage(
      "exams/:examId/taking",
      <ExamTakingPage />,
      undefined,
      "exams/1/taking?attemptId=10",
    );

    expect(await screen.findByRole("status")).toBeInTheDocument();
    expect(screen.queryByText(/Q\s*01\s*\/\s*01/)).not.toBeInTheDocument();
  });

  it("shows an explicit empty state when an attempt has no questions", async () => {
    vi.mocked(getAttempt).mockResolvedValue({ ...attempt, questions: [] });

    renderPage(
      "exams/:examId/taking",
      <ExamTakingPage />,
      undefined,
      "exams/1/taking?attemptId=10",
    );

    expect(await screen.findByRole("heading", { name: "本次考试暂无题目。" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "交卷" })).not.toBeInTheDocument();
  });

  it("shows the not-started state when entering the taking page without an attempt", () => {
    renderPage("exams/:examId/taking", <ExamTakingPage />, undefined, "exams/1/taking");

    expect(screen.getByText("STATE · 未开始")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "未开始考试。" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "返回考试说明" })).toHaveAttribute(
      "href",
      "/exams/1/start",
    );
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

    const submitButtons = screen.getAllByRole("button", { name: "交卷" });
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
    const submitButton = screen.getAllByRole("button", { name: "交卷" })[0];
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

  it("shows visible autosave failure and retries the latest answer snapshot", async () => {
    const user = userEvent.setup();
    vi.mocked(saveAttemptAnswers)
      .mockRejectedValueOnce(new ApiError("保存失败", 409, "保存失败"))
      .mockResolvedValue({ saved_count: 1, saved_at: "2026-06-14" });

    renderPage(
      "exams/:examId/taking",
      <ExamTakingPage />,
      undefined,
      "exams/1/taking?attemptId=10",
    );

    const optionB = await screen.findAllByRole("radio", { name: /选项 B：上海/ });
    await user.click(optionB[0]);

    expect(await screen.findByText("保存失败")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "重试保存" }));

    await waitFor(() => expect(saveAttemptAnswers).toHaveBeenCalledTimes(2));
    expect(saveAttemptAnswers).toHaveBeenLastCalledWith("10", [
      { attempt_question_id: 101, selected_answer: "B" },
    ]);
  });

  it("uses the public manual submit contract when the exam timer expires", async () => {
    const expiredAt = new Date().toISOString();
    vi.mocked(getAttempt).mockResolvedValue({
      ...attempt,
      ends_at: expiredAt,
      server_now: expiredAt,
    });
    vi.mocked(submitAttempt).mockReturnValue(new Promise(() => {}));

    renderPage(
      "exams/:examId/taking",
      <ExamTakingPage />,
      undefined,
      "exams/1/taking?attemptId=10",
    );

    await waitFor(() => expect(submitAttempt).toHaveBeenCalledWith("10", "manual"));
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

    expect(await screen.findByText("考试已交卷。")).toBeInTheDocument();
    expect(screen.getByText("SCORE · 得分")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /只看错题/ })).toBeInTheDocument();
  });

  it("keeps one result page h1 and exposes selected filter state", async () => {
    const user = userEvent.setup();
    renderPage(
      "exams/:examId/result",
      <ExamResultPage />,
      undefined,
      "exams/1/result?attemptId=10",
    );

    expect(await screen.findByText("考试已交卷。")).toBeInTheDocument();
    const h1s = screen.getAllByRole("heading", { level: 1 });
    expect(h1s).toHaveLength(1);
    expect(h1s[0]).toHaveTextContent("本次答卷");

    const allButton = screen.getByRole("button", { name: /全部/ });
    const wrongButton = screen.getByRole("button", { name: /只看错题/ });
    expect(allButton).toHaveAttribute("aria-pressed", "true");
    expect(wrongButton).toHaveAttribute("aria-pressed", "false");

    await user.click(wrongButton);

    expect(allButton).toHaveAttribute("aria-pressed", "false");
    expect(wrongButton).toHaveAttribute("aria-pressed", "true");
  });

  it("renders result query failures as explicit errors", async () => {
    vi.mocked(getAttemptResult).mockRejectedValueOnce(new Error("result unavailable"));

    renderPage(
      "exams/:examId/result",
      <ExamResultPage />,
      undefined,
      "exams/1/result?attemptId=10",
    );

    expect(await screen.findByRole("heading", { name: "答卷加载失败。" })).toBeInTheDocument();
    expect(screen.queryByText("考试已交卷。")).not.toBeInTheDocument();
    expect(screen.queryByText("SCORE · 得分")).not.toBeInTheDocument();
    expect(screen.queryByText("暂无结果，请先完成考试。")).not.toBeInTheDocument();
  });

  it("shows result loading without default score placeholders", async () => {
    vi.mocked(getAttemptResult).mockReturnValue(new Promise<AttemptResult>(() => {}));

    renderPage(
      "exams/:examId/result",
      <ExamResultPage />,
      undefined,
      "exams/1/result?attemptId=10",
    );

    expect(await screen.findByRole("status")).toBeInTheDocument();
    expect(screen.queryByText("考试已交卷。")).not.toBeInTheDocument();
    expect(screen.queryByText("SCORE · 得分")).not.toBeInTheDocument();
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

    expect(await screen.findByText("日常练习")).toBeInTheDocument();
    expect(screen.getByText("PRACTICE · 练习")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "提交本题" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("radio", { name: /选项 A：选项 A/ }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("region", { name: "题号导航" })[0].parentElement).toHaveClass(
      "lg:sticky",
      "lg:top-24",
    );
  });

  it("renders practice query failures as explicit errors", async () => {
    vi.mocked(getPracticeQuestions).mockRejectedValueOnce(new Error("practice unavailable"));

    renderPage("practice", <PracticePage />, {
      candidate,
      loginCandidate: vi.fn(),
      logoutCandidate: vi.fn(),
    });

    expect(await screen.findByRole("heading", { name: "练习暂不可用。" })).toBeInTheDocument();
    expect(screen.queryByText("暂无可练习题目")).not.toBeInTheDocument();
  });

  it("renders practice empty state after an empty question response", async () => {
    vi.mocked(getPracticeQuestions).mockResolvedValueOnce([]);

    renderPage("practice", <PracticePage />, {
      candidate,
      loginCandidate: vi.fn(),
      logoutCandidate: vi.fn(),
    });

    expect(await screen.findByRole("heading", { name: "暂无可练习题目" })).toBeInTheDocument();
    expect(screen.queryByText("日常练习")).not.toBeInTheDocument();
  });

  it("does not fetch practice questions before candidate login", () => {
    renderPage("practice", <PracticePage />, {
      candidate: null,
      loginCandidate: vi.fn(),
      logoutCandidate: vi.fn(),
    });

    expect(screen.getByText("STATE · 未登录")).toBeInTheDocument();
    expect(getPracticeQuestions).not.toHaveBeenCalled();
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
    setCurrentCandidate(candidate);
    vi.mocked(getActiveExams).mockResolvedValue([exam]);

    renderPage("exams", <ExamListPage />);

    expect(await screen.findByTestId("candidate-exam-list-shell")).toHaveClass("gap-8");
    expect(await screen.findByText("待完成的考试")).toBeInTheDocument();
    expect(screen.getByText("EXAMS · 考试")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "内部考试" })).not.toHaveClass("tracking-[-0.04em]");
    const questionCounts = screen.getAllByText("50");
    expect(questionCounts.length).toBeGreaterThan(0);
    expect(screen.getAllByText("100").length).toBeGreaterThan(0);
  });

  it("renders active exam query failures as explicit errors", async () => {
    setCurrentCandidate(candidate);
    vi.mocked(getActiveExams).mockRejectedValueOnce(new Error("exam list unavailable"));

    renderPage("exams", <ExamListPage />);

    expect(await screen.findByRole("heading", { name: "考试列表加载失败。" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "待完成的考试" })).toBeInTheDocument();
    expect(screen.queryByText("今天暂无考试安排。")).not.toBeInTheDocument();
  });

  it("does not request active exams without a candidate session", async () => {
    renderPage("exams", <ExamListPage />);

    await act(async () => {});

    expect(getActiveExams).not.toHaveBeenCalled();
  });

  it("shows not-started and ended availability states in the exam list", async () => {
    setCurrentCandidate(candidate);
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
    expect(screen.getByText("NOT OPEN · 未开放")).toBeInTheDocument();
    expect(screen.getByText("ENDED · 已结束")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "不可进入" }).length).toBe(2);
  });

  it("links in-progress exams directly to the existing attempt", async () => {
    setCurrentCandidate(candidate);
    vi.mocked(getActiveExams).mockResolvedValue([
      {
        ...exam,
        latest_attempt_id: 10,
        latest_attempt_status: "in_progress",
        availability_status: "ended",
        available_until: new Date(Date.now() - 60_000).toISOString(),
      },
    ]);

    renderPage("exams", <ExamListPage />);

    expect(await screen.findByRole("link", { name: /继续考试/ })).toHaveAttribute(
      "href",
      "/exams/1/taking?attemptId=10",
    );
  });

  it("keeps the exam list heading stable with multiple active exams", async () => {
    setCurrentCandidate(candidate);
    vi.mocked(getActiveExams).mockResolvedValue([exam, secondExam]);

    renderPage("exams", <ExamListPage />);

    expect(await screen.findByText("待完成的考试")).toBeInTheDocument();
  });

  it("falls back to the empty-state heading when there are no active exams", async () => {
    setCurrentCandidate(candidate);
    vi.mocked(getActiveExams).mockResolvedValue([]);

    renderPage("exams", <ExamListPage />);

    expect(await screen.findByRole("heading", { name: "暂无待完成考试。" })).toBeInTheDocument();
  });

  it("shows the actual API error when starting an exam fails", async () => {
    const user = userEvent.setup();
    vi.mocked(startExam).mockRejectedValueOnce(
      new ApiError("考试人已有进行中的考试记录 #9", 409, "考试人已有进行中的考试记录 #9"),
    );

    renderPage("exams/:examId/start", <ExamStartPage />, {
      candidate,
      loginCandidate: vi.fn(),
      logoutCandidate: vi.fn(),
    });

    const startButton = await screen.findByRole("button", { name: /开始考试/ });
    await user.click(startButton);

    expect(await screen.findByText("考试人已有进行中的考试记录 #9")).toBeInTheDocument();
    expect(screen.queryByText("请确认考试仍处于发布状态。")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "继续考试" })).toBeInTheDocument();
  });

  it("does not offer continue action after the exam was already handed in", async () => {
    const user = userEvent.setup();
    vi.mocked(startExam).mockRejectedValueOnce(
      new ApiError("考试记录 #10 已交卷", 409, "考试记录 #10 已交卷"),
    );

    renderPage("exams/:examId/start", <ExamStartPage />, {
      candidate,
      loginCandidate: vi.fn(),
      logoutCandidate: vi.fn(),
    });

    const startButton = await screen.findByRole("button", { name: /开始考试/ });
    await user.click(startButton);

    expect(await screen.findByText("考试记录 #10 已交卷")).toBeInTheDocument();
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

    expect(await screen.findByText("考试已交卷。")).toBeInTheDocument();
    expect(screen.getByText("STATE · 已交卷")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "查看成绩" })).toHaveAttribute(
      "href",
      "/exams/1/result?attemptId=10",
    );
    expect(screen.queryByRole("button", { name: "交卷" })).not.toBeInTheDocument();
  });

  it("renders attempt query failures as explicit errors instead of indefinite loading", async () => {
    vi.mocked(getAttempt).mockRejectedValueOnce(
      new ApiError("考试记录不可用", 404, "考试记录不可用"),
    );

    renderPage(
      "exams/:examId/taking",
      <ExamTakingPage />,
      undefined,
      "exams/1/taking?attemptId=10",
    );

    expect(await screen.findByRole("heading", { name: "考试加载失败。" })).toBeInTheDocument();
    expect(screen.getByText("考试记录不可用")).toBeInTheDocument();
    expect(screen.queryByText("Q 01 / 01")).not.toBeInTheDocument();
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
