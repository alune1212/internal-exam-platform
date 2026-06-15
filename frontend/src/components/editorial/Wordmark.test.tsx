import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Wordmark } from "./Wordmark";

describe("Wordmark", () => {
  it("renders the brand text 知试", () => {
    render(<Wordmark />);

    expect(screen.getByText("知试")).toBeInTheDocument();
  });

  it("renders the brand 知 monogram inside the circle", () => {
    render(<Wordmark data-testid="wm" />);

    expect(screen.getByText("知")).toBeInTheDocument();
  });

  it("renders optional subtitle in italic caption", () => {
    render(<Wordmark subtitle="internal exam platform" />);

    const sub = screen.getByText("internal exam platform");
    expect(sub.className).toMatch(/italic/);
    expect(sub.className).toMatch(/text-caption|text-\[11px\]/);
  });

  it("uses dark colors on the circle for dark variant", () => {
    render(<Wordmark data-testid="wm" variant="dark" />);

    const circle = screen.getByTestId("wm").querySelector("span") as HTMLElement;
    expect(circle.className).toMatch(/bg-canvas|text-ink/);
  });

  it("uses light colors on the circle for light variant", () => {
    render(<Wordmark data-testid="wm" variant="light" />);

    const circle = screen.getByTestId("wm").querySelector("span") as HTMLElement;
    expect(circle.className).toMatch(/bg-ink/);
  });

  it("uses size=md circle by default", () => {
    render(<Wordmark size="md" />);

    const monogram = screen.getByText("知");
    expect(monogram.className).toMatch(/size-9|h-9|w-9/);
  });

  it("uses size=sm circle and compact text", () => {
    render(<Wordmark data-testid="wm" size="sm" />);

    const circle = screen.getByTestId("wm").querySelector("span") as HTMLElement;
    expect(circle.className).toMatch(/size-7|h-7|w-7/);
    expect(screen.getByText("知试").className).toMatch(/text-\[18px\]/);
  });

  it("accepts tone as a variant alias", () => {
    render(<Wordmark data-testid="wm" tone="dark" />);

    const circle = screen.getByTestId("wm").querySelector("span") as HTMLElement;
    expect(circle.className).toMatch(/bg-canvas|text-ink/);
  });
});
