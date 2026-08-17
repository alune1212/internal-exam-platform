import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type React from "react";
import { Link, Outlet, RouterProvider, createMemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  getAttempt,
  getAttemptResult,
  saveAttemptAnswers,
  submitAttempt,
  takeoverAttempt,
} from "@/api/attempts";
import { requestCandidateLoginOtp, verifyCandidateLoginOtp } from "@/api/auth";
import { ApiError } from "@/api/client";
import { getActiveExams, startExam } from "@/api/exams";
import {
  getPracticeQuestions,
  getWrongPracticeQuestions,
  submitPracticeAnswer,
} from "@/api/questions";
import type { CandidateSessionContext } from "@/components/layout/CandidateLayout";
import { writeAttemptDraft } from "@/lib/attemptDraft";
import { clearAttemptSession, getAttemptSession, setAttemptSession } from "@/lib/attemptSession";
import { clearCurrentCandidate, setCurrentCandidate } from "@/lib/candidateSession";
import { ExamResultPage } from "@/pages/ExamResultPage";
import { ExamTakingPage } from "@/pages/ExamTakingPage";
import { ExamListPage } from "@/pages/ExamListPage";
import { ExamStartPage } from "@/pages/ExamStartPage";
import { LoginPage } from "@/pages/LoginPage";
import { PracticePage } from "@/pages/PracticePage";
import { WrongQuestionReviewPage } from "@/pages/WrongQuestionReviewPage";
import type { Attempt, AttemptResult } from "@/types/attempt";
import type { Candidate } from "@/types/candidate";
import type { Exam } from "@/types/exam";
import type { PracticeQuestion } from "@/types/question";

vi.mock("@/api/auth", () => ({
  requestCandidateLoginOtp: vi.fn(),
  verifyCandidateLoginOtp: vi.fn(),
}));

vi.mock("@/api/attempts", () => ({
  getAttempt: vi.fn(),
  getAttemptResult: vi.fn(),
  saveAttemptAnswers: vi.fn(),
  submitAttempt: vi.fn(),
  takeoverAttempt: vi.fn(),
}));

vi.mock("@/api/exams", () => ({
  getActiveExams: vi.fn(),
  startExam: vi.fn(),
}));

vi.mock("@/api/questions", () => ({
  getPracticeQuestions: vi.fn(),
  getWrongPracticeQuestions: vi.fn(),
  submitPracticeAnswer: vi.fn(),
}));

