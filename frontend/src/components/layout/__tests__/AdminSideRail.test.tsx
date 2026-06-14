import { render, screen } from "@testing-library/react";
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
      <AdminSideRail />
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
  });

  it("renders the dark wordmark with the admin subtitle", () => {
    renderSideRail("/admin/dashboard");
    const wordmarkLink = screen.getByRole("link", { name: /知试/ });
    expect(wordmarkLink).toBeInTheDocument();
    expect(screen.getByText(/admin/i)).toBeInTheDocument();
  });

  it("highlights the active route with white text and white background", () => {
    renderSideRail("/admin/dashboard");
    const activeLink = screen.getByRole("link", { name: "仪表盘" });
    expect(activeLink).toHaveClass("bg-white");
    expect(activeLink).toHaveClass("text-ink");
  });

  it("applies dark background to the desktop aside container", () => {
    const { container } = renderSideRail("/admin/dashboard");
    const aside = container.querySelector("aside");
    expect(aside).toHaveClass("bg-footer");
  });

  it("opens the mobile sheet when the menu button is triggered", async () => {
    const user = userEvent.setup();
    renderSideRail("/admin/dashboard", false);

    await user.click(screen.getByRole("button", { name: "打开菜单" }));

    expect(await screen.findByText("导航")).toBeInTheDocument();
  });

  it("uses high-contrast light link colors inside the mobile sheet", async () => {
    const user = userEvent.setup();
    renderSideRail("/admin/dashboard", false);

    await user.click(screen.getByRole("button", { name: "打开菜单" }));

    const inactiveLink = await screen.findByRole("link", { name: "题库" });
    expect(inactiveLink).toHaveClass("text-body");
    expect(inactiveLink).toHaveClass("hover:bg-surface-card");
    expect(inactiveLink).toHaveClass("hover:text-ink");
    expect(inactiveLink).not.toHaveClass("text-footer-soft");
    expect(inactiveLink).not.toHaveClass("hover:text-white");
  });
});
