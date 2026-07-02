import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const learningApi = vi.hoisted(() => ({
  archiveLearningVideo: vi.fn(),
  getAdminLearningVideos: vi.fn(),
  publishLearningVideo: vi.fn(),
  updateAdminLearningVideo: vi.fn(),
  uploadLearningVideo: vi.fn(),
}));

vi.mock("@/api/learning", () => learningApi);

import { AdminLearningVideoPage } from "@/pages/admin/LearningVideoPage";
import type { LearningVideo } from "@/types/learning";

const draftVideo: LearningVideo = {
  id: 1,
  title: "草稿视频",
  description: null,
  original_filename: "draft.mp4",
  storage_key: "draft-storage.mp4",
  content_type: "video/mp4",
  file_size_bytes: 1024,
  duration_seconds: 120,
  completion_threshold_percent: 90,
  status: "draft",
  uploaded_at: "2026-07-02T00:00:00Z",
  created_at: "2026-07-02T00:00:00Z",
  updated_at: "2026-07-02T00:00:00Z",
  playback_url: "/media/learning/draft-storage.mp4",
};

const publishedVideo: LearningVideo = {
  ...draftVideo,
  id: 2,
  title: "已发布视频",
  original_filename: "published.mp4",
  storage_key: "published-storage.mp4",
  status: "published",
  playback_url: "/media/learning/published-storage.mp4",
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
      <MemoryRouter initialEntries={["/admin/learning"]}>
        <AdminLearningVideoPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("AdminLearningVideoPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockMediaQuery();
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:learning-video"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });
    learningApi.getAdminLearningVideos.mockResolvedValue([draftVideo, publishedVideo]);
    learningApi.uploadLearningVideo.mockResolvedValue(draftVideo);
    learningApi.publishLearningVideo.mockResolvedValue({ ...draftVideo, status: "published" });
    learningApi.archiveLearningVideo.mockResolvedValue({ ...publishedVideo, status: "archived" });
  });

  it("keeps upload disabled until a playable video duration is captured", async () => {
    const user = userEvent.setup();
    renderPage();

    expect(await screen.findByText("草稿视频")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "上传视频" })).toBeDisabled();

    const file = new File(["video"], "safety.mp4", { type: "video/mp4" });
    await user.upload(screen.getByLabelText("选择视频文件"), file);

    expect(screen.getByLabelText("视频标题")).toHaveValue("safety");
    const probe = await screen.findByTestId("learning-duration-probe");
    Object.defineProperty(probe, "duration", { configurable: true, value: 125 });
    fireEvent.loadedMetadata(probe);

    expect(await screen.findByText("已读取时长 2:05")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "上传视频" }));

    await waitFor(() => expect(learningApi.uploadLearningVideo).toHaveBeenCalled());
    expect(learningApi.uploadLearningVideo.mock.calls[0][0]).toEqual({
      title: "safety",
      description: null,
      duration_seconds: 125,
      file,
    });
  });

  it("shows upload errors returned by the API", async () => {
    const user = userEvent.setup();
    learningApi.uploadLearningVideo.mockRejectedValueOnce(new Error("文件过大"));
    renderPage();

    const file = new File(["video"], "large.mp4", { type: "video/mp4" });
    await user.upload(await screen.findByLabelText("选择视频文件"), file);
    const probe = await screen.findByTestId("learning-duration-probe");
    Object.defineProperty(probe, "duration", { configurable: true, value: 60 });
    fireEvent.loadedMetadata(probe);
    await user.click(screen.getByRole("button", { name: "上传视频" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("文件过大");
  });

  it("publishes and archives videos from the list", async () => {
    const user = userEvent.setup();
    renderPage();

    expect(await screen.findByText("已发布视频")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "发布" }));
    await waitFor(() => expect(learningApi.publishLearningVideo).toHaveBeenCalled());
    expect(learningApi.publishLearningVideo.mock.calls[0][0]).toBe(1);

    await user.click(screen.getAllByRole("button", { name: "归档" })[1]);
    await waitFor(() => expect(learningApi.archiveLearningVideo).toHaveBeenCalled());
    expect(learningApi.archiveLearningVideo.mock.calls[0][0]).toBe(2);
  });
});
