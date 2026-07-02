import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MetricCard } from "../MetricCard";

describe("MetricCard", () => {
  it("renders the italic-caps label and value", () => {
    render(<MetricCard label="QUESTION BANK · 题库" value={42} />);

    expect(screen.getByText("QUESTION BANK · 题库")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("renders an optional unit next to the value", () => {
    render(<MetricCard label="QUESTION BANK · 题库" value={42} unit="题" />);

    expect(screen.getByText("题")).toBeInTheDocument();
  });

  it("applies success tone color to the value", () => {
    render(<MetricCard label="PUBLISHED · 已发布" value={3} tone="success" />);

    const valueEl = screen.getByText("3");
    expect(valueEl.className).toContain("text-success");
  });

  it("applies warning tone color to the value", () => {
    render(<MetricCard label="NOT STARTED · 未开始" value={5} tone="warning" />);

    const valueEl = screen.getByText("5");
    expect(valueEl.className).toContain("text-warning");
  });

  it("uses default ink tone when tone prop is omitted", () => {
    render(<MetricCard label="SUBMITTED · 已交卷" value={7} />);

    const valueEl = screen.getByText("7");
    expect(valueEl.className).toContain("text-ink");
  });

  it("renders an optional caption", () => {
    render(<MetricCard label="QUESTION BANK · 题库" value={42} caption="最近更新 2 分钟前" />);

    expect(screen.getByText("最近更新 2 分钟前")).toBeInTheDocument();
  });

  it("keeps metric typography within the design system tracking scale", () => {
    render(<MetricCard label="QUESTION BANK · 题库" value={42} />);

    expect(screen.getByText("42").parentElement).not.toHaveClass("tracking-[-0.04em]");
  });
});
