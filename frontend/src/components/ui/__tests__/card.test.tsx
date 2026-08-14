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
  });

  it("CardHeader applies chapter-style layout (chapter + title + description)", () => {
    render(
      <CardHeader chapter="CHAPTER 01 · WELCOME" data-testid="h">
        <CardTitle>开始考试</CardTitle>
        <CardDescription>填写姓名进入</CardDescription>
      </CardHeader>,
    );
    const header = screen.getByTestId("h");
    const chapter = screen.getByText("CHAPTER 01 · WELCOME");
    expect(header.className).toContain("border-b");
    expect(header.className).toContain("border-hairline-soft");
    expect(chapter.className).toMatch(/uppercase|tracking-/);
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
});
