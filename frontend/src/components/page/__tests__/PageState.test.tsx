import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PageState } from "../PageState";

describe("PageState", () => {
  it("renders loading through ContentSkeleton", () => {
    render(<PageState state="loading" />);

    expect(screen.getByRole("status")).toHaveAttribute("aria-busy", "true");
  });

  it("renders empty state through EmptyState", () => {
    render(
      <PageState
        state="empty"
        eyebrow="STATE · 空状态"
        title="暂无内容"
        description="这里还没有可显示的数据。"
      />,
    );

    expect(screen.getByText("STATE · 空状态")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "暂无内容" })).toBeInTheDocument();
    expect(screen.getByText("这里还没有可显示的数据。")).toBeInTheDocument();
  });

  it("renders error state with error tone", () => {
    render(
      <PageState
        state="error"
        eyebrow="STATE · 异常状态"
        title="加载失败"
        description="请稍后重试。"
      />,
    );

    expect(screen.getByText("STATE · 异常状态").parentElement).toHaveClass("text-error");
  });

  it("passes primary and secondary actions through", async () => {
    const action = vi.fn();
    const secondaryAction = vi.fn();

    render(
      <PageState
        state="empty"
        eyebrow="STATE · 空状态"
        title="暂无内容"
        description="这里还没有可显示的数据。"
        action={{ label: "刷新", onClick: action }}
        secondaryAction={{ label: "返回", onClick: secondaryAction }}
      />,
    );

    screen.getByRole("button", { name: "刷新" }).click();
    screen.getByRole("button", { name: "返回" }).click();

    expect(action).toHaveBeenCalledTimes(1);
    expect(secondaryAction).toHaveBeenCalledTimes(1);
  });
});
