import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
    expect(screen.getByRole("main")).not.toHaveClass("max-w-6xl");
    expect(screen.queryByRole("contentinfo")).not.toBeInTheDocument();
  });

  it("locks Admin Workbench to admin navigation without candidate or focus chrome", () => {
    renderAdminShell();

    expect(screen.getByRole("link", { name: "仪表盘" })).toHaveAttribute(
      "href",
      "/admin/dashboard",
    );
    expect(screen.getByRole("link", { name: "考试编排" })).toHaveAttribute("href", "/admin/exams");
    expect(screen.queryByRole("link", { name: "返回考试列表首页" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "学习" })).not.toHaveAttribute("href", "/learning");
    expect(screen.queryByRole("region", { name: "题号导航" })).not.toBeInTheDocument();
  });

  it("preserves logout and returns to the admin login route", async () => {
    renderAdminShell();

    await userEvent.setup().click(screen.getByRole("button", { name: "退出登录" }));

    expect(await screen.findByText("管理员登录")).toBeInTheDocument();
    expect(window.sessionStorage.getItem("internal-exam-admin-token")).toBeNull();
  });

  it("redirects an unauthenticated admin route to admin login", async () => {
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

    render(<RouterProvider router={router} />);

    expect(await screen.findByText("管理员登录")).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/admin/login");
  });
});
