import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getActiveExams } from "@/api/exams";
import { clearCurrentCandidate, setCurrentCandidate } from "@/lib/candidateSession";
import { ExamListPage } from "@/pages/ExamListPage";
import type { Candidate } from "@/types/candidate";
import type { Exam } from "@/types/exam";

vi.mock("@/api/exams", () => ({
  getActiveExams: vi.fn(),
}));

const candidate: Candidate = {
  id: 7,
  email: "user@example.com",
  display_name: "测试用户",
  status: "active",
  token: "candidate-token",
  token_expires_at: "2099-01-01T00:00:00.000Z",
};

const exam: Exam = {
  id: 1,
  title: "年度安全培训考试",
  description: "请按开放时间完成考试。",
  duration_minutes: 60,
  question_rule: { question_count: 20, total_score: 100 },
  status: "active",
  show_answer_after_submit: true,
  availability_status: "open",
  available_from: "2026-01-01T00:00:00Z",
  available_until: "2099-01-01T00:00:00Z",
};

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/exams"]}>
        <ExamListPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ExamListPage V2 Candidate Calm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.sessionStorage.clear();
    window.localStorage.clear();
    clearCurrentCandidate();
    vi.mocked(getActiveExams).mockResolvedValue([exam]);
    setCurrentCandidate(candidate);
  });

  it("renders the governed calm frame, statuses, metadata, and card action", async () => {
    renderPage();

    const heading = await screen.findByRole("heading", {
      level: 2,
      name: "年度安全培训考试",
    });
    const shell = screen.getByTestId("candidate-exam-list-shell");
    expect(shell).toHaveAttribute("data-density", "calm");
    expect(shell).toHaveAttribute("data-width", "wide");
    expect(screen.getByRole("heading", { level: 1, name: "受邀考试" })).toBeInTheDocument();
    expect(heading).toBeInTheDocument();
    expect(screen.getByText("已受邀")).toHaveAttribute("data-feedback-kind", "status-pill");
    expect(screen.getByText("可以开始")).toBeInTheDocument();
    expect(screen.getByText("60 分钟")).toBeInTheDocument();
    expect(screen.getByText("20")).toBeInTheDocument();
    expect(screen.getByText("100")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /开始考试/ })).toHaveAttribute(
      "href",
      "/exams/1/start",
    );
    expect(
      screen.getByRole("link", { name: /开始考试/ }).closest("[data-surface-owner]"),
    ).toHaveAttribute("data-surface-owner", "data");
  });

  it("keeps an in-progress attempt directly resumable after the new window closes", async () => {
    vi.mocked(getActiveExams).mockResolvedValueOnce([
      {
        ...exam,
        available_until: "2020-01-01T00:00:00Z",
        availability_status: "ended",
        latest_attempt_id: 42,
        latest_attempt_status: "in_progress",
      },
    ]);
    renderPage();

    expect(await screen.findByRole("link", { name: /继续考试/ })).toHaveAttribute(
      "href",
      "/exams/1/taking?attemptId=42",
    );
    expect(screen.getByText("新开考窗口已关闭")).toBeInTheDocument();
    expect(screen.getByText("暂不可进入")).toBeInTheDocument();
  });

  it("covers loading, recoverable error, and empty states", async () => {
    vi.mocked(getActiveExams).mockReturnValueOnce(new Promise(() => {}));
    renderPage();
    expect(await screen.findByRole("status")).toHaveAttribute("aria-busy", "true");
    expect(screen.queryByText("暂无受邀考试。")).not.toBeInTheDocument();
  });

  it("shows an explicit error and stays session-scoped", async () => {
    vi.mocked(getActiveExams).mockRejectedValueOnce(new Error("network unavailable"));
    renderPage();

    expect(await screen.findByRole("heading", { name: "考试列表加载失败。" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "重试" })).toBeInTheDocument();
    expect(getActiveExams).toHaveBeenCalledTimes(1);

    clearCurrentCandidate();
    vi.clearAllMocks();
    renderPage();
    expect(getActiveExams).not.toHaveBeenCalled();
  });

  it("renders the governed empty state when no invited exams are available", async () => {
    vi.mocked(getActiveExams).mockResolvedValueOnce([]);
    renderPage();

    expect(await screen.findByRole("heading", { name: "暂无受邀考试。" })).toBeInTheDocument();
    expect(screen.getByText(/正式考试仅对受邀的应考人员开放/)).toBeInTheDocument();
  });

  it("wraps long exam titles and keeps card metadata responsive", async () => {
    vi.mocked(getActiveExams).mockResolvedValueOnce([
      {
        ...exam,
        title: "这是一个包含很长中文名称以及unbroken-exam-identifier-2026的考试标题",
      },
    ]);
    renderPage();

    const heading = await screen.findByRole("heading", { level: 2 });
    expect(heading).toHaveClass("min-w-0", "break-words");
    expect(heading.closest("[data-surface-owner]")).toHaveAttribute("data-surface-owner", "data");
    expect(screen.getByText("时长").closest("dl")).toHaveClass("grid-cols-1", "sm:grid-cols-3");
  });
});