const candidate: Candidate = {
  id: 1,
  token: "candidate-token",
  token_expires_at: "2099-01-01T00:00:00.000Z",
  email: "zhangmin@example.com",
  display_name: "张敏",
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
  attempt_session_generation: 1,
  answer_revision: 0,
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
  const childRoutes = [{ path, element }];
  if (path !== "exams") {
    childRoutes.push({ path: "exams", element: <div>考试列表</div> });
  }
  if (path !== "exams/:examId/result") {
    childRoutes.push({ path: "exams/:examId/result", element: <div>结果页</div> });
  }
  const router = createMemoryRouter(
    [
      {
        path: "/",
        element: <Outlet context={context ?? null} />,
        children: childRoutes,
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
    setCurrentCandidate(candidate);
    setAttemptSession({
      candidateId: candidate.id,
      attemptId: attempt.id,
      credential: "attempt-credential",
      generation: 1,
      answerRevision: 0,
    });
    vi.mocked(getAttempt).mockResolvedValue(attempt);
    vi.mocked(getAttemptResult).mockResolvedValue(result);
    vi.mocked(getActiveExams).mockResolvedValue([exam]);
    vi.mocked(getPracticeQuestions).mockResolvedValue(practiceQuestions);
    vi.mocked(submitPracticeAnswer).mockResolvedValue({
      practice_answer_id: 1,
      question_id: 201,
      selected_answer: "A",
      score: 2,
      is_correct: true,
      correct_answer: "A",
      analysis: "选项 A 是正确答案。",
      option_comparison: [
        { label: "A", content: "选项 A", selected: true, correct: true },
        { label: "B", content: "选项 B", selected: false, correct: false },
      ],
    });
    vi.mocked(getWrongPracticeQuestions).mockResolvedValue([
      {
        question_id: 201,
        question_type: "single",
        stem: "练习题题干",
        category_1: "安全",
        category_2: "账号",
        status: "active",
        correct_answer: "A",
        analysis: "选项 A 是正确答案。",
        incorrect_count: 1,
        total_attempts: 2,
        mastered: true,
        latest_practiced_at: "2026-07-21T08:00:00Z",
        history: [
          {
            practice_answer_id: 1,
            selected_answer: "B",
            is_correct: false,
            practiced_at: "2026-07-21T07:00:00Z",
          },
          {
            practice_answer_id: 2,
            selected_answer: "A",
            is_correct: true,
            practiced_at: "2026-07-21T08:00:00Z",
          },
        ],
        options: [
          { label: "A", content: "选项 A", selected: true, correct: true },
          { label: "B", content: "选项 B", selected: false, correct: false },
        ],
      },
    ]);
    vi.mocked(saveAttemptAnswers).mockResolvedValue({
      saved_count: 1,
      saved_at: "2026-06-14",
      answer_revision: 1,
    });
    vi.mocked(submitAttempt).mockResolvedValue(result);
    vi.mocked(takeoverAttempt).mockResolvedValue({
      attempt_id: 10,
      attempt_session_credential: "replacement-credential",
      attempt_session_generation: 2,
      answer_revision: 1,
      ends_at: attempt.ends_at,
    });
    vi.mocked(startExam).mockResolvedValue({ attempt_id: 10 } as Awaited<
      ReturnType<typeof startExam>
    >);
    vi.mocked(requestCandidateLoginOtp).mockResolvedValue({
      challenge_id: 7,
      expires_at: "2026-07-03T08:10:00Z",
      resend_available_at: "2026-07-03T08:01:00Z",
    });
    vi.mocked(verifyCandidateLoginOtp).mockResolvedValue({
      outcome: "authenticated",
      account: {
        id: candidate.id,
        email: candidate.email,
        display_name: candidate.display_name,
        status: candidate.status,
      },
      token: candidate.token,
      token_expires_at: candidate.token_expires_at,
    });
  });

  it("renders the clean candidate login copy with email OTP fields", () => {
    renderPage("login", <LoginPage />, {
      candidate: null,
      loginCandidate: vi.fn(),
      logoutCandidate: vi.fn(),
    });

    expect(screen.getByTestId("candidate-login-header")).toBeInTheDocument();
    expect(screen.getByText("用户入口")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "邮箱登录" })).toHaveClass(
      "font-display",
      "text-display-lg",
    );
    expect(screen.getByLabelText("邮箱")).toBeInTheDocument();
    expect(screen.queryByLabelText("员工号（可选）")).not.toBeInTheDocument();
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
    expect(screen.queryByRole("contentinfo")).not.toBeInTheDocument();
  });

  it("requests an email OTP before showing the verification step", async () => {
    const user = userEvent.setup();
    renderPage("login", <LoginPage />, {
      candidate: null,
      loginCandidate: vi.fn(),
      logoutCandidate: vi.fn(),
    });

    await user.type(screen.getByLabelText("邮箱"), "zhangmin@example.com");
    await user.click(screen.getByRole("button", { name: "发送验证码" }));

    await waitFor(() => expect(requestCandidateLoginOtp).toHaveBeenCalled());
    expect(vi.mocked(requestCandidateLoginOtp).mock.calls[0][0]).toEqual({
      email: "zhangmin@example.com",
    });
    expect(screen.getByLabelText("验证码")).toBeInTheDocument();
    expect(screen.queryByText("已识别：张敏")).not.toBeInTheDocument();
  });

  it("verifies the OTP before storing the candidate session", async () => {
    const user = userEvent.setup();
    const loginCandidate = vi.fn();
    renderPage("login", <LoginPage />, {
      candidate: null,
      loginCandidate,
      logoutCandidate: vi.fn(),
    });

    await user.type(screen.getByLabelText("邮箱"), "zhangmin@example.com");
    await user.click(screen.getByRole("button", { name: "发送验证码" }));
    await user.type(await screen.findByLabelText("验证码"), "123456");
    await user.click(screen.getByRole("button", { name: "验证并继续" }));

    await waitFor(() => expect(verifyCandidateLoginOtp).toHaveBeenCalled());
    expect(vi.mocked(verifyCandidateLoginOtp).mock.calls[0][0]).toEqual({
      challenge_id: 7,
      otp: "123456",
    });
    expect(loginCandidate).toHaveBeenCalledWith(candidate);
  });

  it("shows a neutral OTP verification error", async () => {
    const user = userEvent.setup();
    vi.mocked(verifyCandidateLoginOtp).mockRejectedValueOnce(new Error("bad code"));
    renderPage("login", <LoginPage />, {
      candidate: null,
      loginCandidate: vi.fn(),
      logoutCandidate: vi.fn(),
    });

    await user.type(screen.getByLabelText("邮箱"), "zhangmin@example.com");
    await user.click(screen.getByRole("button", { name: "发送验证码" }));
    await user.type(await screen.findByLabelText("验证码"), "000000");
    await user.click(screen.getByRole("button", { name: "验证并继续" }));

    expect(await screen.findByText("验证码无效或已过期，请重新获取后再试。")).toBeInTheDocument();
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
    expect(screen.getAllByText("第 01 题 · 单选 · 2 分").length).toBeGreaterThan(0);
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

    expect(screen.getByText("未开始")).toBeInTheDocument();
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

    await waitFor(() =>
      expect(submitAttempt).toHaveBeenCalledWith("10", "attempt-credential", "manual"),
    );
  });

  it("waits for queued autosave before final exam submit and ignores duplicate submits", async () => {
    const user = userEvent.setup();
    let resolveFirstSave: (value: {
      saved_count: number;
      saved_at: string;
      answer_revision: number;
    }) => void = () => {};
    const firstSave = new Promise<{
      saved_count: number;
      saved_at: string;
      answer_revision: number;
    }>((resolve) => {
      resolveFirstSave = resolve;
    });
    vi.mocked(saveAttemptAnswers)
      .mockImplementationOnce(() => firstSave)
      .mockResolvedValue({ saved_count: 1, saved_at: "2026-06-14", answer_revision: 2 });
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

    resolveFirstSave({ saved_count: 1, saved_at: "2026-06-14", answer_revision: 1 });

    await waitFor(() => expect(submitAttempt).toHaveBeenCalledTimes(1));
    expect(submitAttempt).toHaveBeenCalledWith("10", "attempt-credential", "manual");
    expect(saveAttemptAnswers).toHaveBeenLastCalledWith(
      "10",
      "attempt-credential",
      [{ attempt_question_id: 101, selected_answer: "B" }],
      1,
    );
  });

  it("shows visible autosave failure and retries the latest answer snapshot", async () => {
    const user = userEvent.setup();
    vi.mocked(saveAttemptAnswers)
      .mockRejectedValueOnce(new ApiError("保存失败", 500, "保存失败"))
      .mockResolvedValue({ saved_count: 1, saved_at: "2026-06-14", answer_revision: 1 });

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
    expect(saveAttemptAnswers).toHaveBeenLastCalledWith(
      "10",
      "attempt-credential",
      [{ attempt_question_id: 101, selected_answer: "B" }],
      0,
    );
  });

  it("restores a matching pending draft after reload and retries it", async () => {
    const activeSession = getAttemptSession(candidate.id, attempt.id);
    expect(activeSession).not.toBeNull();
    writeAttemptDraft(activeSession!, { 101: "B" });

    renderPage(
      "exams/:examId/taking",
      <ExamTakingPage />,
      undefined,
      "exams/1/taking?attemptId=10",
    );

    const optionB = await screen.findAllByRole("radio", { name: /选项 B：上海/ });
    await waitFor(() =>
      expect(optionB.some((option) => option.getAttribute("aria-checked") === "true")).toBe(true),
    );
    await waitFor(() =>
      expect(saveAttemptAnswers).toHaveBeenCalledWith(
        "10",
        "attempt-credential",
        [{ attempt_question_id: 101, selected_answer: "B" }],
        0,
      ),
    );
  });

  it("keeps the pending draft and blocks submit while offline", async () => {
    const user = userEvent.setup();
    vi.mocked(saveAttemptAnswers).mockRejectedValue(new Error("network unavailable"));

    renderPage(
      "exams/:examId/taking",
      <ExamTakingPage />,
      undefined,
      "exams/1/taking?attemptId=10",
    );

    const optionB = await screen.findAllByRole("radio", { name: /选项 B：上海/ });
    await user.click(optionB[0]);
    expect(await screen.findByText("网络中断，答案待同步")).toBeVisible();
    await user.click(screen.getAllByRole("button", { name: "交卷" })[0]);

    await waitFor(() => expect(saveAttemptAnswers).toHaveBeenCalledTimes(2));
    expect(submitAttempt).not.toHaveBeenCalled();
    expect(window.sessionStorage.getItem("internal-exam-attempt-draft:1:10")).toContain(
      '"101":"B"',
    );
  });

  it("surfaces a stale answer revision without overwriting the local draft", async () => {
    const user = userEvent.setup();
    vi.mocked(saveAttemptAnswers).mockRejectedValueOnce(
      new ApiError("答案版本已更新", 409, "答案版本已更新，当前服务端版本为 1，请先重新载入。"),
    );

    renderPage(
      "exams/:examId/taking",
      <ExamTakingPage />,
      undefined,
      "exams/1/taking?attemptId=10",
    );

    const optionB = await screen.findAllByRole("radio", { name: /选项 B：上海/ });
    await user.click(optionB[0]);

    expect(await screen.findByText("答案版本冲突，请重新接管")).toBeVisible();
    expect(screen.getByRole("button", { name: "重新登录并接管" })).toBeInTheDocument();
    expect(window.sessionStorage.getItem("internal-exam-attempt-draft:1:10")).toContain(
      '"101":"B"',
    );
  });

  it("invalidates a rotated device session and clears its unusable draft", async () => {
    const activeSession = getAttemptSession(candidate.id, attempt.id);
    expect(activeSession).not.toBeNull();
    writeAttemptDraft(activeSession!, { 101: "B" });
    vi.mocked(getAttempt).mockRejectedValueOnce(
      new ApiError("设备会话失效", 409, "本设备的考试会话已失效，请重新验证码登录后接管考试。"),
    );

    renderPage(
      "exams/:examId/taking",
      <ExamTakingPage />,
      undefined,
      "exams/1/taking?attemptId=10",
    );

    expect(
      await screen.findByRole("heading", { name: "需要重新核验并接管考试。" }),
    ).toBeInTheDocument();
    expect(getAttemptSession(candidate.id, attempt.id)).toBeNull();
    expect(window.sessionStorage.getItem("internal-exam-attempt-draft:1:10")).toBeNull();
  });

  it("uses a fresh-login return marker to take over and load the same attempt", async () => {
    clearAttemptSession(candidate.id, attempt.id);

    renderPage(
      "exams/:examId/taking",
      <ExamTakingPage />,
      undefined,
      "exams/1/taking?attemptId=10&takeover=1",
    );

    await waitFor(() => expect(takeoverAttempt).toHaveBeenCalledWith("10"));
    expect(await screen.findAllByRole("radio", { name: /选项 A：北京/ })).not.toHaveLength(0);
    expect(getAttempt).toHaveBeenCalledWith("10", "replacement-credential");
    expect(getAttemptSession(candidate.id, attempt.id)?.generation).toBe(2);
  });

  it("clears the attempt session and pending draft after successful submit", async () => {
    const user = userEvent.setup();
    const activeSession = getAttemptSession(candidate.id, attempt.id);
    expect(activeSession).not.toBeNull();
    writeAttemptDraft(activeSession!, { 101: "A" });

    renderPage(
      "exams/:examId/taking",
      <ExamTakingPage />,
      undefined,
      "exams/1/taking?attemptId=10",
    );

    await screen.findAllByRole("radio", { name: /选项 A：北京/ });
    await user.click(screen.getAllByRole("button", { name: "交卷" })[0]);

    await waitFor(() => expect(submitAttempt).toHaveBeenCalledTimes(1));
    await waitFor(() => {
      expect(getAttemptSession(candidate.id, attempt.id)).toBeNull();
      expect(window.sessionStorage.getItem("internal-exam-attempt-draft:1:10")).toBeNull();
    });
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

    await waitFor(() =>
      expect(submitAttempt).toHaveBeenCalledWith("10", "attempt-credential", "manual"),
    );
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
      expect(saveAttemptAnswers).toHaveBeenCalledWith(
        "10",
        "attempt-credential",
        [{ attempt_question_id: 101, selected_answer: "B" }],
        0,
      ),
    );
  });

  it("guards beforeunload only while the active attempt has unsynchronized work", async () => {
    let resolveSave: (value: {
      saved_count: number;
      saved_at: string;
      answer_revision: number;
    }) => void = () => {};
    vi.mocked(saveAttemptAnswers).mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveSave = resolve;
        }),
    );
    const user = userEvent.setup();

    renderPage(
      "exams/:examId/taking",
      <ExamTakingPage />,
      undefined,
      "exams/1/taking?attemptId=10",
    );

    await user.click((await screen.findAllByRole("radio", { name: /选项 B：上海/ }))[0]);
    await waitFor(() => expect(saveAttemptAnswers).toHaveBeenCalledTimes(1));

    const unsavedEvent = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(unsavedEvent);
    expect(unsavedEvent.defaultPrevented).toBe(true);

    resolveSave({ saved_count: 1, saved_at: "2026-08-14T00:02:00.000Z", answer_revision: 1 });
    await waitFor(() =>
      expect(screen.getByTestId("exam-save-status")).toHaveTextContent(/^答案已保存$/),
    );

    const savedEvent = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(savedEvent);
    expect(savedEvent.defaultPrevented).toBe(false);
  });

  it("shows an in-app leave warning and lets the candidate stay or leave explicitly", async () => {
    const user = userEvent.setup();
    vi.mocked(saveAttemptAnswers).mockImplementation(() => new Promise(() => {}));

    function TakingWithLeaveLink() {
      return (
        <>
          <ExamTakingPage />
          <Link to="/exams">离开考试</Link>
        </>
      );
    }

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    const router = createMemoryRouter(
      [
        {
          path: "/",
          element: <Outlet />,
          children: [
            { path: "exams/:examId/taking", element: <TakingWithLeaveLink /> },
            { path: "exams", element: <div>考试列表</div> },
          ],
        },
      ],
      { initialEntries: ["/exams/1/taking?attemptId=10"] },
    );
    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    await user.click((await screen.findAllByRole("radio", { name: /选项 B：上海/ }))[0]);
    await waitFor(() => expect(saveAttemptAnswers).toHaveBeenCalledTimes(1));
    const leaveLink = screen.getByRole("link", { name: "离开考试" });

    await user.click(leaveLink);
    expect(await screen.findByRole("alertdialog")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "留在考试" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "仍要离开" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "留在考试" }));
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "离开考试" })).toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: "离开考试" }));
    await user.click(screen.getByRole("button", { name: "仍要离开" }));
    expect(await screen.findByText("考试列表")).toBeInTheDocument();
  });

  it("keeps shortcuts inside the question workspace and exposes mobile save and sheet actions", async () => {
    const user = userEvent.setup();
    renderPage(
      "exams/:examId/taking",
      <ExamTakingPage />,
      undefined,
      "exams/1/taking?attemptId=10",
    );

    await screen.findAllByRole("radio", { name: /选项 B：上海/ });
    const heading = screen.getAllByTestId("exam-question-heading")[0];
    heading.focus();
    expect(document.activeElement).toBe(heading);
    await user.keyboard("b");
    await waitFor(() => expect(saveAttemptAnswers).toHaveBeenCalled());

    const optionB = screen.getAllByRole("radio", { name: /选项 B：上海/ });
    optionB.forEach((option) => expect(option).toHaveAttribute("aria-checked", "true"));

    const saveButtons = screen.getAllByRole("button", { name: "保存答案" });
    expect(saveButtons.length).toBeGreaterThanOrEqual(2);
    const workspace = screen.getByTestId("exam-save-status").closest("[data-exam-workspace]");
    expect(workspace).not.toBeNull();
    expect(
      Array.from(workspace?.querySelectorAll("*") ?? []).some((element) =>
        String(element.className).includes("safe-area-inset-bottom"),
      ),
    ).toBe(true);

    const sheetTrigger = screen.getByRole("button", { name: "打开题号导航" });
    await user.click(sheetTrigger);
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByRole("button", { name: "交卷" })).toBeInTheDocument();
    (dialog as HTMLElement).focus();
    await user.keyboard("a");
    expect(optionB[0]).toHaveAttribute("aria-checked", "true");
  });

  it("renders the exam result page black-card result copy and filter controls", async () => {
    renderPage(
      "exams/:examId/result",
      <ExamResultPage />,
      undefined,
      "exams/1/result?attemptId=10",
    );

    expect(await screen.findByText("考试已交卷。")).toBeInTheDocument();
    expect(screen.getAllByText("得分", { exact: true }).length).toBeGreaterThan(0);
    expect(
      screen.getByRole("heading", { name: "本次答卷" }).closest("[data-density]"),
    ).toHaveAttribute("data-density", "calm");
    expect(screen.getByRole("button", { name: /只看错题/ })).toBeInTheDocument();
  });

  it("shows score only while answer details are not released", async () => {
    vi.mocked(getAttemptResult).mockResolvedValueOnce({
      ...result,
      show_answer_after_submit: false,
      questions: [],
    });

    renderPage(
      "exams/:examId/result",
      <ExamResultPage />,
      undefined,
      "exams/1/result?attemptId=10",
    );

    expect(await screen.findByText("答案与解析尚未发布。")).toBeInTheDocument();
    expect(screen.getByText(/当前仅显示分数和通过状态/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /只看错题/ })).not.toBeInTheDocument();
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
    expect(screen.queryByText("得分", { exact: true })).not.toBeInTheDocument();
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
    expect(screen.queryByText("得分", { exact: true })).not.toBeInTheDocument();
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

    expect(await screen.findByText("答案与解析尚未发布。")).toBeInTheDocument();
    expect(screen.queryByText("正确答案")).not.toBeInTheDocument();
    expect(screen.queryByText("北京是首都。")).not.toBeInTheDocument();
  });

  it("renders the practice focus page with submit affordance", async () => {
    renderPage("practice", <PracticePage />, {
      candidate,
      loginCandidate: vi.fn(),
      logoutCandidate: vi.fn(),
    });

    expect(await screen.findByRole("link", { name: "查看错题复习" })).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "查看错题复习" }).closest("[data-density]"),
    ).toHaveAttribute("data-density", "focus");
    expect(screen.queryByRole("heading", { level: 1 })).not.toBeInTheDocument();
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

    expect(screen.getByText("未登录")).toBeInTheDocument();
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

  it("locks immediate practice feedback and starts retries as new submissions", async () => {
    const user = userEvent.setup();
    renderPage("practice", <PracticePage />, {
      candidate,
      loginCandidate: vi.fn(),
      logoutCandidate: vi.fn(),
    });

    await user.click((await screen.findAllByRole("radio", { name: /选项 A：选项 A/ }))[0]);
    await user.click(screen.getAllByRole("button", { name: "提交本题" })[0]);

    expect(await screen.findAllByText("回答正确")).not.toHaveLength(0);
    expect(screen.getAllByText("正确答案：A")).not.toHaveLength(0);
    expect(screen.getAllByText("选项 A 是正确答案。")).not.toHaveLength(0);
    expect(screen.queryByRole("button", { name: "提交本题" })).not.toBeInTheDocument();
    expect(screen.getAllByRole("radio", { name: /选项 A：选项 A/ })[0]).toBeDisabled();

    await user.click(screen.getAllByRole("button", { name: "重新练习本题" })[0]);
    expect(screen.getAllByRole("button", { name: "提交本题" })[0]).toBeDisabled();
    expect(screen.getAllByRole("radio", { name: /选项 A：选项 A/ })[0]).not.toBeDisabled();
  });

  it("shows candidate-scoped wrong-question mastery and category filters", async () => {
    const user = userEvent.setup();
    renderPage("practice/wrong-questions", <WrongQuestionReviewPage />, {
      candidate,
      loginCandidate: vi.fn(),
      logoutCandidate: vi.fn(),
    });

    const wrongReviewHeading = await screen.findByRole("heading", { name: "错题复习" });
    expect(wrongReviewHeading).toBeInTheDocument();
    expect(wrongReviewHeading.closest("[data-density]")).toHaveAttribute("data-density", "calm");
    expect(await screen.findByText("错 1 次 · 共练习 2 次")).toBeInTheDocument();
    expect(screen.getAllByText("已掌握").length).toBeGreaterThan(1);
    expect(screen.getByRole("link", { name: /再次练习/ })).toHaveAttribute(
      "href",
      "/practice?questionId=201",
    );

    await user.type(screen.getByLabelText("一级分类"), "安全");
    await waitFor(() =>
      expect(getWrongPracticeQuestions).toHaveBeenLastCalledWith({
        category_1: "安全",
        category_2: undefined,
        mastered: undefined,
      }),
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
    setCurrentCandidate(candidate);
    vi.mocked(getActiveExams).mockResolvedValue([exam]);

    renderPage("exams", <ExamListPage />);

    expect(await screen.findByTestId("candidate-exam-list-shell")).toHaveClass("gap-8");
    expect(screen.getByTestId("candidate-exam-list-shell")).toHaveAttribute("data-density", "calm");
    expect(await screen.findByText("受邀考试")).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("受邀考试");
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
    expect(screen.getByRole("heading", { name: "受邀考试" })).toBeInTheDocument();
    expect(screen.queryByText("今天暂无考试安排。")).not.toBeInTheDocument();
  });

  it("does not request active exams without a candidate session", async () => {
    clearCurrentCandidate();
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
    expect(screen.getAllByText("尚未开放").length).toBeGreaterThan(0);
    expect(screen.getAllByText("暂不可进入").length).toBeGreaterThan(0);
    expect(screen.getAllByRole("button", { name: /尚未开放|暂不可进入/ }).length).toBe(2);
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
    expect(screen.getByText("新开考窗口已关闭")).toBeInTheDocument();
  });

  it("keeps the exam list heading stable with multiple active exams", async () => {
    setCurrentCandidate(candidate);
    vi.mocked(getActiveExams).mockResolvedValue([exam, secondExam]);

    renderPage("exams", <ExamListPage />);

    expect(await screen.findByText("受邀考试")).toBeInTheDocument();
  });

  it("falls back to the empty-state heading when there are no active exams", async () => {
    setCurrentCandidate(candidate);
    vi.mocked(getActiveExams).mockResolvedValue([]);

    renderPage("exams", <ExamListPage />);

    expect(await screen.findByRole("heading", { name: "暂无受邀考试。" })).toBeInTheDocument();
  });

  it("shows the actual API error when starting an exam fails", async () => {
    const user = userEvent.setup();
    vi.mocked(getActiveExams).mockResolvedValue([exam]);
    vi.mocked(startExam).mockRejectedValueOnce(
      new ApiError("考试人已有进行中的考试记录 #9", 409, "考试人已有进行中的考试记录 #9"),
    );

    renderPage(
      "exams/:examId/start",
      <ExamStartPage />,
      {
        candidate,
        loginCandidate: vi.fn(),
        logoutCandidate: vi.fn(),
      },
      "exams/1/start",
    );

    const startButton = await screen.findByRole("button", { name: /开始考试/ });
    await user.click(startButton);

    expect(await screen.findByText("考试人已有进行中的考试记录 #9")).toBeInTheDocument();
    expect(screen.queryByText("请确认考试仍处于发布状态。")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "继续考试" })).toBeInTheDocument();
  });

  it("does not offer continue action after the exam was already handed in", async () => {
    const user = userEvent.setup();
    vi.mocked(getActiveExams).mockResolvedValue([exam]);
    vi.mocked(startExam).mockRejectedValueOnce(
      new ApiError("考试记录 #10 已交卷", 409, "考试记录 #10 已交卷"),
    );

    renderPage(
      "exams/:examId/start",
      <ExamStartPage />,
      {
        candidate,
        loginCandidate: vi.fn(),
        logoutCandidate: vi.fn(),
      },
      "exams/1/start",
    );

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
    expect(screen.getByText("已交卷")).toBeInTheDocument();
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
    vi.mocked(getActiveExams).mockResolvedValue([exam]);
    vi.mocked(startExam).mockRejectedValueOnce(new Error("network down"));

    renderPage(
      "exams/:examId/start",
      <ExamStartPage />,
      {
        candidate,
        loginCandidate: vi.fn(),
        logoutCandidate: vi.fn(),
      },
      "exams/1/start",
    );

    const startButton = await screen.findByRole("button", { name: /开始考试/ });
    await user.click(startButton);

    expect(await screen.findByText("network down")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "继续考试" })).not.toBeInTheDocument();
  });
});
