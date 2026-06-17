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
    const card = screen.getByRole("radio");
    expect(card.className).toContain("bg-canvas");
    expect(card.className).toContain("border-hairline");
  });

  it("applies selected surface (surface-card + ink) when selected", () => {
    render(<OptionCard label="A" content="Beijing" selected={true} onSelect={() => undefined} />);
    const card = screen.getByRole("radio");
    expect(card.className).toContain("bg-surface-card");
    expect(card.className).toContain("border-ink");
  });

  it("exposes radio semantics with aria-checked reflecting selected state", () => {
    render(<OptionCard label="A" content="Beijing" selected={true} onSelect={() => undefined} />);
    expect(screen.getByRole("radio")).toHaveAttribute("aria-checked", "true");
  });

  it("can expose checkbox semantics for multiple-choice options", () => {
    render(
      <OptionCard
        label="A"
        content="Beijing"
        selected={true}
        selectionRole="checkbox"
        onSelect={() => undefined}
      />,
    );

    expect(screen.getByRole("checkbox")).toHaveAttribute("aria-checked", "true");
  });

  it("calls onSelect with the label exactly once on click", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<OptionCard label="B" content="Shanghai" selected={false} onSelect={onSelect} />);
    await user.click(screen.getByRole("radio"));
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith("B");
  });

  describe("questionType visual variants", () => {
    it("renders a circular badge for single-choice", () => {
      render(
        <OptionCard
          label="A"
          content="Beijing"
          selected={false}
          questionType="single"
          onSelect={() => undefined}
        />,
      );
      expect(screen.getByText("A")).toBeInTheDocument();
      // Single choice uses rounded-full badge
      const badge = screen.getByText("A").closest("span")!;
      expect(badge.className).toContain("rounded-full");
    });

    it("renders a square badge for multiple-choice", () => {
      render(
        <OptionCard
          label="B"
          content="Shanghai"
          selected={false}
          questionType="multiple"
          selectionRole="checkbox"
          onSelect={() => undefined}
        />,
      );
      expect(screen.getByText("B")).toBeInTheDocument();
      // Multiple choice uses rounded-sm (square) badge
      const badge = screen.getByText("B").closest("span")!;
      expect(badge.className).toContain("rounded-sm");
    });

    it("renders checkmark icon for judge option A (correct)", () => {
      const { container } = render(
        <OptionCard
          label="A"
          content="正确"
          selected={false}
          questionType="judge"
          onSelect={() => undefined}
        />,
      );
      // Judge options don't render the letter text — they render an icon
      expect(screen.queryByText("A")).not.toBeInTheDocument();
      // The SVG icon (Check) should be present
      const svg = container.querySelector("svg");
      expect(svg).toBeInTheDocument();
    });

    it("renders cross icon for judge option B (incorrect)", () => {
      const { container } = render(
        <OptionCard
          label="B"
          content="错误"
          selected={false}
          questionType="judge"
          onSelect={() => undefined}
        />,
      );
      expect(screen.queryByText("B")).not.toBeInTheDocument();
      const svg = container.querySelector("svg");
      expect(svg).toBeInTheDocument();
    });

    it("applies centered layout and rounded-lg for judge options", () => {
      render(
        <OptionCard
          label="A"
          content="正确"
          selected={false}
          questionType="judge"
          onSelect={() => undefined}
        />,
      );
      const card = screen.getByRole("radio");
      expect(card.className).toContain("justify-center");
      expect(card.className).toContain("rounded-lg");
      expect(card.className).toContain("text-center");
    });

    it("does not apply centered layout for single-choice", () => {
      render(
        <OptionCard
          label="A"
          content="Beijing"
          selected={false}
          questionType="single"
          onSelect={() => undefined}
        />,
      );
      const card = screen.getByRole("radio");
      expect(card.className).not.toContain("justify-center");
      expect(card.className).not.toContain("text-center");
    });
  });
});
