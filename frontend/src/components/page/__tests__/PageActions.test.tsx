import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Button } from "@/components/ui/button";

import { PageActions } from "../PageActions";

describe("PageActions", () => {
  it("does not render an action group for empty child values", () => {
    const { rerender } = render(<PageActions>{[]}</PageActions>);

    expect(screen.queryByRole("group", { name: "页面操作" })).not.toBeInTheDocument();

    rerender(<PageActions />);
    expect(screen.queryByRole("group", { name: "页面操作" })).not.toBeInTheDocument();

    rerender(<PageActions>{null}</PageActions>);
    expect(screen.queryByRole("group", { name: "页面操作" })).not.toBeInTheDocument();

    rerender(<PageActions>{undefined}</PageActions>);
    expect(screen.queryByRole("group", { name: "页面操作" })).not.toBeInTheDocument();

    rerender(<PageActions>{false}</PageActions>);
    expect(screen.queryByRole("group", { name: "页面操作" })).not.toBeInTheDocument();
  });

  it("wraps actions without forcing one-line overflow", () => {
    render(
      <PageActions>
        <Button type="button">主要操作</Button>
        <Button type="button" variant="outline">
          次要操作
        </Button>
      </PageActions>,
    );

    const group = screen.getByRole("group", { name: "页面操作" });
    expect(group).toHaveClass("flex", "flex-wrap", "gap-control-gap");
    expect(group).toHaveAttribute("data-action-group", "page");
    expect(group).toHaveAttribute("data-action-placement", "page");
    expect(group).toHaveAttribute("data-action-reflow", "wrap");
    expect(screen.getByRole("button", { name: "主要操作" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "次要操作" })).toBeInTheDocument();
  });

  it("supports semantic placement and predictable stacked mobile reflow", () => {
    render(
      <PageActions placement="auth" reflow="stack">
        <Button type="button">继续</Button>
        <Button type="button" variant="outline">
          返回
        </Button>
      </PageActions>,
    );

    const group = screen.getByRole("group", { name: "页面操作" });
    expect(group).toHaveAttribute("data-action-group", "auth");
    expect(group).toHaveAttribute("data-action-reflow", "stack");
    expect(group).toHaveClass("flex-col", "sm:flex-row", "w-full");
  });

  it.each(["header", "card", "form", "report", "destructive"] as const)(
    "exposes the %s placement contract",
    (placement) => {
      render(
        <PageActions placement={placement}>
          <Button type="button">操作</Button>
        </PageActions>,
      );

      expect(screen.getByRole("group", { name: "页面操作" })).toHaveAttribute(
        "data-action-group",
        placement,
      );
    },
  );
});
