import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Timer } from "./Timer";

describe("Timer", () => {
  it("renders the REMAINING caption label", () => {
    render(<Timer remainingSeconds={1200} />);
    expect(screen.getByText(/REMAINING/i)).toBeInTheDocument();
  });

  it("renders padded mm:ss for > 5 minutes (green/no-pulse state)", () => {
    render(<Timer remainingSeconds={1500} />);
    const time = screen.getByText("25:00");
    expect(time).toBeInTheDocument();
    expect(time.className).not.toContain("text-error");
  });

  it("renders 00:00 when remaining is zero", () => {
    render(<Timer remainingSeconds={0} />);
    expect(screen.getByText("00:00")).toBeInTheDocument();
  });

  it("switches to text-error colour when remaining is <= 5 minutes", () => {
    render(<Timer remainingSeconds={299} />);
    const time = screen.getByText("04:59");
    expect(time.className).toContain("text-error");
  });

  it("applies the animate-pulse class when remaining is exactly 5 minutes", () => {
    render(<Timer remainingSeconds={300} />);
    const time = screen.getByText("05:00");
    const wrapper = time.parentElement;
    expect(wrapper?.className).toContain("motion-safe:animate-pulse");
    expect(wrapper?.className).toContain("duration-pulse");
    expect(wrapper).not.toHaveAttribute("style");
  });

  it("does not apply animate-pulse when remaining is > 5 minutes", () => {
    render(<Timer remainingSeconds={301} />);
    const time = screen.getByText("05:01");
    const wrapper = time.parentElement;
    expect(wrapper?.className).not.toContain("animate-pulse");
  });

  it("does not pollute screen readers with per-second ticks", () => {
    render(<Timer remainingSeconds={1200} />);
    const time = screen.getByText("20:00");
    // The clock face itself is no longer an aria-live region; a separate
    // sr-only region handles threshold announcements only.
    expect(time).not.toHaveAttribute("aria-live");
    expect(screen.getByRole("status")).toBeInTheDocument();
  });
});
