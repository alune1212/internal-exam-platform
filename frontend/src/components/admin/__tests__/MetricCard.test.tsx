import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MetricCard } from "../MetricCard";

describe("MetricCard", () => {
  it("renders an upright caps label and value", () => {
    render(<MetricCard label="题库" value={42} />);

    expect(screen.getByText("题库")).toBeInTheDocument();
    expect(screen.getByText("题库")).not.toHaveClass("italic");
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(
      screen.getByText("42").closest('[data-surface-owner="metric-card"]'),
    ).toBeInTheDocument();
    expect(screen.getByText("42").closest('[data-surface-role="focus"]')).toBeInTheDocument();
  });

  it("renders an optional unit next to the value", () => {
    render(<MetricCard label="题库" value={42} unit="题" />);

    expect(screen.getByText("题")).toBeInTheDocument();
  });

  it("applies success tone color to the value", () => {
    render(<MetricCard label="已发布" value={3} tone="success" />);

    const valueEl = screen.getByText("3");
    expect(valueEl.className).toContain("text-success");
  });

  it("applies warning tone color to the value", () => {
    render(<MetricCard label="未开始" value={5} tone="warning" />);

    const valueEl = screen.getByText("5");
    expect(valueEl.className).toContain("text-warning");
  });

  it("uses default ink tone when tone prop is omitted", () => {
    render(<MetricCard label="已交卷" value={7} />);

    const valueEl = screen.getByText("7");
    expect(valueEl.className).toContain("text-ink");
  });

  it("renders an optional caption", () => {
    render(<MetricCard label="题库" value={42} caption="最近更新 2 分钟前" />);

    expect(screen.getByText("最近更新 2 分钟前")).toBeInTheDocument();
  });

  it("keeps metric typography within the design system tracking scale", () => {
    render(<MetricCard label="题库" value={42} />);

    expect(screen.getByText("42").parentElement).not.toHaveClass("tracking-[-0.04em]");
  });

  it("exposes tone semantics without adding a nested surface owner", () => {
    render(<MetricCard label="异常" value={2} tone="error" />);

    const card = screen.getByText("2").closest('[data-surface-owner="metric-card"]');
    expect(card).toHaveAttribute("data-metric-tone", "error");
    expect(card).toHaveAttribute("data-color-independent", "true");
    expect(card?.querySelector("[data-surface-owner]")).not.toBeInTheDocument();
  });
});
