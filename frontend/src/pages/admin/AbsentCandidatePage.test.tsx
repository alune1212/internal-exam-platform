import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getAbsentCandidates } from "@/api/reports";
import { AbsentCandidatePage } from "@/pages/admin/AbsentCandidatePage";

vi.mock("@/api/reports", () => ({
  getAbsentCandidates: vi.fn(),
  downloadReportExport: vi.fn(),
}));

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AbsentCandidatePage />
    </QueryClientProvider>,
  );
}

describe("AbsentCandidatePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getAbsentCandidates).mockImplementation(async (status = "not_started") => {
      if (status === "in_progress") {
        return [
          {
            candidate_id: 2,
            exam_id: 7,
            exam_title: "正式考试",
            roster_name: "李四",
            roster_email: "lisi@example.com",
            department: "产品部",
            exam_group: "A",
            attendance_status: "in_progress",
          },
        ];
      }
      return [
        {
          candidate_id: 3,
          exam_id: 7,
          exam_title: "正式考试",
          roster_name: "王五",
          roster_email: "wangwu@example.com",
          department: "技术部",
          exam_group: "B",
          attendance_status: "not_started",
        },
      ];
    });
  });

  it("splits not-started and in-progress attendance views", async () => {
    const user = userEvent.setup();
    renderPage();

    expect(await screen.findByText("王五")).toBeInTheDocument();
    expect(getAbsentCandidates).toHaveBeenLastCalledWith("not_started");
    expect(screen.getByRole("button", { name: "未开始" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "进行中" })).toHaveAttribute("aria-pressed", "false");

    await user.click(screen.getByRole("button", { name: "进行中" }));

    expect(await screen.findByText("李四")).toBeInTheDocument();
    await waitFor(() => expect(getAbsentCandidates).toHaveBeenLastCalledWith("in_progress"));
    expect(screen.queryByText("王五")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "未开始" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: "进行中" })).toHaveAttribute("aria-pressed", "true");
  });
});
