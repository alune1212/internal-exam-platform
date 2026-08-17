import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Outlet, RouterProvider, createMemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getCandidateProfile, updateCandidateProfile } from "@/api/auth";
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
    expect(
      screen.getByRole("heading", { name: "账号资料" }).closest("[data-density]"),
    ).toHaveAttribute("data-density", "calm");
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
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

  it("uses the semantic reading frame and preserves long profile text", async () => {
    const longName = "这是一个用于验证资料输入在窄屏下仍可保留的超长显示姓名";
    const longProfile = { ...profile, display_name: longName };
    vi.mocked(getCandidateProfile).mockResolvedValue(longProfile);

    renderProfilePage();

    expect(await screen.findByDisplayValue(longName)).toBeInTheDocument();
    expect(screen.getByTestId("candidate-profile-shell")).toHaveAttribute("data-width", "reading");
    expect(screen.getByTestId("candidate-profile-form-section")).toHaveAttribute(
      "data-surface-role",
      "panel",
    );
    expect(screen.getByRole("group", { name: "资料保存操作" })).toBeInTheDocument();
  });

  it("shows pending and success states while keeping the profile update payload unchanged", async () => {
    const user = userEvent.setup();
    let resolveUpdate: (value: CandidateProfile) => void = () => undefined;
    const pendingUpdate = new Promise<CandidateProfile>((resolve) => {
      resolveUpdate = resolve;
    });
    vi.mocked(getCandidateProfile).mockResolvedValue(profile);
    vi.mocked(updateCandidateProfile).mockReturnValueOnce(pendingUpdate);

    renderProfilePage();

    const displayName = await screen.findByLabelText("显示姓名");
    await user.clear(displayName);
    await user.type(displayName, "李四");
    await user.click(screen.getByRole("button", { name: "保存显示姓名" }));

    expect(vi.mocked(updateCandidateProfile).mock.calls[0]?.[0]).toEqual({ display_name: "李四" });
    expect(screen.getByRole("button", { name: /保存显示姓名/ })).toBeDisabled();
    expect(
      screen.getByTestId("candidate-profile-form-section").querySelector("form"),
    ).toHaveAttribute("aria-busy", "true");
    expect(displayName).toBeDisabled();

    resolveUpdate({ ...profile, display_name: "李四" });
    expect(await screen.findByText("资料已更新，正式考试名单保持不变。")).toBeInTheDocument();
  });

  it("keeps keyboard validation local and reports a recoverable save error", async () => {
    const user = userEvent.setup();
    vi.mocked(getCandidateProfile).mockResolvedValue(profile);
    vi.mocked(updateCandidateProfile).mockRejectedValueOnce(new Error("save unavailable"));

    renderProfilePage();

    const displayName = await screen.findByLabelText("显示姓名");
    await user.clear(displayName);
    await user.keyboard("{Enter}");
    expect(await screen.findByText("请输入姓名")).toBeInTheDocument();
    expect(updateCandidateProfile).not.toHaveBeenCalled();

    await user.type(displayName, "王五");
    await user.keyboard("{Enter}");
    expect(await screen.findByRole("alert")).toHaveTextContent("资料保存失败，请稍后重试。");
  });
});
