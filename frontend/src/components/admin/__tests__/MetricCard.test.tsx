import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MetricCard } from "../MetricCard";

describe("MetricCard", () => {
  it("renders the italic-caps label and value", () => {
    render(<MetricCard label="QUESTIONS · 题库" value={42} />);

    expect(screen.getByText("QUESTIONS · 题库")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("renders an optional unit next to the value", () => {
    render(<MetricCard label="QUESTIONS · 题库" value={42} unit="题" />);

    expect(screen.getByText("题")).toBeInTheDocument();
  });

  it("applies success tone color to the value", () => {
    render(<MetricCard label="EXAMS LIVE · 进行中" value={3} tone="success" />);

    const valueEl = screen.getByText("3");
    expect(valueEl.className).toContain("text-success");
  });

  it("applies warning tone color to the value", () => {
    render(<MetricCard label="ABSENT · 未参加" value={5} tone="warning" />);

    const valueEl = screen.getByText("5");
    expect(valueEl.className).toContain("text-warning");
  });

  it("uses default ink tone when tone prop is omitted", () => {
    render(<MetricCard label="SUBMITTED · 已提交" value={7} />);

    const valueEl = screen.getByText("7");
    expect(valueEl.className).toContain("text-ink");
  });

  it("renders an optional caption", () => {
    render(<MetricCard label="QUESTIONS · 题库" value={42} caption="最近更新 2 分钟前" />);

    expect(screen.getByText("最近更新 2 分钟前")).toBeInTheDocument();
  });
});
