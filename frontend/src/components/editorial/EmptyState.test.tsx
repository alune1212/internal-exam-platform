import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { EmptyState } from "./EmptyState";

describe("EmptyState", () => {
  it("renders chapter, title, and description", () => {
    render(<EmptyState chapter="CHAPTER 00" description="还没有任何数据。" title="暂无内容" />);

    expect(screen.getByText("CHAPTER 00")).toBeInTheDocument();
    expect(screen.getByText("暂无内容")).toBeInTheDocument();
    expect(screen.getByText("还没有任何数据。")).toBeInTheDocument();
    expect(document.querySelector('[aria-hidden="true"]')).not.toBeInTheDocument();
  });

  it("renders an action button when action is provided", () => {
    const onClick = vi.fn();

    render(
      <EmptyState
        action={{ label: "新建", onClick }}
        chapter="CHAPTER 00"
        description="还没有任何数据。"
        title="暂无内容"
      />,
    );

    expect(screen.getByRole("button", { name: "新建" })).toBeInTheDocument();
  });

  it("invokes action.onClick when the button is clicked", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();

    render(
      <EmptyState
        action={{ label: "新建", onClick }}
        chapter="CHAPTER 00"
        description="x"
        title="暂无内容"
      />,
    );

    await user.click(screen.getByRole("button", { name: "新建" }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("renders and invokes a secondary action when provided", async () => {
    const user = userEvent.setup();
    const onSecondary = vi.fn();

    render(
      <EmptyState
        action={{ label: "返回", onClick: () => undefined }}
        secondaryAction={{ label: "重试", onClick: onSecondary }}
        chapter="CHAPTER 99 · OOPS"
        description="请稍后再试。"
        title="出了点小问题。"
        tone="error"
      />,
    );

    await user.click(screen.getByRole("button", { name: "重试" }));
    expect(onSecondary).toHaveBeenCalledTimes(1);
  });

  it("omits the action button when action is not provided", () => {
    render(<EmptyState chapter="CHAPTER 00" description="x" title="暂无内容" />);

    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("error tone recolors chapter to error", () => {
    render(
      <EmptyState
        chapter="CHAPTER 99 · ERROR"
        description="请稍后重试。"
        title="出错了"
        tone="error"
      />,
    );

    expect(screen.getByText("CHAPTER 99 · ERROR").parentElement?.className).toMatch(/text-error/);
  });

  it("default tone keeps chapter muted", () => {
    render(<EmptyState chapter="CHAPTER 00" description="x" title="暂无内容" />);

    expect(screen.getByText("CHAPTER 00").parentElement?.className).toMatch(/text-muted/);
  });

  it("title uses display font", () => {
    render(<EmptyState chapter="x" description="y" title="暂无内容" />);

    const heading = screen.getByRole("heading", { level: 2, name: "暂无内容" });
    expect(heading.className).toMatch(/font-display/);
  });

  it("accepts explicit role and aria-live for page-level states", () => {
    render(
      <EmptyState
        aria-live="polite"
        chapter="CHAPTER 00"
        description="x"
        role="status"
        title="暂无内容"
      />,
    );

    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");
  });

  it("muted tone keeps a quiet neutral surface", () => {
    render(<EmptyState chapter="CHAPTER 00" description="x" title="暂无内容" tone="muted" />);

    expect(screen.getByText("CHAPTER 00").parentElement?.className).toMatch(/text-muted/);
    expect(screen.getByRole("heading", { level: 2, name: "暂无内容" }).className).toMatch(
      /text-ink/,
    );
  });

  it("allows a state without a decorative context label", () => {
    render(<EmptyState description="没有数据" title="暂无内容" />);

    expect(screen.getByRole("heading", { level: 2, name: "暂无内容" })).toBeInTheDocument();
    expect(document.querySelector("[data-context-label]")).not.toBeInTheDocument();
  });
});
