import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { CANDIDATE_NAVIGATION_ITEMS, TopNav } from "@/components/layout/TopNav";
import { breakpointQueries } from "@/lib/breakpoints";
import type { Candidate } from "@/types/candidate";

const candidate: Candidate = {
  id: 1,
  token: "candidate-token",
  token_expires_at: "2099-01-01T00:00:00.000Z",
  email: "zhangmin@example.com",
  display_name: "张敏",
  status: "active",
};

function mockMediaQuery(matches: boolean) {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string) => ({
      matches: matches && query === breakpointQueries.lg,
      media: query,
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }),
  });
}

function renderTopNav(props: {
  candidate: Candidate | null;
  onLogout: () => void;
  initialEntry?: string;
  desktop?: boolean;
}) {
  mockMediaQuery(props.desktop ?? true);

  return render(
    <MemoryRouter initialEntries={[props.initialEntry ?? "/practice"]}>
      <TopNav candidate={props.candidate} onLogout={props.onLogout} />
    </MemoryRouter>,
  );
}

describe("TopNav", () => {
  it("renders the wordmark linking to the home route", () => {
    renderTopNav({ candidate, onLogout: () => {} });
    const wordmarkLink = screen.getByRole("link", { name: /返回考试列表首页/ });
    expect(wordmarkLink).toHaveAttribute("href", "/exams");
  });

  it("preserves the ordered desktop destinations and hrefs", () => {
    renderTopNav({ candidate, onLogout: () => {} });
    const nav = screen.getByTestId("candidate-desktop-nav");
    expect(
      within(nav)
        .getAllByRole("link")
        .map((link) => link.getAttribute("href")),
    ).toEqual(["/learning", "/practice", "/exams"]);
    expect(CANDIDATE_NAVIGATION_ITEMS.map((item) => item.to)).toEqual([
      "/learning",
      "/practice",
      "/exams",
    ]);
  });

  it("exposes active state semantics without changing the destination", () => {
    renderTopNav({ candidate, onLogout: () => {} });
    const activeLink = screen.getByRole("link", { name: "练习" });
    expect(activeLink).toHaveClass("text-ink");
    expect(activeLink).toHaveClass("bg-surface-card");
    expect(activeLink).toHaveAttribute("aria-current", "page");
    expect(activeLink).toHaveAttribute("data-active", "true");
    expect(screen.getByRole("link", { name: "学习" })).toHaveAttribute("data-active", "false");
  });

  it("keeps active semantics for nested candidate routes", () => {
    const { unmount } = renderTopNav({
      candidate,
      onLogout: () => {},
      initialEntry: "/learning/42",
    });

    expect(screen.getByRole("link", { name: "学习" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "学习" })).toHaveAttribute("data-active", "true");

    unmount();
    renderTopNav({
      candidate,
      onLogout: () => {},
      initialEntry: "/practice/wrong-questions",
    });

    expect(screen.getByRole("link", { name: "练习" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "练习" })).toHaveAttribute("data-active", "true");
  });

  it("keeps the same keyboard order in the mobile sheet", async () => {
    const user = userEvent.setup();
    renderTopNav({ candidate, onLogout: () => {}, desktop: false });

    await user.click(screen.getByRole("button", { name: "打开菜单" }));

    const nav = await screen.findByTestId("candidate-mobile-nav");
    expect(
      within(nav)
        .getAllByRole("link")
        .slice(0, 3)
        .map((link) => link.getAttribute("href")),
    ).toEqual(["/learning", "/practice", "/exams"]);
    expect(within(nav).getByRole("link", { name: "打开账号资料" })).toHaveAttribute(
      "href",
      "/profile",
    );
  });

  it("keeps mobile navigation internally scrollable with safe-area padding", async () => {
    const user = userEvent.setup();
    renderTopNav({ candidate, onLogout: () => {}, desktop: false });

    await user.click(screen.getByRole("button", { name: "打开菜单" }));

    const sheet = await screen.findByTestId("candidate-mobile-navigation");
    expect(sheet).toHaveClass("max-h-[calc(100dvh-1rem)]");
    expect(sheet).toHaveClass("overflow-y-auto");
    expect(sheet).toHaveClass("overscroll-contain");
    expect(sheet).toHaveClass("pb-[calc(1.5rem+env(safe-area-inset-bottom))]");
  });

  it("renders the candidate NamePlate when a candidate is logged in", () => {
    renderTopNav({ candidate, onLogout: () => {} });
    expect(screen.getByText("张敏")).toBeInTheDocument();
    expect(screen.getByText("用户")).toBeInTheDocument();
  });

  it("renders a login link when no candidate is logged in", () => {
    renderTopNav({ candidate: null, onLogout: () => {} });
    expect(screen.getByRole("link", { name: /登录/ })).toBeInTheDocument();
  });

  it("shows a return-to-list button on the exam taking route", () => {
    renderTopNav({ candidate, onLogout: () => {}, initialEntry: "/exams/1/taking" });
    expect(screen.getByRole("link", { name: "返回考试列表" })).toBeInTheDocument();
  });

  it("hides the return-to-list button on the exam list route", () => {
    renderTopNav({ candidate, onLogout: () => {}, initialEntry: "/exams" });
    expect(screen.queryByRole("link", { name: "返回考试列表" })).not.toBeInTheDocument();
  });

  it("invokes onLogout when the logout icon button is clicked", async () => {
    const onLogout = vi.fn();
    const user = userEvent.setup();
    renderTopNav({ candidate, onLogout });

    await user.click(screen.getByRole("button", { name: "退出登录" }));

    expect(onLogout).toHaveBeenCalledOnce();
  });

  it("invokes logout from the mobile navigation after closing it", async () => {
    const onLogout = vi.fn();
    const user = userEvent.setup();
    renderTopNav({ candidate, onLogout, desktop: false });

    await user.click(screen.getByRole("button", { name: "打开菜单" }));
    await user.click(await screen.findByRole("button", { name: "退出登录" }));

    expect(onLogout).toHaveBeenCalledOnce();
  });

  it("marks the sticky header as scrolled after the page scrolls", async () => {
    Object.defineProperty(window, "scrollY", { configurable: true, value: 0 });
    const { container } = renderTopNav({ candidate, onLogout: () => {} });
    const header = container.querySelector("header");
    expect(header).toHaveAttribute("data-scrolled", "false");

    Object.defineProperty(window, "scrollY", { configurable: true, value: 24 });
    window.dispatchEvent(new Event("scroll"));

    await waitFor(() => expect(header).toHaveAttribute("data-scrolled", "true"));
  });
});
