import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatusPill } from "./StatusPill";

describe("StatusPill", () => {
  it("renders the label", () => {
    render(<StatusPill>live</StatusPill>);

    expect(screen.getByText("live")).toBeInTheDocument();
  });

  it("applies uppercase, caption size, tracking, and rounded-sm", () => {
    render(<StatusPill data-testid="p">live</StatusPill>);

    const el = screen.getByTestId("p");
    expect(el.className).toMatch(/uppercase/);
    expect(el.className).toMatch(/text-caption|text-\[11px\]/);
    expect(el.className).toMatch(/tracking-\[0\.16em\]/);
    expect(el.className).toMatch(/rounded-sm/);
  });

  it("uses ink text by default", () => {
    render(<StatusPill data-testid="p">draft</StatusPill>);

    expect(screen.getByTestId("p").className).toMatch(/text-ink/);
  });

  it("success variant uses text-success", () => {
    render(
      <StatusPill data-testid="p" variant="success">
        live
      </StatusPill>,
    );

    expect(screen.getByTestId("p").className).toMatch(/text-success/);
  });

  it("warning variant uses text-warning", () => {
    render(
      <StatusPill data-testid="p" variant="warning">
        soon
      </StatusPill>,
    );

    expect(screen.getByTestId("p").className).toMatch(/text-warning/);
  });

  it("error variant uses text-error", () => {
    render(
      <StatusPill data-testid="p" variant="error">
        wrong
      </StatusPill>,
    );

    expect(screen.getByTestId("p").className).toMatch(/text-error/);
  });

  it("forwards extra className", () => {
    render(
      <StatusPill className="ml-2" data-testid="p">
        live
      </StatusPill>,
    );

    expect(screen.getByTestId("p")).toHaveClass("ml-2");
  });
});
