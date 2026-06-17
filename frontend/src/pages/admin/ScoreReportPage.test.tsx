import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getAdminExams } from "@/api/exams";
import { downloadReportExport, getScoreReport } from "@/api/reports";
import { ScoreReportPage } from "@/pages/admin/ScoreReportPage";

vi.mock("@/api/exams", () => ({
  getAdminExams: vi.fn(),
}));

vi.mock("@/api/reports", () => ({
  getScoreReport: vi.fn(),
  downloadReportExport: vi.fn(),
}));

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ScoreReportPage />
    </QueryClientProvider>,
  );
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
    vi.mocked(downloadReportExport).mockResolvedValue();
  });

  it("filters and downloads by the selected exam", async () => {
    const user = userEvent.setup();
    renderPage();

    expect(await screen.findByDisplayValue("正式考试")).toBeInTheDocument();
    await waitFor(() => expect(getScoreReport).toHaveBeenCalledWith("7"));

    await user.click(await screen.findByRole("button", { name: /导出当前考试/ }));

    await waitFor(() => expect(downloadReportExport).toHaveBeenCalledTimes(1));
    expect(downloadReportExport).toHaveBeenCalledWith("7");
    expect(await screen.findByRole("alert")).toHaveTextContent("报表已开始下载");
  });
});
