import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PageState } from "../PageState";

describe("PageState", () => {
  it("renders loading through ContentSkeleton", () => {
    render(<PageState state="loading" />);

    expect(screen.getByRole("status")).toHaveAttribute("aria-busy", "true");
  });

  it("forwards native props to the loading status element", () => {
    render(<PageState state="loading" data-testid="loading-state" aria-label="正在加载" />);

    const loading = screen.getByRole("status");
    expect(loading).toHaveAttribute("data-testid", "loading-state");
    expect(loading).toHaveAttribute("aria-label", "正在加载");
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

  it("exposes a user-triggered retry action for recoverable errors", () => {
    const retry = vi.fn();

    render(
      <PageState state="error" title="加载失败" description="网络暂时不可用。" onRetry={retry} />,
    );

    expect(screen.getByRole("button", { name: "重试" })).toBeInTheDocument();
    expect(retry).not.toHaveBeenCalled();
    screen.getByRole("button", { name: "重试" }).click();
    expect(retry).toHaveBeenCalledTimes(1);
  });
});
