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
    vi.clearAllMocks();
    vi.mocked(loginAdmin).mockResolvedValue({
      token: "signed-session-token",
      token_type: "bearer",
    });
  });

  it("renders the semantic admin login eyebrow", () => {
    renderPage();

    expect(screen.getByText("ADMIN · 登录")).toBeInTheDocument();
  });

  it("renders as a clean auth canvas without admin navigation or footer", () => {
    renderPage();

    expect(screen.getByText("ADMIN · 登录")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "登录管理后台" })).toHaveClass(
      "font-display",
      "text-display-lg",
    );
    expect(screen.getByTestId("admin-login-header")).toBeInTheDocument();
    expect(screen.getByTestId("admin-login-form-section")).toHaveClass("rounded-md");
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
    expect(screen.queryByRole("contentinfo")).not.toBeInTheDocument();
  });

  it("stores the returned session token instead of the password", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText(/Username/), "admin");
    await user.type(screen.getByLabelText(/Password/), "change-me");
    await user.click(screen.getByRole("button", { name: /登录管理后台/ }));

    await waitFor(() => expect(getAdminToken()).toBe("signed-session-token"));
    expect(getAdminToken()).not.toBe("change-me");
  });
});
