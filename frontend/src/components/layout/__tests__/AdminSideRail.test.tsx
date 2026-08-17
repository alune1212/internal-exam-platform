import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import { ADMIN_NAVIGATION_GROUPS, AdminSideRail } from "@/components/layout/AdminSideRail";

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
  const primaryLabels = ["仪表盘", "用户账户", "考试", "题库", "题库导入", "学习", "报表", "运维"];

  it("renders every primary admin destination exactly once", () => {
    renderSideRail("/admin/dashboard");
    expect(screen.getByRole("link", { name: "仪表盘" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "用户账户" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "题库" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "题库导入" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "考试" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "学习" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "报表" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "运维" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "退出登录" })).toBeInTheDocument();

    const renderedLabels = screen
      .getAllByRole("link")
      .map((link) => link.textContent)
      .filter((label): label is string => Boolean(label && primaryLabels.includes(label)));
    expect(renderedLabels).toHaveLength(primaryLabels.length);
  });

  it("preserves the exact ordered targets in the shared desktop model", () => {
    renderSideRail("/admin/dashboard");
    const nav = screen.getByRole("navigation", { name: "管理后台导航" });
    expect(
      within(nav)
        .getAllByRole("link")
        .map((link) => link.getAttribute("href")),
    ).toEqual([
      "/admin/dashboard",
      "/admin/questions",
      "/admin/questions/import",
      "/admin/learning",
      "/admin/exams",
      "/admin/reports/scores",
      "/admin/accounts",
      "/admin/operations",
    ]);
    expect(ADMIN_NAVIGATION_GROUPS.flatMap((group) => group.items.map((item) => item.to))).toEqual([
      "/admin/dashboard",
      "/admin/questions",
      "/admin/questions/import",
      "/admin/learning",
      "/admin/exams",
      "/admin/reports/scores",
      "/admin/accounts",
      "/admin/operations",
    ]);
  });

  it("orders grouped destinations in the canonical operational sequence", () => {
    renderSideRail("/admin/dashboard");
    const navNames = screen
      .getAllByRole("link")
      .map((link) => link.textContent)
      .filter((name): name is string => Boolean(name && primaryLabels.includes(name)));

    expect(navNames).toEqual([
      "仪表盘",
      "题库",
      "题库导入",
      "学习",
      "考试",
      "报表",
      "用户账户",
      "运维",
    ]);
    expect(
      screen
        .getAllByText(/^(概览|内容|考试|复盘|系统)/)
        .filter((label) => label.tagName === "P")
        .map((label) => label.textContent?.replace(" · 当前分组", "")),
    ).toEqual(["概览", "内容", "考试", "复盘", "系统"]);
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
    expect(activeLink).toHaveAttribute("aria-current", "page");
    expect(document.getElementById("admin-nav-group-overview")?.closest("section")).toHaveAttribute(
      "data-active-group",
      "true",
    );
    expect(document.getElementById("admin-nav-group-content")?.closest("section")).toHaveAttribute(
      "data-active-group",
      "false",
    );
  });

  it("only highlights import on the question import route", () => {
    renderSideRail("/admin/questions/import");
    const questionLink = screen.getByRole("link", { name: "题库" });
    const importLink = screen.getByRole("link", { name: "题库导入" });

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

  it("keeps the learning nav item active across learning subpages", () => {
    renderSideRail("/admin/learning/reports");
    const learningLink = screen.getByRole("link", { name: "学习" });

    expect(learningLink).toHaveClass("bg-canvas");
    expect(learningLink).toHaveClass("text-ink");
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
    expect(screen.getByTestId("admin-desktop-navigation-scroll")).toHaveClass("overflow-y-auto");
    expect(screen.getByTestId("admin-desktop-navigation-scroll")).toHaveClass("overscroll-contain");
  });

  it("keeps logout keyboard reachable and invokes the existing callback", async () => {
    const user = userEvent.setup();
    const onLogout = vi.fn();
    mockMediaQuery(true);

    render(
      <MemoryRouter initialEntries={["/admin/dashboard"]}>
        <AdminSideRail onLogout={onLogout} />
      </MemoryRouter>,
    );

    const logout = screen.getByRole("button", { name: "退出登录" });
    logout.focus();
    expect(document.activeElement).toBe(logout);
    await user.keyboard("{Enter}");
    expect(onLogout).toHaveBeenCalledTimes(1);
  });

  it("opens the mobile sheet when the menu button is triggered", async () => {
    const user = userEvent.setup();
    renderSideRail("/admin/dashboard", false);

    await user.click(screen.getByRole("button", { name: "打开菜单" }));

    expect(await screen.findByText("导航")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "退出登录" })).toBeInTheDocument();
  });

  it("keeps the grouped order and active item in the mobile sheet", async () => {
    const user = userEvent.setup();
    renderSideRail("/admin/exams/1/edit", false);

    await user.click(screen.getByRole("button", { name: "打开菜单" }));

    const nav = await screen.findByRole("navigation", { name: "管理后台导航" });
    const navNames = within(nav)
      .getAllByRole("link")
      .map((link) => link.textContent)
      .filter((label): label is string => Boolean(label && primaryLabels.includes(label)));
    expect(navNames).toEqual([
      "仪表盘",
      "题库",
      "题库导入",
      "学习",
      "考试",
      "报表",
      "用户账户",
      "运维",
    ]);
    expect(screen.getByRole("link", { name: "考试" })).toHaveAttribute("aria-current", "page");
    expect(document.getElementById("admin-nav-group-exams")?.closest("section")).toHaveAttribute(
      "data-active-group",
      "true",
    );
    expect(within(nav).getByRole("link", { name: "考试" })).toHaveAttribute("data-active", "true");
  });

  it("keeps mobile navigation internally scrollable with a reachable logout", async () => {
    const user = userEvent.setup();
    renderSideRail("/admin/dashboard", false);

    await user.click(screen.getByRole("button", { name: "打开菜单" }));

    const sheet = await screen.findByTestId("admin-mobile-navigation");
    expect(sheet).toHaveClass("max-h-[calc(100dvh-1rem)]");
    expect(sheet).toHaveClass("overflow-y-auto");
    expect(sheet).toHaveClass("overscroll-contain");
    expect(sheet).toHaveClass("pb-[calc(1.5rem+env(safe-area-inset-bottom))]");
    const logout = within(sheet).getByRole("button", { name: "退出登录" });
    logout.focus();
    expect(document.activeElement).toBe(logout);
  });

  it("keeps desktop and mobile navigation keyboard order and targets in parity", async () => {
    const desktop = renderSideRail("/admin/dashboard", true);
    const desktopNav = screen.getByRole("navigation", { name: "管理后台导航" });
    const desktopTargets = within(desktopNav)
      .getAllByRole("link")
      .map((link) => link.getAttribute("href"));
    desktop.unmount();

    const user = userEvent.setup();
    renderSideRail("/admin/dashboard", false);
    await user.click(screen.getByRole("button", { name: "打开菜单" }));
    const mobileNav = await screen.findByRole("navigation", { name: "管理后台导航" });
    expect(
      within(mobileNav)
        .getAllByRole("link")
        .map((link) => link.getAttribute("href")),
    ).toEqual(desktopTargets);
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
