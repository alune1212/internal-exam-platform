import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { OptionCard } from "./OptionCard";

describe("OptionCard", () => {
  it("renders option label letter and content", () => {
    render(<OptionCard label="A" content="Beijing" selected={false} onSelect={() => undefined} />);
    expect(screen.getByText("A")).toBeInTheDocument();
    expect(screen.getByText("Beijing")).toBeInTheDocument();
  });

  it("applies unselected surface (canvas + hairline) when not selected", () => {
    render(<OptionCard label="A" content="Beijing" selected={false} onSelect={() => undefined} />);
    const card = screen.getByRole("button");
    expect(card.className).toContain("bg-canvas");
    expect(card.className).toContain("border-hairline");
  });

  it("applies selected surface (surface-card + ink) when selected", () => {
    render(<OptionCard label="A" content="Beijing" selected={true} onSelect={() => undefined} />);
    const card = screen.getByRole("button");
    expect(card.className).toContain("bg-surface-card");
    expect(card.className).toContain("border-ink");
  });

  it("exposes aria-checked reflecting selected state", () => {
    render(<OptionCard label="A" content="Beijing" selected={true} onSelect={() => undefined} />);
    expect(screen.getByRole("button")).toHaveAttribute("aria-checked", "true");
  });

  it("calls onSelect with the label exactly once on click", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<OptionCard label="B" content="Shanghai" selected={false} onSelect={onSelect} />);
    await user.click(screen.getByRole("button"));
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith("B");
  });
});
