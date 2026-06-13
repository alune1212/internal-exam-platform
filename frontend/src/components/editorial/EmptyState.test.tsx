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

  it("title uses italic and display font", () => {
    render(<EmptyState chapter="x" description="y" title="暂无内容" />);

    const heading = screen.getByRole("heading", { level: 2, name: "暂无内容" });
    expect(heading.className).toMatch(/italic/);
    expect(heading.className).toMatch(/font-display/);
  });
});
