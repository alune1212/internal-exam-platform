import { render, screen, waitFor } from "@testing-library/react";
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
    const wordmarkLink = screen.getByRole("link", { name: /返回考试列表首页/ });
    expect(wordmarkLink).toHaveAttribute("href", "/exams");
  });

  it("renders the two primary nav items", () => {
    renderTopNav({ candidate, onLogout: () => {} });
    expect(screen.getByRole("link", { name: "练习" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "考试" })).toBeInTheDocument();
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

  it("keeps desktop nav markers visible across route changes", () => {
    const { rerender } = renderTopNav({
      candidate,
      onLogout: () => {},
      initialEntry: "/practice",
    });

    const practiceMarker = screen
      .getByRole("link", { name: "练习" })
      .querySelector("span[aria-hidden='true']") as HTMLElement;
    const examsMarker = screen
      .getByRole("link", { name: "考试" })
      .querySelector("span[aria-hidden='true']") as HTMLElement;
    expect(practiceMarker).not.toHaveClass("opacity-0");
    expect(examsMarker).not.toHaveClass("opacity-0");

    rerender(
      <MemoryRouter initialEntries={["/exams"]}>
        <TopNav candidate={candidate} onLogout={() => {}} />
      </MemoryRouter>,
    );

    const nextPracticeMarker = screen
      .getByRole("link", { name: "练习" })
      .querySelector("span[aria-hidden='true']") as HTMLElement;
    const nextExamsMarker = screen
      .getByRole("link", { name: "考试" })
      .querySelector("span[aria-hidden='true']") as HTMLElement;
    expect(nextPracticeMarker).not.toHaveClass("opacity-0");
    expect(nextExamsMarker).not.toHaveClass("opacity-0");
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
