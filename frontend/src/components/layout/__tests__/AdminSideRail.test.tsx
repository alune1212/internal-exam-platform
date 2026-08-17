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
  const primaryLabels = [
    "仪表盘",
    "用户账户",
    "考试编排",
    "题库",
    "题库导入",
    "学习",
    "报表",
    "运维",
  ];

  it("renders every primary admin destination exactly once", () => {
    renderSideRail("/admin/dashboard");
    expect(screen.getByRole("link", { name: "仪表盘" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "用户账户" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "题库" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "题库导入" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "考试编排" })).toBeInTheDocument();
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
      "考试编排",
      "报表",
      "用户账户",
      "运维",
    ]);
    expect(
      ["content", "system"].map(
        (groupId) =>
          screen.getByRole("navigation").querySelector(`#admin-nav-group-${groupId}`)?.textContent,
      ),
    ).toEqual(["内容", "系统"]);
  });

  it("uses a stable four-block rhythm with explicit group and link spacing", () => {
    renderSideRail("/admin/dashboard");
    const nav = screen.getByRole("navigation", { name: "管理后台导航" });
    const groups = Array.from(nav.querySelectorAll<HTMLElement>("section[data-nav-group-id]"));

    expect(nav).toHaveClass("gap-1");
    expect(groups.map((group) => group.dataset.navGroupId)).toEqual([
      "overview",
      "content",
      "exams",
      "review",
      "system",
    ]);
    expect(groups.map((group) => group.dataset.visualBreakBefore)).toEqual([
      "false",
      "true",
      "true",
      "false",
      "true",
    ]);

    for (const group of groups) {
      expect(group).toHaveClass("gap-2");
      const links = within(group).getAllByRole("link");
      expect(links[0]?.parentElement).toHaveClass("gap-1");
    }
  });

  it("separates visible group headings with a hairline divider", () => {
    renderSideRail("/admin/dashboard");
    const nav = screen.getByRole("navigation", { name: "管理后台导航" });

    for (const groupId of ["content", "system"]) {
      const title = nav.querySelector<HTMLElement>(`#admin-nav-group-${groupId}`);
      expect(title).toHaveClass("flex", "items-center", "gap-2");
      expect(title?.querySelector("[data-nav-group-divider]")).toHaveClass("h-px", "flex-1");
      expect(title?.querySelector("[data-nav-group-divider]")).toHaveAttribute(
        "aria-hidden",
        "true",
      );
    }

    for (const groupId of ["overview", "exams", "review"]) {
      const title = nav.querySelector<HTMLElement>(`#admin-nav-group-${groupId}`);
      expect(title?.querySelector("[data-nav-group-divider]")).not.toBeInTheDocument();
    }
  });

  it("hides single-item group labels while preserving navigation semantics", () => {
    renderSideRail("/admin/dashboard");
    const nav = screen.getByRole("navigation", { name: "管理后台导航" });

    for (const groupId of ["overview", "exams", "review"]) {
      const title = nav.querySelector<HTMLElement>(`#admin-nav-group-${groupId}`);
      expect(title).toHaveClass("sr-only");
      expect(title?.closest("section")).toHaveAttribute(
        "aria-labelledby",
        `admin-nav-group-${groupId}`,
      );
    }

    for (const groupId of ["content", "system"]) {
      const title = nav.querySelector<HTMLElement>(`#admin-nav-group-${groupId}`);
      expect(title).not.toHaveClass("sr-only");
      expect(title?.closest("section")).toHaveAttribute(
        "aria-labelledby",
        `admin-nav-group-${groupId}`,
      );
    }

    expect(nav.querySelector("#admin-nav-group-exams")).toHaveTextContent("考试");
    expect(within(nav).getByRole("link", { name: "考试编排" })).toHaveAttribute(
      "href",
      "/admin/exams",
    );
    expect(within(nav).queryByRole("link", { name: "考试" })).not.toBeInTheDocument();
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
    expect(questionLink).toHaveClass("text-canvas");
    expect(questionLink).toHaveClass("hover:bg-white/10");
    expect(questionLink).toHaveClass("focus-visible:ring-canvas");
    expect(questionLink).toHaveClass("focus-visible:ring-offset-footer");
    expect(questionLink).not.toHaveClass("bg-canvas");
  });

  it("keeps dark active and inactive links visually distinct and focusable", () => {
    renderSideRail("/admin/dashboard");
    const activeLink = screen.getByRole("link", { name: "仪表盘" });
    const inactiveLink = screen.getByRole("link", { name: "题库" });

    expect(activeLink).toHaveClass("bg-canvas", "text-ink");
    expect(activeLink).toHaveClass("focus-visible:ring-canvas");
    expect(activeLink).toHaveClass("focus-visible:ring-offset-footer");
    expect(inactiveLink).toHaveClass("text-canvas", "hover:bg-white/10");
    expect(inactiveLink).toHaveClass("focus-visible:ring-canvas");
    expect(inactiveLink).toHaveClass("focus-visible:ring-offset-footer");
    expect(inactiveLink).not.toHaveClass("text-footer-soft");
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
      "考试编排",
      "报表",
      "用户账户",
      "运维",
    ]);
    expect(screen.getByRole("link", { name: "考试编排" })).toHaveAttribute("aria-current", "page");
    expect(document.getElementById("admin-nav-group-exams")?.closest("section")).toHaveAttribute(
      "data-active-group",
      "true",
    );
    const activeLink = within(nav).getByRole("link", { name: "考试编排" });
    expect(activeLink).toHaveAttribute("data-active", "true");
    expect(activeLink).toHaveClass(
      "bg-surface-card",
      "text-ink",
      "focus-visible:ring-ink",
      "focus-visible:ring-offset-canvas",
    );
  });

  it("applies the same single-item label visibility rule in the mobile sheet", async () => {
    const user = userEvent.setup();
    renderSideRail("/admin/dashboard", false);

    await user.click(screen.getByRole("button", { name: "打开菜单" }));

    const nav = await screen.findByRole("navigation", { name: "管理后台导航" });
    for (const groupId of ["overview", "exams", "review"]) {
      const title = nav.querySelector<HTMLElement>(`#admin-nav-group-${groupId}`);
      expect(title).toHaveClass("sr-only");
      expect(title?.closest("section")).toHaveAttribute(
        "aria-labelledby",
        `admin-nav-group-${groupId}`,
      );
    }

    for (const groupId of ["content", "system"]) {
      const title = nav.querySelector<HTMLElement>(`#admin-nav-group-${groupId}`);
      expect(title).not.toHaveClass("sr-only");
    }

    expect(nav.querySelector("#admin-nav-group-exams")).toHaveTextContent("考试");
    expect(within(nav).getByRole("link", { name: "考试编排" })).toHaveAttribute(
      "href",
      "/admin/exams",
    );
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

    const readGroupLayout = (nav: HTMLElement) =>
      Array.from(nav.querySelectorAll<HTMLElement>("section[data-nav-group-id]")).map((group) => ({
        id: group.dataset.navGroupId,
        visibleLabel: !group.querySelector("p")?.classList.contains("sr-only"),
        visualBreakBefore: group.dataset.visualBreakBefore,
        className: group.className,
        linkContainerClassName: group.querySelector("p + div")?.className,
        dividerPresent: Boolean(group.querySelector("[data-nav-group-divider]")),
      }));

    expect(readGroupLayout(mobileNav)).toEqual(readGroupLayout(desktopNav));
  });

  it("uses high-contrast light link colors inside the mobile sheet", async () => {
    const user = userEvent.setup();
    renderSideRail("/admin/dashboard", false);

    await user.click(screen.getByRole("button", { name: "打开菜单" }));

    const inactiveLink = await screen.findByRole("link", { name: "题库" });
    expect(inactiveLink).toHaveClass("text-body");
    expect(inactiveLink).toHaveClass("hover:bg-surface-card");
    expect(inactiveLink).toHaveClass("hover:text-ink");
    expect(inactiveLink).toHaveClass("focus-visible:ring-ink");
    expect(inactiveLink).toHaveClass("focus-visible:ring-offset-canvas");
    expect(inactiveLink).not.toHaveClass("text-muted");
    expect(inactiveLink).not.toHaveClass("hover:text-canvas");
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
