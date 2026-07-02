import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { AdminSideRail } from "@/components/layout/AdminSideRail";

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

function renderSideRail(initialPath: string, matches = true) {
  mockMediaQuery(matches);

  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <AdminSideRail onLogout={() => {}} />
    </MemoryRouter>,
  );
}

describe("AdminSideRail", () => {
  it("renders all five admin nav items", () => {
    renderSideRail("/admin/dashboard");
    expect(screen.getByRole("link", { name: "仪表盘" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "题库" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "导入" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "考试" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "报表" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "退出登录" })).toBeInTheDocument();
  });

  it("orders nav items to match the admin chapter sequence", () => {
    renderSideRail("/admin/dashboard");
    const navNames = screen
      .getAllByRole("link")
      .map((link) => link.textContent)
      .filter((name): name is string =>
        Boolean(name && ["仪表盘", "考试", "题库", "导入", "报表"].includes(name)),
      );

    expect(navNames).toEqual(["仪表盘", "考试", "题库", "导入", "报表"]);
  });

  it("renders the dark wordmark with the admin subtitle", () => {
    renderSideRail("/admin/dashboard");
    const wordmarkLink = screen.getByRole("link", { name: /返回管理后台首页/ });
    expect(wordmarkLink).toBeInTheDocument();
    expect(screen.getByText(/admin/i)).toBeInTheDocument();
  });

  it("highlights the active route with white text and white background", () => {
    renderSideRail("/admin/dashboard");
    const activeLink = screen.getByRole("link", { name: "仪表盘" });
    expect(activeLink).toHaveClass("bg-canvas");
    expect(activeLink).toHaveClass("text-ink");
  });

  it("only highlights import on the question import route", () => {
    renderSideRail("/admin/questions/import");
    const questionLink = screen.getByRole("link", { name: "题库" });
    const importLink = screen.getByRole("link", { name: "导入" });

    expect(importLink).toHaveClass("bg-canvas");
    expect(importLink).toHaveClass("text-ink");
    expect(questionLink).toHaveClass("text-footer-soft");
    expect(questionLink).not.toHaveClass("bg-canvas");
  });

  it("keeps the reports nav item active across report subpages", () => {
    renderSideRail("/admin/reports/wrong");
    const reportsLink = screen.getByRole("link", { name: "报表" });

    expect(reportsLink).toHaveClass("bg-canvas");
    expect(reportsLink).toHaveClass("text-ink");
  });

  it("applies dark background to the desktop aside container", () => {
    const { container } = renderSideRail("/admin/dashboard");
    const aside = container.querySelector("aside");
    expect(aside).toHaveClass("bg-footer");
  });

  it("keeps the desktop rail viewport-stable", () => {
    const { container } = renderSideRail("/admin/questions");
    const aside = container.querySelector("aside");
    expect(aside).toHaveClass("sticky");
    expect(aside).toHaveClass("top-0");
    expect(aside).toHaveClass("h-dvh");
    expect(aside).toHaveClass("overflow-hidden");
    expect(screen.getByRole("button", { name: "退出登录" })).toHaveClass("w-full");
  });

  it("opens the mobile sheet when the menu button is triggered", async () => {
    const user = userEvent.setup();
    renderSideRail("/admin/dashboard", false);

    await user.click(screen.getByRole("button", { name: "打开菜单" }));

    expect(await screen.findByText("导航")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "退出登录" })).toBeInTheDocument();
  });

  it("uses high-contrast light link colors inside the mobile sheet", async () => {
    const user = userEvent.setup();
    renderSideRail("/admin/dashboard", false);

    await user.click(screen.getByRole("button", { name: "打开菜单" }));

    const inactiveLink = await screen.findByRole("link", { name: "题库" });
    expect(inactiveLink).toHaveClass("text-body-sm");
    expect(inactiveLink).toHaveClass("text-muted");
    expect(inactiveLink).toHaveClass("hover:bg-surface-card");
    expect(inactiveLink).toHaveClass("hover:text-ink");
    expect(inactiveLink).not.toHaveClass("text-footer-soft");
    expect(inactiveLink).not.toHaveClass("hover:text-white");
  });

  it("marks the mobile sticky header as scrolled after the page scrolls", async () => {
    Object.defineProperty(window, "scrollY", { configurable: true, value: 0 });
    const { container } = renderSideRail("/admin/dashboard", false);
    const header = container.firstElementChild;
    expect(header).toHaveAttribute("data-scrolled", "false");

    Object.defineProperty(window, "scrollY", { configurable: true, value: 24 });
    window.dispatchEvent(new Event("scroll"));

    await waitFor(() => expect(header).toHaveAttribute("data-scrolled", "true"));
  });
});
