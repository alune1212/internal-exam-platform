import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getAdminAccounts, updateAdminAccountStatus } from "@/api/accounts";
import { AccountDirectoryPage } from "@/pages/admin/AccountDirectoryPage";
import type { AdminAccount } from "@/types/account";

vi.mock("@/api/accounts", () => ({
  getAdminAccounts: vi.fn(),
  updateAdminAccountStatus: vi.fn(),
}));

function setMatchMedia(matches: boolean) {
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    writable: true,
    value: (query: string) => ({
      matches: query.includes("1024") ? matches : true,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }),
  });
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AccountDirectoryPage />
    </QueryClientProvider>,
  );
}

describe("AccountDirectoryPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setMatchMedia(true);
    vi.mocked(getAdminAccounts).mockResolvedValue([
      { id: 1, email: "active@example.com", display_name: "已注册用户", status: "active" },
      { id: 2, email: "pending@example.com", display_name: null, status: "pending" },
      { id: 3, email: "inactive@example.com", display_name: "已停用用户", status: "inactive" },
    ]);
    vi.mocked(updateAdminAccountStatus).mockImplementation(async (id, status) => ({
      id,
      email: `${id}@example.com`,
      display_name: "用户",
      status,
    }));
  });

  it("renders lifecycle states and keeps email/delete controls out of the directory", async () => {
    renderPage();

    expect(await screen.findByRole("heading", { name: "账户目录" })).toBeInTheDocument();
    expect(screen.getByTestId("account-directory-shell")).toHaveAttribute("data-width", "wide");
    expect(document.querySelector('[data-surface-role="data"]')).toBeInTheDocument();
    expect(screen.queryByText(/ACCOUNT NAME|EMAIL ·|STATUS ·|ACTION ·/)).not.toBeInTheDocument();
    expect(screen.getByText("待完成注册")).toBeInTheDocument();
    expect(screen.getAllByText("已启用").length).toBeGreaterThan(0);
    expect(screen.getByText("已停用")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /删除|编辑邮箱|修改邮箱/ }),
    ).not.toBeInTheDocument();
  });

  it("searches and toggles completed account status only", async () => {
    const user = userEvent.setup();
    renderPage();

    await screen.findByText("已注册用户");
    await user.clear(screen.getByLabelText("搜索邮箱或显示名"));
    await user.type(screen.getByLabelText("搜索邮箱或显示名"), "active@example.com");
    await user.click(screen.getByRole("button", { name: "搜索账户" }));
    await waitFor(() =>
      expect(getAdminAccounts).toHaveBeenLastCalledWith({
        query: "active@example.com",
        status: "all",
      }),
    );

    await user.click(screen.getByRole("button", { name: "停用账户" }));
    await waitFor(() => expect(updateAdminAccountStatus).toHaveBeenCalledWith(1, "inactive"));
  });

  it("keeps loading and empty states inside the data surface", async () => {
    const pending = deferred<AdminAccount[]>();
    vi.mocked(getAdminAccounts).mockReturnValueOnce(pending.promise);
    renderPage();

    expect(screen.getByRole("status")).toHaveAttribute("data-page-state", "loading");
    expect(
      document.querySelector('[data-surface-role="data"] [data-state-surface="inherit"]'),
    ).toBeInTheDocument();

    pending.resolve([]);
    expect(await screen.findByText("没有符合条件的账户。")).toBeInTheDocument();
  });

  it("offers a recoverable first-load error and supports retry", async () => {
    const user = userEvent.setup();
    vi.mocked(getAdminAccounts).mockRejectedValueOnce(new Error("账户服务暂不可用"));
    renderPage();

    expect(await screen.findByRole("heading", { name: "账户目录加载失败。" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "重试" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "重试" }));
    expect(await screen.findByText("已注册用户")).toBeInTheDocument();
  });

  it("exposes pending and confirmed status mutations", async () => {
    const user = userEvent.setup();
    const pending = deferred<AdminAccount>();
    vi.mocked(updateAdminAccountStatus).mockReturnValueOnce(pending.promise);
    renderPage();

    const action = await screen.findByRole("button", { name: "停用账户" });
    await user.click(action);

    await waitFor(() => {
      const pendingAction = screen.getByRole("button", { name: "停用账户" });
      expect(pendingAction).toHaveAttribute("aria-busy", "true");
      expect(pendingAction).toBeDisabled();
    });

    pending.resolve({
      id: 1,
      email: "active@example.com",
      display_name: "已注册用户",
      status: "inactive",
    });
    expect(await screen.findByText("账户已停用；其历史记录与名单快照仍保留。")).toBeInTheDocument();
  });

  it("keeps long account values wrapped in the responsive data representation", async () => {
    const longEmail = "candidate-with-a-very-long-unbroken-email-address@example.com";
    setMatchMedia(false);
    vi.mocked(getAdminAccounts).mockResolvedValueOnce([
      {
        id: 8,
        email: longEmail,
        display_name: "一段很长的应考人员显示姓名用于检查窄屏换行",
        status: "active",
      },
    ]);
    renderPage();

    const email = await screen.findByText(longEmail);
    expect(email).toHaveClass("break-words");
    expect(screen.getByTestId("account-directory-shell")).not.toHaveClass("max-w-3xl");
  });
});
