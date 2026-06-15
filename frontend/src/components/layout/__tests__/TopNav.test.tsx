import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { TopNav } from "@/components/layout/TopNav";
import type { Candidate } from "@/types/candidate";

const candidate: Candidate = {
  id: 1,
  name: "张敏",
  employee_no: "E1001",
  department: "产品部",
  should_attend: true,
  status: "active",
};

function mockDesktopMediaQuery() {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string) => ({
      matches: query === "(min-width: 1024px)",
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
}) {
  mockDesktopMediaQuery();

  return render(
    <MemoryRouter initialEntries={[props.initialEntry ?? "/practice"]}>
      <TopNav candidate={props.candidate} onLogout={props.onLogout} />
    </MemoryRouter>,
  );
}

describe("TopNav", () => {
  it("renders the wordmark linking to the home route", () => {
    renderTopNav({ candidate, onLogout: () => {} });
    const wordmarkLink = screen.getByRole("link", { name: /返回考试首页/ });
    expect(wordmarkLink).toHaveAttribute("href", "/exams");
  });

  it("renders all three primary nav items", () => {
    renderTopNav({ candidate, onLogout: () => {} });
    expect(screen.getByRole("link", { name: "练习" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "考试" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "排名" })).toBeInTheDocument();
  });

  it("marks the active nav item with an underline and text-ink class", () => {
    renderTopNav({ candidate, onLogout: () => {} });
    const activeLink = screen.getByRole("link", { name: "练习" });
    expect(activeLink).toHaveClass("text-ink");
    // The first aria-hidden span is the §N marker (text-ink),
    // the second is the underline rule (bg-ink). Select the rule specifically.
    const underline = activeLink.querySelectorAll("span[aria-hidden='true']")[1];
    expect(underline).toHaveClass("bg-ink");
  });

  it("keeps ranking active without also highlighting the exam list item", () => {
    renderTopNav({ candidate, onLogout: () => {}, initialEntry: "/exams/1/ranking" });

    expect(screen.getByRole("link", { name: "排名" })).toHaveClass("text-ink");
    expect(screen.getByRole("link", { name: "考试" })).toHaveClass("text-muted");
  });

  it("renders the candidate NamePlate when a candidate is logged in", () => {
    renderTopNav({ candidate, onLogout: () => {} });
    expect(screen.getByText("张敏")).toBeInTheDocument();
    expect(screen.getByText(/E1001/)).toBeInTheDocument();
  });

  it("renders a login link when no candidate is logged in", () => {
    renderTopNav({ candidate: null, onLogout: () => {} });
    expect(screen.getByRole("link", { name: /登录/ })).toBeInTheDocument();
  });

  it("invokes onLogout when the logout icon button is clicked", async () => {
    const onLogout = vi.fn();
    const user = userEvent.setup();
    renderTopNav({ candidate, onLogout });

    await user.click(screen.getByRole("button", { name: "退出登录" }));

    expect(onLogout).toHaveBeenCalledOnce();
  });
});
