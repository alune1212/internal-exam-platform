import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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
    expect(screen.getByText("safety.mp4 · 1 KiB")).toBeInTheDocument();
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
    expect(await screen.findByText("视频已上传为草稿。")).toBeInTheDocument();
  });

  it("uses a focusable product control to open the native file picker", async () => {
    const user = userEvent.setup();
    renderPage();

    const input = await screen.findByLabelText("选择视频文件");
    const clickSpy = vi.spyOn(input, "click");
    const trigger = screen.getByRole("button", { name: "选择视频文件" });

    expect(input).toHaveClass("hidden");
    expect(screen.getAllByRole("button", { name: "选择视频文件" })).toHaveLength(1);
    expect(trigger.tagName).toBe("BUTTON");
    trigger.focus();
    expect(trigger).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(clickSpy).toHaveBeenCalledTimes(1);
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

  it("associates unreadable video metadata with the file field and blocks upload", async () => {
    const user = userEvent.setup();
    renderPage();

    const file = new File(["video"], "broken.mp4", { type: "video/mp4" });
    await user.upload(await screen.findByLabelText("选择视频文件"), file);
    const probe = await screen.findByTestId("learning-duration-probe");
    Object.defineProperty(probe, "duration", { configurable: true, value: 0 });
    fireEvent.loadedMetadata(probe);

    const fileInput = screen.getByLabelText("选择视频文件");
    expect(await screen.findByRole("alert")).toHaveTextContent("无法读取视频时长");
    expect(fileInput).toHaveAttribute("aria-invalid", "true");
    expect(fileInput).toHaveAttribute(
      "aria-describedby",
      "learning-video-file-status learning-video-file-error",
    );
    expect(screen.getByRole("button", { name: "上传视频" })).toBeDisabled();
  });

  it("keeps upload controls busy while the upload is pending", async () => {
    const user = userEvent.setup();
    let resolveUpload!: (video: LearningVideo) => void;
    learningApi.uploadLearningVideo.mockReturnValueOnce(
      new Promise<LearningVideo>((resolve) => {
        resolveUpload = resolve;
      }),
    );
    renderPage();

    const file = new File(["video"], "pending.mp4", { type: "video/mp4" });
    await user.upload(await screen.findByLabelText("选择视频文件"), file);
    const probe = await screen.findByTestId("learning-duration-probe");
    Object.defineProperty(probe, "duration", { configurable: true, value: 60 });
    fireEvent.loadedMetadata(probe);
    await user.click(screen.getByRole("button", { name: "上传视频" }));

    const uploadButton = await screen.findByRole("button", { name: "上传中" });
    expect(uploadButton).toBeDisabled();
    expect(uploadButton).toHaveAttribute("aria-busy", "true");
    expect(
      screen.getByTestId("admin-learning-video-shell").querySelector('[data-surface-role="panel"]'),
    ).toHaveAttribute("aria-busy", "true");

    resolveUpload(draftVideo);
    expect(await screen.findByText("视频已上传为草稿。")).toBeInTheDocument();
  });

  it("renders a recoverable query error and retries through the page state", async () => {
    const user = userEvent.setup();
    learningApi.getAdminLearningVideos.mockRejectedValueOnce(new Error("服务暂不可用"));
    renderPage();

    expect(await screen.findByText("视频列表加载失败。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "重试" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "重试" }));
    expect(await screen.findByText("草稿视频")).toBeInTheDocument();
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

  it("opens the edit dialog with long values, restores focus, and saves with the form action", async () => {
    const user = userEvent.setup();
    const longTitle = "一条用于验证编辑弹层换行和内容边界的超长学习视频标题".repeat(4);
    const longDescription = "学习说明包含连续文本和较长的中文内容，用于确认弹层内部可滚动。".repeat(
      8,
    );
    const longVideo = {
      ...draftVideo,
      title: longTitle,
      description: longDescription,
    };
    learningApi.getAdminLearningVideos.mockResolvedValueOnce([longVideo]);
    learningApi.updateAdminLearningVideo.mockResolvedValueOnce({
      ...longVideo,
      title: "更新后标题",
    });
    renderPage();

    const editTrigger = await screen.findByRole("button", { name: "编辑" });
    editTrigger.focus();
    await user.click(editTrigger);

    const dialog = await screen.findByRole("dialog", { name: "编辑视频信息" });
    expect(dialog).toHaveClass("overflow-y-auto");
    expect(within(dialog).getByLabelText("视频标题")).toHaveValue(longTitle);
    expect(within(dialog).getByLabelText("视频说明")).toHaveValue(longDescription);
    expect(within(dialog).getByRole("button", { name: "保存" })).toBeEnabled();

    await user.clear(within(dialog).getByLabelText("视频标题"));
    await user.type(within(dialog).getByLabelText("视频标题"), "更新后标题");
    await user.click(within(dialog).getByRole("button", { name: "保存" }));

    await waitFor(() =>
      expect(learningApi.updateAdminLearningVideo).toHaveBeenCalledWith(1, {
        title: "更新后标题",
        description: longDescription,
      }),
    );
    expect(await screen.findByText("视频信息已保存。")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(screen.getAllByRole("button", { name: "编辑" })[0]).toHaveFocus();
  });

  it("keeps the edit dialog open and exposes save errors inside the overlay", async () => {
    const user = userEvent.setup();
    learningApi.updateAdminLearningVideo.mockRejectedValueOnce(new Error("标题保存失败"));
    renderPage();

    const editTrigger = await screen.findAllByRole("button", { name: "编辑" });
    await user.click(editTrigger[0]);
    await user.click(screen.getByRole("button", { name: "保存" }));

    const dialog = await screen.findByRole("dialog", { name: "编辑视频信息" });
    expect(dialog).toHaveTextContent("标题保存失败");
    expect(dialog.querySelector('[role="alert"]')).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "保存" })).toBeEnabled();
  });

  it("marks the edit fields and save action busy while the update is pending", async () => {
    const user = userEvent.setup();
    let resolveUpdate!: (video: LearningVideo) => void;
    learningApi.updateAdminLearningVideo.mockReturnValueOnce(
      new Promise<LearningVideo>((resolve) => {
        resolveUpdate = resolve;
      }),
    );
    renderPage();

    await user.click((await screen.findAllByRole("button", { name: "编辑" }))[0]);
    const dialog = await screen.findByRole("dialog", { name: "编辑视频信息" });
    await user.click(within(dialog).getByRole("button", { name: "保存" }));

    const saveButton = await within(dialog).findByRole("button", { name: "保存中" });
    expect(saveButton).toBeDisabled();
    expect(saveButton).toHaveAttribute("aria-busy", "true");
    expect(dialog.querySelector("form")).toHaveAttribute("aria-busy", "true");
    expect(within(dialog).getByLabelText("视频标题")).toBeDisabled();
    expect(within(dialog).getByLabelText("视频说明")).toBeDisabled();

    resolveUpdate(draftVideo);
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });
});
