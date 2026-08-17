import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { loginAdmin } from "@/api/auth";
import { getAdminToken } from "@/lib/adminSession";
import { AdminLoginPage } from "@/pages/admin/AdminLoginPage";

vi.mock("@/api/auth", () => ({
  loginAdmin: vi.fn(),
}));

const store = new Map<string, string>();
const mockStorage: Storage = {
  getItem: (key: string) => store.get(key) ?? null,
  setItem: (key: string, value: string) => {
    store.set(key, value);
  },
  removeItem: (key: string) => {
    store.delete(key);
  },
  clear: () => {
    store.clear();
  },
  get length() {
    return store.size;
  },
  key: (index: number) => [...store.keys()][index] ?? null,
};

Object.defineProperty(window, "localStorage", { value: mockStorage });

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AdminLoginPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("AdminLoginPage", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    vi.clearAllMocks();
    vi.mocked(loginAdmin).mockResolvedValue({
      token: "signed-session-token",
      token_type: "bearer",
    });
  });

  it("renders a Chinese-first admin auth canvas", () => {
    renderPage();

    expect(screen.getByText("管理员登录")).toBeInTheDocument();
    expect(screen.getByLabelText("管理员账号")).toBeInTheDocument();
    expect(screen.getByLabelText("密码")).toBeInTheDocument();
  });

  it("keeps one heading, one governed form surface, and one primary action", () => {
    renderPage();

    expect(screen.getByTestId("admin-login-header")).toHaveAttribute("data-page-header");
    expect(screen.getByRole("heading", { level: 1, name: "进入管理后台" })).toHaveClass(
      "font-display",
      "text-display-lg",
    );
    expect(screen.getByTestId("admin-login-form-section")).toHaveAttribute(
      "data-surface-owner",
      "panel",
    );
    expect(screen.getByRole("group", { name: "管理后台登录操作" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "进入管理后台" })).toBeInTheDocument();
    expect(screen.getByRole("main")).toHaveAttribute("data-auth-canvas", "admin");
    expect(screen.getByTestId("admin-login-canvas-content")).toHaveClass("landscape:grid");
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
    expect(screen.queryByRole("contentinfo")).not.toBeInTheDocument();
    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
  });

  it("stores the returned session token instead of the password", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText("管理员账号"), "admin");
    await user.type(screen.getByLabelText("密码"), "change-me");
    await user.click(screen.getByRole("button", { name: /进入管理后台/ }));

    await waitFor(() => expect(getAdminToken()).toBe("signed-session-token"));
    expect(getAdminToken()).not.toBe("change-me");
  });

  it("exposes credential failures as an actionable alert", async () => {
    const user = userEvent.setup();
    vi.mocked(loginAdmin).mockRejectedValueOnce(new Error("invalid credentials"));
    renderPage();

    await user.type(screen.getByLabelText("管理员账号"), "admin");
    await user.type(screen.getByLabelText("密码"), "wrong");
    await user.click(screen.getByRole("button", { name: "进入管理后台" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("账号或密码不正确。");
    expect(getAdminToken()).toBeNull();
  });
});
