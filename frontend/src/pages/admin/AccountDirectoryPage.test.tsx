import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getAdminAccounts, updateAdminAccountStatus } from "@/api/accounts";
import { AccountDirectoryPage } from "@/pages/admin/AccountDirectoryPage";

vi.mock("@/api/accounts", () => ({
  getAdminAccounts: vi.fn(),
  updateAdminAccountStatus: vi.fn(),
}));

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
});
