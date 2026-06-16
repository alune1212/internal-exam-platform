import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type React from "react";
import { Outlet, RouterProvider, createMemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getAttempt, getAttemptResult, saveAttemptAnswers, submitAttempt } from "@/api/attempts";
import { ApiError } from "@/api/client";
import { getActiveExams, getExamRanking, startExam } from "@/api/exams";
import { getPracticeQuestions } from "@/api/questions";
import type { CandidateSessionContext } from "@/components/layout/CandidateLayout";
import { ExamResultPage } from "@/pages/ExamResultPage";
import { ExamTakingPage } from "@/pages/ExamTakingPage";
import { ExamListPage } from "@/pages/ExamListPage";
import { ExamStartPage } from "@/pages/ExamStartPage";
import { LoginPage } from "@/pages/LoginPage";
import { PracticePage } from "@/pages/PracticePage";
import { RankingPage } from "@/pages/RankingPage";
import type { Attempt, AttemptResult } from "@/types/attempt";
import type { Candidate } from "@/types/candidate";
import type { Exam } from "@/types/exam";
import type { Question } from "@/types/question";

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
  getExamRanking: vi.fn(),
  startExam: vi.fn(),
}));

vi.mock("@/api/questions", () => ({
  getPracticeQuestions: vi.fn(),
  submitPracticeAnswer: vi.fn(),
}));

const candidate: Candidate = {
  id: 1,
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
  show_ranking: true,
};

const secondExam: Exam = {
  ...exam,
  id: 2,
  title: "第二次内部考试",
};

const rankingRows = [
  {
    rank: 1,
    candidate_name: "张三",
    department: "综合管理部",
    score: 3,
    total_score: 749,
  },
  {
    rank: 2,
    candidate_name: "李四",
    department: "财务部",
    score: 0,
    total_score: 749,
  },
  {
    rank: 3,
    candidate_name: "王五",
    department: "运营部",
    score: 0,
    total_score: 749,
  },
];

const practiceQuestions: Question[] = [
  {
    id: 201,
    question_type: "single",
    stem: "练习题题干",
    score: 2,
    status: "active",
    options: [
      { id: 1, label: "A", content: "选项 A", is_correct: true, sort_order: 1 },
      { id: 2, label: "B", content: "选项 B", is_correct: false, sort_order: 2 },
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
    vi.mocked(getExamRanking).mockResolvedValue(rankingRows);
    vi.mocked(getPracticeQuestions).mockResolvedValue(practiceQuestions);
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

  it("renders ranking summary cards before the detailed ranking table", async () => {
    renderPage("exams/:examId/ranking", <RankingPage />, undefined, "exams/1/ranking");

    expect(await screen.findByText("榜单概览")).toBeInTheDocument();
    expect(screen.getByText("最高分")).toBeInTheDocument();
    expect(screen.getByText("平均分")).toBeInTheDocument();
    expect(screen.getByText("TOP 3")).toBeInTheDocument();
    expect(screen.getByText("明细排名")).toBeInTheDocument();
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
