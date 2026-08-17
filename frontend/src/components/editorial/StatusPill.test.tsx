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
    expect(el.className).toMatch(/tracking-caption/);
    expect(el.className).toMatch(/rounded-sm/);
    expect(el).toHaveAttribute("role", "status");
    expect(el).toHaveAttribute("data-feedback-kind", "status-pill");
    expect(el).toHaveAttribute("data-color-independent", "true");
  });

  it("uses ink text by default", () => {
    render(<StatusPill data-testid="p">draft</StatusPill>);

    expect(screen.getByTestId("p").className).toMatch(/text-ink/);
  });

  it("success variant uses the governed light-surface status tokens", () => {
    render(
      <StatusPill data-testid="p" variant="success">
        live
      </StatusPill>,
    );

    expect(screen.getByTestId("p")).toHaveClass(
      "border-success-border",
      "bg-success-surface",
      "text-status-success",
    );
  });

  it("warning variant uses the governed light-surface status tokens", () => {
    render(
      <StatusPill data-testid="p" variant="warning">
        soon
      </StatusPill>,
    );

    expect(screen.getByTestId("p")).toHaveClass(
      "border-warning-border",
      "bg-warning-surface",
      "text-status-warning",
    );
  });

  it("error variant uses the governed light-surface status tokens", () => {
    render(
      <StatusPill data-testid="p" variant="error">
        wrong
      </StatusPill>,
    );

    expect(screen.getByTestId("p")).toHaveClass(
      "border-error-border",
      "bg-error-surface",
      "text-status-error",
    );
  });

  it("supports a tone alias while exposing the resolved semantic state", () => {
    render(
      <StatusPill data-testid="p" tone="success">
        已完成
      </StatusPill>,
    );

    expect(screen.getByTestId("p")).toHaveAttribute("data-status-variant", "success");
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
