import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Button } from "../button";
import { buttonVariants } from "../button-variants";

describe("Button", () => {
  it("renders children with default pill class", () => {
    render(<Button>提交</Button>);
    const btn = screen.getByRole("button", { name: "提交" });
    expect(btn.className).toContain("rounded-pill");
    expect(btn.className).toContain("bg-ink");
  });

  it("renders outline variant with pill + border-ink", () => {
    render(<Button variant="outline">取消</Button>);
    const btn = screen.getByRole("button", { name: "取消" });
    expect(btn.className).toContain("rounded-pill");
    expect(btn.className).toContain("border-ink");
  });

  it("renders icon size as 36x36", () => {
    render(<Button size="icon" aria-label="关闭" />);
    const btn = screen.getByRole("button", { name: "关闭" });
    expect(btn.className).toContain("size-9");
  });

  it("buttonVariants() returns expected class string", () => {
    expect(buttonVariants({ variant: "ghost" })).toContain("hover:bg-surface-card");
    expect(buttonVariants({ variant: "link" })).toContain("underline-offset-4");
    expect(buttonVariants({ size: "sm" })).toContain("h-9");
    expect(buttonVariants({ size: "lg" })).toContain("h-12");
  });

  it("renders as Slot when asChild=true", () => {
    render(
      <Button asChild>
        <a href="/x">链接</a>
      </Button>,
    );
    const link = screen.getByRole("link", { name: "链接" });
    expect(link.className).toContain("rounded-pill");
  });

  it("guards pending actions and exposes busy state", () => {
    render(<Button pending>保存</Button>);
    const button = screen.getByRole("button", { name: "保存" });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
    expect(button).toHaveAttribute("data-pending");
    expect(button).toHaveAttribute("data-state", "pending");
  });
});
