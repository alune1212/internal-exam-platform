import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PageSection } from "../PageSection";

describe("PageSection", () => {
  it("renders a plain section without framed card styling", () => {
    render(<PageSection variant="plain">普通区块</PageSection>);

    const section = screen.getByText("普通区块");
    expect(section).toHaveClass("flex", "flex-col");
    expect(section).toHaveAttribute("data-surface-role", "plain");
    expect(section).not.toHaveClass("shadow-card");
  });

  it("renders a card section for display content", () => {
    render(<PageSection variant="card">展示卡片</PageSection>);

    expect(screen.getByText("展示卡片")).toHaveClass(
      "rounded-lg",
      "border",
      "border-hairline",
      "bg-canvas",
      "shadow-card",
    );
    expect(screen.getByText("展示卡片")).toHaveAttribute("data-surface-owner", "card");
  });

  it("renders a panel section for dense forms", () => {
    render(<PageSection variant="panel">表单面板</PageSection>);

    expect(screen.getByText("表单面板")).toHaveClass("rounded-md", "bg-surface-card");
    expect(screen.getByText("表单面板")).toHaveAttribute("data-surface-owner", "panel");
  });

  it("renders a table section for admin data tables", () => {
    render(<PageSection variant="table">表格区块</PageSection>);

    expect(screen.getByText("表格区块")).toHaveClass("overflow-hidden", "rounded-lg");
    expect(screen.getByText("表格区块")).toHaveAttribute("data-surface-owner", "table");
  });

  it("keeps the variant as the authoritative surface owner", () => {
    render(
      <PageSection variant="panel" data-surface-owner="card">
        受控表面
      </PageSection>,
    );

    expect(screen.getByText("受控表面")).toHaveAttribute("data-surface-owner", "panel");
  });

  it.each([
    ["focus", "focus"],
    ["focus-summary", "focus-summary"],
    ["summary", "summary"],
    ["data", "data"],
    ["overlay", "overlay"],
  ] as const)("exposes the governed %s surface owner", (variant, owner) => {
    render(<PageSection variant={variant}>内容</PageSection>);

    const section = screen.getByText("内容");
    expect(section).toHaveAttribute("data-surface-role", variant);
    expect(section).toHaveAttribute("data-surface-owner", owner);
  });

  it("supports the surface alias without adding a second owner", () => {
    render(<PageSection surface="data">数据区域</PageSection>);

    const section = screen.getByText("数据区域");
    expect(section).toHaveAttribute("data-surface-owner", "data");
    expect(section).toHaveAttribute("data-surface-role", "data");
  });
});
