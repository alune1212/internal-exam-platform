import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { downloadReportExport, getScoreReport } from "@/api/reports";
import { ScoreReportPage } from "@/pages/admin/ScoreReportPage";

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
    vi.mocked(getScoreReport).mockResolvedValue([]);
    vi.mocked(downloadReportExport).mockResolvedValue();
  });

  it("downloads the combined report workbook", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: /导出全部报表/ }));

    await waitFor(() => expect(downloadReportExport).toHaveBeenCalledTimes(1));
    expect(await screen.findByRole("alert")).toHaveTextContent("报表已开始下载");
  });
});
