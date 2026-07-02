import { render, screen } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";

import { AdminLayout } from "@/components/layout/AdminLayout";
import { setAdminToken } from "@/lib/adminSession";

function mockMediaQuery(matches: boolean) {
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

function renderAdminShell() {
  mockMediaQuery(true);
  setAdminToken("admin-token");

  const router = createMemoryRouter(
    [
      {
        path: "/admin",
        element: <AdminLayout />,
        children: [{ path: "dashboard", element: <div>仪表盘内容</div> }],
      },
      { path: "/admin/login", element: <div>管理员登录</div> },
    ],
    { initialEntries: ["/admin/dashboard"] },
  );

  return render(<RouterProvider router={router} />);
}

describe("AdminLayout", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
  });

  it("renders the authenticated admin app shell without a global footer", () => {
    renderAdminShell();

    expect(screen.getByText("仪表盘内容")).toBeInTheDocument();
    expect(screen.getByRole("navigation")).toBeInTheDocument();
    expect(screen.queryByRole("contentinfo")).not.toBeInTheDocument();
  });
});
