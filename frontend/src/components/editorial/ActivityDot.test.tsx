import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ActivityDot, StatusDot } from "./ActivityDot";

describe("ActivityDot", () => {
  it("keeps activity distinct from a status pill and exposes a non-color label", () => {
    render(<ActivityDot status="success" label="已同步" />);

    const dot = screen.getByRole("status", { name: "已同步" });
    expect(dot).toHaveAttribute("data-feedback-kind", "activity-dot");
    expect(dot).toHaveAttribute("data-status-dot", "success");
    expect(dot).toHaveAttribute("data-color-independent", "true");
    expect(dot.querySelector('[aria-hidden="true"]')).toBeInTheDocument();
  });

  it("provides a spoken meaning for a dot-only state and shares the StatusDot alias", () => {
    const { rerender } = render(<ActivityDot status="error" />);

    expect(screen.getByRole("status", { name: "异常" })).toBeInTheDocument();

    rerender(<StatusDot status="warning" />);
    expect(screen.getByRole("status", { name: "需要关注" })).toBeInTheDocument();
  });
});
