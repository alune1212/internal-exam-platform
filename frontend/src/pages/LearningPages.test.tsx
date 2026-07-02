import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Outlet, RouterProvider, createMemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type React from "react";

import { getLearningVideo, getLearningVideos, updateLearningProgress } from "@/api/learning";
import type { CandidateSessionContext } from "@/components/layout/CandidateLayout";
import { CandidateLayout } from "@/components/layout/CandidateLayout";
import { clearCurrentCandidate } from "@/lib/candidateSession";
import { LearningListPage } from "@/pages/LearningListPage";
import { LearningVideoPage } from "@/pages/LearningVideoPage";
import { LoginPage } from "@/pages/LoginPage";
import type { Candidate } from "@/types/candidate";
import type { CandidateLearningVideo } from "@/types/learning";

vi.mock("@/api/auth", () => ({
  loginCandidate: vi.fn(),
}));

vi.mock("@/api/learning", () => ({
  getLearningVideos: vi.fn(),
  getLearningVideo: vi.fn(),
  updateLearningProgress: vi.fn(),
}));

const candidate: Candidate = {
  id: 1,
  token: "candidate-token",
  name: "张敏",
  employee_no: "E1001",
  department: "产品部",
  should_attend: true,
  status: "active",
};

const video: CandidateLearningVideo = {
  id: 9,
  title: "安全培训",
  description: "观看基础安全要求。",
  original_filename: "safety.mp4",
  storage_key: "opaque.mp4",
  content_type: "video/mp4",
  file_size_bytes: 1024,
  duration_seconds: 120,
  completion_threshold_percent: 90,
  status: "published",
  uploaded_at: "2026-07-02T00:00:00Z",
  created_at: "2026-07-02T00:00:00Z",
  updated_at: "2026-07-02T00:00:00Z",
  playback_url: "/media/learning/opaque.mp4",
  progress: {
    last_position_seconds: 0,
    watched_seconds: 0,
    completion_percent: 0,
    completed_at: null,
    last_heartbeat_at: null,
  },
};

function renderWithQuery(ui: React.ReactElement) {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
        })
      }
    >
      {ui}
    </QueryClientProvider>,
  );
}

function CandidateContext({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
        })
      }
    >
      {children}
    </QueryClientProvider>
  );
}

function renderLearningPage(
  routePath: string,
  element: React.ReactElement,
  initialEntry: string,
  contextCandidate: Candidate | null = candidate,
) {
  const router = createMemoryRouter(
    [
      {
        path: "/",
        element: (
          <Outlet
            context={
              {
                candidate: contextCandidate,
                loginCandidate: vi.fn(),
                logoutCandidate: vi.fn(),
              } satisfies CandidateSessionContext
            }
          />
        ),
        children: [{ path: routePath, element }],
      },
    ],
    { initialEntries: [initialEntry] },
  );

  return renderWithQuery(<RouterProvider router={router} />);
}

describe("Learning pages", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clearCurrentCandidate();
    window.localStorage.clear();
    window.sessionStorage.clear();
  });

  it("does not fetch learning videos before candidate context exists", () => {
    renderLearningPage("learning", <LearningListPage />, "/learning", null);

    expect(vi.mocked(getLearningVideos)).not.toHaveBeenCalled();
  });

  it("renders candidate learning video progress and completion state", async () => {
    vi.mocked(getLearningVideos).mockResolvedValueOnce([
      {
        ...video,
        progress: {
          ...video.progress,
          completion_percent: 90,
          completed_at: "2026-07-02T01:00:00Z",
        },
      },
    ]);

    renderLearningPage("learning", <LearningListPage />, "/learning");

    expect(await screen.findByRole("heading", { name: "安全培训" })).toBeInTheDocument();
    expect(screen.getByText("已完成")).toBeInTheDocument();
    expect(screen.getByText("90%")).toBeInTheDocument();
  });

  it("renders learning query failures as explicit errors", async () => {
    vi.mocked(getLearningVideos).mockRejectedValueOnce(new Error("learning unavailable"));

    renderLearningPage("learning", <LearningListPage />, "/learning");

    expect(await screen.findByText("学习视频加载失败。")).toBeInTheDocument();
  });

  it("returns to login when opening learning without a session", async () => {
    const router = createMemoryRouter(
      [
        {
          path: "/",
          element: <CandidateLayout />,
          children: [
            { path: "login", element: <LoginPage /> },
            { path: "learning", element: <LearningListPage /> },
          ],
        },
      ],
      { initialEntries: ["/learning"] },
    );

    render(
      <CandidateContext>
        <RouterProvider router={router} />
      </CandidateContext>,
    );

    expect(await screen.findByRole("heading", { name: "入场核验" })).toBeInTheDocument();
    expect(vi.mocked(getLearningVideos)).not.toHaveBeenCalled();
  });

  it("renders the video player and sends progress heartbeat from watched interval", async () => {
    vi.mocked(getLearningVideo).mockResolvedValueOnce(video);
    vi.mocked(updateLearningProgress).mockResolvedValueOnce({
      ...video.progress,
      last_position_seconds: 10,
      watched_seconds: 10,
      completion_percent: 8,
    });
    renderLearningPage("learning/:videoId", <LearningVideoPage />, "/learning/9");

    const player = (await screen.findByTestId("learning-video-shell")).querySelector(
      "video",
    ) as HTMLVideoElement;
    Object.defineProperty(player, "currentTime", { configurable: true, value: 0 });
    fireEvent.play(player);
    Object.defineProperty(player, "currentTime", { configurable: true, value: 10 });
    fireEvent.pause(player);

    await waitFor(() =>
      expect(updateLearningProgress).toHaveBeenCalledWith(9, {
        current_position_seconds: 10,
        watched_start_seconds: 0,
        watched_end_seconds: 10,
      }),
    );
  });
});
