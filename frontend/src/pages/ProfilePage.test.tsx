import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Outlet, RouterProvider, createMemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getCandidateProfile } from "@/api/auth";
import type { CandidateSessionContext } from "@/components/layout/CandidateLayout";
import { ProfilePage } from "@/pages/ProfilePage";
import type { Candidate, CandidateProfile } from "@/types/candidate";

vi.mock("@/api/auth", () => ({
  getCandidateProfile: vi.fn(),
  updateCandidateProfile: vi.fn(),
}));

const candidate: Candidate = {
  id: 42,
  token: "candidate-token",
  token_expires_at: "2099-01-01T00:00:00.000Z",
  email: "zhangsan@example.com",
  display_name: "张三",
  status: "active",
};

const profile: CandidateProfile = {
  id: candidate.id,
  email: candidate.email,
  display_name: candidate.display_name,
  status: "active",
};

const profileQueryKey = ["candidate", candidate.id, "profile"];

function renderProfilePage(queryClient = createQueryClient()) {
  const router = createMemoryRouter(
    [
      {
        path: "/",
        element: (
          <Outlet
            context={
              {
                candidate,
                loginCandidate: vi.fn(),
                logoutCandidate: vi.fn(),
              } satisfies CandidateSessionContext
            }
          />
        ),
        children: [{ path: "profile", element: <ProfilePage /> }],
      },
    ],
    { initialEntries: ["/profile"] },
  );

  return {
    queryClient,
    ...render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    ),
  };
}

function createQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

describe("ProfilePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("recovers from a first-load error after an explicit retry", async () => {
    vi.mocked(getCandidateProfile)
      .mockRejectedValueOnce(new Error("temporary outage"))
      .mockResolvedValueOnce(profile);

    renderProfilePage();

    expect(await screen.findByRole("heading", { name: "账号资料加载失败。" })).toBeInTheDocument();

    await userEvent.setup().click(screen.getByRole("button", { name: "重试" }));

    expect(await screen.findByRole("heading", { name: "账号资料" })).toBeInTheDocument();
    expect(screen.getByDisplayValue(profile.email)).toBeInTheDocument();
    await waitFor(() => expect(getCandidateProfile).toHaveBeenCalledTimes(2));
  });

  it("keeps cached profile content visible when a refresh fails and retries it", async () => {
    const queryClient = createQueryClient();
    queryClient.setQueryData(profileQueryKey, profile);
    vi.mocked(getCandidateProfile)
      .mockRejectedValueOnce(new Error("background refresh failed"))
      .mockResolvedValueOnce({ ...profile, display_name: "李四" });

    renderProfilePage(queryClient);

    const staleNotice = await screen.findByTestId("page-stale-warning");
    expect(staleNotice).toHaveTextContent("当前显示上一次成功的数据。");
    expect(staleNotice).toHaveTextContent("上次成功更新于");
    expect(screen.getByDisplayValue(profile.email)).toBeInTheDocument();
    expect(screen.getByDisplayValue(profile.display_name ?? "")).toBeInTheDocument();

    await userEvent.setup().click(screen.getByRole("button", { name: "重试" }));

    expect(await screen.findByDisplayValue("李四")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByTestId("page-stale-warning")).not.toBeInTheDocument());
    expect(getCandidateProfile).toHaveBeenCalledTimes(2);
  });
});
