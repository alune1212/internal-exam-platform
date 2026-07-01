import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getAdminExams } from "@/api/exams";
import {
  downloadReportExport,
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
    vi.mocked(getQuestionAccuracy).mockResolvedValue([]);
    vi.mocked(getWrongQuestions).mockResolvedValue([]);
    vi.mocked(downloadReportExport).mockResolvedValue();
  });

  it("filters and downloads by the selected exam", async () => {
    const user = userEvent.setup();
    renderReportPage();

    expect(await screen.findByDisplayValue("正式考试")).toBeInTheDocument();
    await waitFor(() => expect(getScoreReport).toHaveBeenCalledWith("7"));

    await user.click(await screen.findByRole("button", { name: /导出当前考试/ }));

    await waitFor(() => expect(downloadReportExport).toHaveBeenCalledTimes(1));
    expect(downloadReportExport).toHaveBeenCalledWith("7");
    expect(await screen.findByRole("status")).toHaveTextContent("报表已开始下载");
  });

  it("renders exam-list failures as report errors instead of exporting all scores", async () => {
    vi.mocked(getAdminExams).mockRejectedValueOnce(new Error("exam list unavailable"));

    renderReportPage();

    expect(await screen.findByRole("heading", { name: "报表加载失败。" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /导出全部报表/ })).not.toBeInTheDocument();
    expect(getScoreReport).not.toHaveBeenCalled();
  });

  it.each([
    ["题目正确率", <QuestionAccuracyPage />, getQuestionAccuracy],
    ["错题排行", <WrongQuestionPage />, getWrongQuestions],
  ])("renders exam-list failures as report errors for %s", async (_title, page, queryFn) => {
    vi.mocked(getAdminExams).mockRejectedValueOnce(new Error("exam list unavailable"));

    renderReportPage(page);

    expect(await screen.findByRole("heading", { name: "报表加载失败。" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /导出全部报表/ })).not.toBeInTheDocument();
    expect(queryFn).not.toHaveBeenCalled();
  });
});
