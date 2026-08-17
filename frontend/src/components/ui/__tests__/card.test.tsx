import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "../card";

describe("Card", () => {
  it("renders root with rounded-lg + border-hairline + shadow-card", () => {
    render(<Card data-testid="c">内容</Card>);
    const el = screen.getByTestId("c");
    expect(el.className).toContain("rounded-lg");
    expect(el.className).toContain("border-hairline");
    expect(el.className).toContain("shadow-card");
    expect(el).toHaveAttribute("data-surface-owner", "card");
    expect(el).toHaveAttribute("data-surface-role", "card");
  });

  it("CardHeader applies chapter-style layout (chapter + title + description)", () => {
    render(
      <CardHeader chapter="CHAPTER 01 · WELCOME" data-testid="h">
        <CardTitle>开始考试</CardTitle>
        <CardDescription>填写姓名进入</CardDescription>
      </CardHeader>,
    );
    const header = screen.getByTestId("h");
    const chapter = screen.getByTestId("h").querySelector('[data-slot="card-context"]');
    expect(header.className).toContain("border-b");
    expect(header.className).toContain("border-hairline-soft");
    expect(chapter).toHaveAttribute("data-context-label");
    expect(chapter?.className).toMatch(/tracking-/);
    expect(screen.getByRole("heading", { level: 3, name: "开始考试" })).toHaveClass("break-words");
  });

  it("CardContent has p-5 lg:p-8 padding", () => {
    render(<CardContent data-testid="cc">x</CardContent>);
    expect(screen.getByTestId("cc").className).toContain("p-5");
    expect(screen.getByTestId("cc").className).toContain("lg:p-8");
  });

  it("exports CardFooter for footer actions", () => {
    render(<CardFooter data-testid="cf">actions</CardFooter>);
    expect(screen.getByTestId("cf")).toHaveTextContent("actions");
  });

  it("supports governed summary and overlay surfaces without a parallel Card family", () => {
    const { rerender } = render(
      <Card surface="summary" data-testid="surface">
        summary
      </Card>,
    );

    expect(screen.getByTestId("surface")).toHaveAttribute("data-surface-owner", "summary");
    expect(screen.getByTestId("surface")).toHaveAttribute("data-surface-role", "summary");

    rerender(
      <Card surface="overlay" data-testid="surface">
        overlay
      </Card>,
    );
    expect(screen.getByTestId("surface")).toHaveClass("shadow-elevate");
  });

  it("allows a card heading to follow the surrounding document order", () => {
    render(
      <CardHeader>
        <CardTitle as="h2">区域标题</CardTitle>
      </CardHeader>,
    );

    expect(screen.getByRole("heading", { level: 2, name: "区域标题" })).toBeInTheDocument();
  });
});
