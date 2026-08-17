import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const learningApi = vi.hoisted(() => ({
  downloadLearningReportExport: vi.fn(),
  getAdminLearningVideos: vi.fn(),
  getLearningReport: vi.fn(),
}));

vi.mock("@/api/learning", () => learningApi);

import { AdminLearningReportPage } from "@/pages/admin/LearningReportPage";
import type { LearningReportRow, LearningVideo } from "@/types/learning";

const video: LearningVideo = {
  id: 7,
  title: "安全培训",
  description: null,
  original_filename: "safety.mp4",
  storage_key: "safety-storage.mp4",
  content_type: "video/mp4",
  file_size_bytes: 1024,
  duration_seconds: 120,
  completion_threshold_percent: 90,
  status: "published",
  uploaded_at: "2026-07-02T00:00:00Z",
  created_at: "2026-07-02T00:00:00Z",
  updated_at: "2026-07-02T00:00:00Z",
  playback_url: "/media/learning/safety-storage.mp4",
};

const reportRow: LearningReportRow = {
  candidate_id: 3,
  account_email: "zhangmin@example.com",
  display_name: "张敏",
  account_status: "active",
  video_id: 7,
  video_title: "安全培训",
  video_status: "published",
  duration_seconds: 120,
  completion_percent: 90,
  completion_status: "completed",
  last_heartbeat_at: "2026-07-02T01:00:00Z",
  completed_at: "2026-07-02T01:00:00Z",
};

function mockMediaQuery(matches = true) {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string) => ({
      matches,
      media: query,
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }),
  });
}

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/admin/learning/reports"]}>
        <AdminLearningReportPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("AdminLearningReportPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockMediaQuery();
    learningApi.getAdminLearningVideos.mockResolvedValue([video]);
    learningApi.getLearningReport.mockResolvedValue([reportRow]);
    learningApi.downloadLearningReportExport.mockResolvedValue(undefined);
  });

  it("passes video and completion filters to the report query", async () => {
    const user = userEvent.setup();
    renderPage();

    expect(await screen.findByText("张敏")).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("视频"), "7");
    await user.selectOptions(screen.getByLabelText("完成状态"), "completed");

    await waitFor(() =>
      expect(learningApi.getLearningReport).toHaveBeenLastCalledWith({
        videoId: "7",
        status: "completed",
      }),
    );
  });

  it("uses the shared report toolbar and Chinese-first table headers", async () => {
    renderPage();

    expect(await screen.findByText("张敏")).toBeInTheDocument();
    const toolbar = screen.getByRole("group", { name: "报表筛选与操作" });
    expect(toolbar).toHaveAttribute("data-report-order", "filters-segments-notice-actions");
    expect(screen.getByText("用户姓名")).toBeInTheDocument();
    expect(screen.getByText("用户邮箱")).toBeInTheDocument();
    expect(screen.queryByText(/ACCOUNT NAME|ACCOUNT EMAIL|ACCOUNT STATUS/)).not.toBeInTheDocument();
  });

  it("exports the current learning report filter", async () => {
    const user = userEvent.setup();
    renderPage();

    await screen.findByText("张敏");
    await user.selectOptions(screen.getByLabelText("视频"), "7");
    await user.selectOptions(screen.getByLabelText("完成状态"), "completed");
    await user.click(screen.getByRole("button", { name: "导出学习报表" }));

    await waitFor(() => expect(learningApi.downloadLearningReportExport).toHaveBeenCalled());
    expect(learningApi.downloadLearningReportExport.mock.calls[0][0]).toEqual({
      videoId: "7",
      status: "completed",
    });
  });

  it("retries the prerequisite video query before retrying the report", async () => {
    learningApi.getAdminLearningVideos
      .mockRejectedValueOnce(new Error("video list unavailable"))
      .mockResolvedValueOnce([video]);
    const user = userEvent.setup();
    renderPage();

    expect(await screen.findByRole("heading", { name: "报表加载失败。" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "重试" }));

    await waitFor(() => expect(learningApi.getAdminLearningVideos).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(learningApi.getLearningReport).toHaveBeenCalled());
  });
});
