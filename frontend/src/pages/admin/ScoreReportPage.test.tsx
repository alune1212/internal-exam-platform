import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getAdminExams } from "@/api/exams";
import {
  downloadReportExport,
  getRanking,
  getQuestionAccuracy,
  getScoreReport,
  getWrongQuestions,
} from "@/api/reports";
import { QuestionAccuracyPage } from "@/pages/admin/QuestionAccuracyPage";
import { ScoreReportPage } from "@/pages/admin/ScoreReportPage";
import { WrongQuestionPage } from "@/pages/admin/WrongQuestionPage";

vi.mock("@/api/exams", () => ({
  getAdminExams: vi.fn(),
}));

vi.mock("@/api/reports", () => ({
  getScoreReport: vi.fn(),
  getRanking: vi.fn(),
  getQuestionAccuracy: vi.fn(),
  getWrongQuestions: vi.fn(),
  downloadReportExport: vi.fn(),
}));

function renderReportPage(page = <ScoreReportPage />) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{page}</QueryClientProvider>);
}

describe("ScoreReportPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getAdminExams).mockResolvedValue([
      {
        id: 7,
        title: "正式考试",
        description: null,
        duration_minutes: 60,
        question_rule: {},
        status: "active",
        show_answer_after_submit: true,
      },
    ]);
    vi.mocked(getScoreReport).mockResolvedValue([]);
    vi.mocked(getRanking).mockResolvedValue([]);
    vi.mocked(getQuestionAccuracy).mockResolvedValue([]);
    vi.mocked(getWrongQuestions).mockResolvedValue([]);
    vi.mocked(downloadReportExport).mockResolvedValue();
  });

  it("filters and downloads by the selected exam", async () => {
    const user = userEvent.setup();
    renderReportPage();

    expect(await screen.findByRole("heading", { name: "成绩册" })).toBeInTheDocument();
    expect(await screen.findByDisplayValue("正式考试")).toBeInTheDocument();
    await waitFor(() => expect(getScoreReport).toHaveBeenCalledWith("7"));
    await waitFor(() => expect(getRanking).toHaveBeenCalledWith("7"));

    await user.click(await screen.findByRole("button", { name: /导出当前考试/ }));

    await waitFor(() => expect(downloadReportExport).toHaveBeenCalledTimes(1));
    expect(downloadReportExport).toHaveBeenCalledWith("7");
    expect(await screen.findByRole("status")).toHaveTextContent("报表已开始下载");
  });

  it("renders the selected exam ranking beside score rows", async () => {
    vi.mocked(getScoreReport).mockResolvedValueOnce([
      {
        candidate_id: 9,
        roster_name: "冻结名单",
        roster_email: "frozen@example.com",
        exam_id: 7,
        exam_title: "正式考试",
        score: 90,
        total_score: 100,
        submitted_at: "2026-08-11T10:00:00Z",
      },
    ]);
    vi.mocked(getRanking).mockResolvedValueOnce([
      {
        rank: 1,
        candidate_id: 9,
        roster_name: "冻结名单",
        roster_email: "frozen@example.com",
        exam_id: 7,
        exam_title: "正式考试",
        score: 90,
        total_score: 100,
        submitted_at: "2026-08-11T10:00:00Z",
      },
    ]);

    renderReportPage();

    expect(await screen.findByText("冻结名单")).toBeInTheDocument();
    expect(screen.getByText("名次")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
    await waitFor(() => expect(getRanking).toHaveBeenCalledWith("7"));
  });

  it("renders exam-list failures as report errors instead of exporting all scores", async () => {
    vi.mocked(getAdminExams).mockRejectedValueOnce(new Error("exam list unavailable"));

    renderReportPage();

    expect(await screen.findByRole("heading", { name: "报表加载失败。" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /导出全部报表/ })).not.toBeInTheDocument();
    expect(getScoreReport).not.toHaveBeenCalled();
  });

  it.each([
    ["题目表现", <QuestionAccuracyPage />, getQuestionAccuracy],
    ["错题回看", <WrongQuestionPage />, getWrongQuestions],
  ])("renders exam-list failures as report errors for %s", async (_title, page, queryFn) => {
    vi.mocked(getAdminExams).mockRejectedValueOnce(new Error("exam list unavailable"));

    renderReportPage(page);

    expect(await screen.findByRole("heading", { name: "报表加载失败。" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /导出全部报表/ })).not.toBeInTheDocument();
    expect(queryFn).not.toHaveBeenCalled();
  });

  it("filters and downloads question accuracy by the selected exam", async () => {
    const user = userEvent.setup();
    vi.mocked(getQuestionAccuracy).mockResolvedValueOnce([
      {
        question_id: 11,
        stem: "单选题干",
        correct_count: 7,
        total_count: 8,
        accuracy_rate: 0.875,
      },
    ]);

    renderReportPage(<QuestionAccuracyPage />);

    expect(await screen.findByRole("heading", { name: "题目表现" })).toBeInTheDocument();
    expect(await screen.findByDisplayValue("正式考试")).toBeInTheDocument();
    await waitFor(() => expect(getQuestionAccuracy).toHaveBeenCalledWith("7"));
    expect(await screen.findByText("单选题干")).toBeInTheDocument();
    expect(screen.getByText("87.5%")).toBeInTheDocument();
    expect(screen.getByText("TOTAL · 总数")).toBeInTheDocument();
    expect(screen.queryByText("TOTAL · 总分")).not.toBeInTheDocument();

    await user.click(await screen.findByRole("button", { name: /导出当前考试/ }));

    await waitFor(() => expect(downloadReportExport).toHaveBeenCalledTimes(1));
    expect(downloadReportExport).toHaveBeenCalledWith("7");
  });

  it("filters and downloads wrong-question rankings by the selected exam", async () => {
    const user = userEvent.setup();
    vi.mocked(getWrongQuestions).mockResolvedValueOnce([
      {
        question_id: 12,
        stem: "多选题干",
        wrong_count: 3,
        category_1: "制度",
        category_2: "多选",
      },
    ]);

    renderReportPage(<WrongQuestionPage />);

    expect(await screen.findByRole("heading", { name: "错题回看" })).toBeInTheDocument();
    expect(await screen.findByDisplayValue("正式考试")).toBeInTheDocument();
    await waitFor(() => expect(getWrongQuestions).toHaveBeenCalledWith("7"));
    expect(await screen.findByText("多选题干")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();

    await user.click(await screen.findByRole("button", { name: /导出当前考试/ }));

    await waitFor(() => expect(downloadReportExport).toHaveBeenCalledTimes(1));
    expect(downloadReportExport).toHaveBeenCalledWith("7");
  });
});
