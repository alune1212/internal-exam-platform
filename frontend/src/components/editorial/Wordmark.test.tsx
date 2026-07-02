import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Wordmark } from "./Wordmark";

describe("Wordmark", () => {
  it("renders the brand text 知试", () => {
    render(<Wordmark />);

    expect(screen.getByText("知试")).toBeInTheDocument();
  });

  it("renders the shared brand glyph", () => {
    const { container } = render(<Wordmark data-testid="wm" />);

    const mark = container.querySelector("[data-brand-mark]");
    expect(mark).toBeInTheDocument();
    expect(mark?.querySelector("svg")).toHaveAttribute("viewBox", "0 0 64 64");
  });

  it("renders optional subtitle in italic caption", () => {
    render(<Wordmark subtitle="internal exam platform" />);

    const sub = screen.getByText("internal exam platform");
    expect(sub.className).toMatch(/italic/);
    expect(sub.className).toMatch(/text-caption|text-\[11px\]/);
  });

  it("uses dark-surface colors on the brand mark for dark variant", () => {
    render(<Wordmark data-testid="wm" variant="dark" />);

    const mark = screen.getByTestId("wm").querySelector("[data-brand-mark]") as HTMLElement;
    expect(mark.className).toMatch(/bg-canvas|text-ink/);
  });

  it("uses light-surface colors on the brand mark for light variant", () => {
    render(<Wordmark data-testid="wm" variant="light" />);

    const mark = screen.getByTestId("wm").querySelector("[data-brand-mark]") as HTMLElement;
    expect(mark.className).toMatch(/bg-ink/);
  });

  it("uses size=md brand mark by default", () => {
    const { container } = render(<Wordmark size="md" />);

    const mark = container.querySelector("[data-brand-mark]") as HTMLElement;
    expect(mark.className).toMatch(/size-9|h-9|w-9/);
  });

  it("uses size=sm circle and compact text", () => {
    render(<Wordmark data-testid="wm" size="sm" />);

    const mark = screen.getByTestId("wm").querySelector("[data-brand-mark]") as HTMLElement;
    expect(mark.className).toMatch(/size-7|h-7|w-7/);
    expect(screen.getByText("知试").className).toMatch(/text-\[18px\]/);
  });

  it("accepts tone as a variant alias", () => {
    render(<Wordmark data-testid="wm" tone="dark" />);

    const mark = screen.getByTestId("wm").querySelector("[data-brand-mark]") as HTMLElement;
    expect(mark.className).toMatch(/bg-canvas|text-ink/);
  });
});
