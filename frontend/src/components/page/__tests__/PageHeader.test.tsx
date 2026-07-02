import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Button } from "@/components/ui/button";

import { PageHeader } from "../PageHeader";

describe("PageHeader", () => {
  it("renders the shared eyebrow, title, and description", () => {
    render(
      <PageHeader
        eyebrow="EXAMS · 考试"
        title="待完成的考试"
        description="开放中的考试会显示在这里，开始前请确认规则。"
      />,
    );

    expect(screen.getByText("EXAMS · 考试")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "待完成的考试" })).toHaveClass(
      "font-display",
      "text-display-lg",
      "font-semibold",
      "text-ink",
    );
    expect(screen.getByText("开放中的考试会显示在这里，开始前请确认规则。")).toHaveClass(
      "text-body-lg",
    );
  });

  it("places actions in a responsive action region", () => {
    render(
      <PageHeader
        eyebrow="QUESTION BANK · 题库"
        title="题库档案"
        actions={<Button type="button">新增题目</Button>}
      />,
    );

    expect(screen.getByRole("button", { name: "新增题目" })).toBeInTheDocument();
  });
});
