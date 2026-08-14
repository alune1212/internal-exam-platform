import { render, screen } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { RouteErrorPage } from "../RouteErrorPage";

describe("RouteErrorPage", () => {
  it("offers user-triggered reload and safe-home actions for a route failure", async () => {
    const onReload = vi.fn();
    const router = createMemoryRouter(
      [
        {
          path: "/broken",
          loader: () => {
            throw new Error("chunk unavailable");
          },
          errorElement: <RouteErrorPage onReload={onReload} safePath="/safe" />,
        },
        { path: "/safe", element: <p>安全入口</p> },
      ],
      { initialEntries: ["/broken"] },
    );

    render(<RouterProvider router={router} />);

    expect(await screen.findByRole("heading", { name: "页面暂时无法打开。" })).toBeInTheDocument();
    expect(screen.getByText("页面资源暂时不可用，请重试或返回安全入口。")).toBeInTheDocument();

    screen.getByRole("button", { name: "重新加载" }).click();
    expect(onReload).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("heading", { name: "页面暂时无法打开。" })).toBeInTheDocument();

    screen.getByRole("button", { name: "返回首页" }).click();
    expect(await screen.findByText("安全入口")).toBeInTheDocument();
  });
});
