import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Button } from "@/components/ui/button";

import { PageHeader } from "../PageHeader";

describe("PageHeader", () => {
  it("renders a meaningful eyebrow above the title and description", () => {
    render(
      <PageHeader
        eyebrow="EXAMS · 考试"
        title="待完成的考试"
        description="开放中的考试会显示在这里，开始前请确认规则。"
      />,
    );

    expect(screen.getByText("EXAMS · 考试")).toBeInTheDocument();
    const heading = screen.getByRole("heading", { level: 1, name: "待完成的考试" });
    expect(heading).toHaveClass("font-display", "text-display-lg", "font-semibold", "text-ink");
    expect(screen.getByText("EXAMS · 考试").compareDocumentPosition(heading)).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING,
    );
    expect(screen.getByText("EXAMS · 考试").closest("span")?.parentElement).not.toContainHTML(
      'aria-hidden="true"',
    );
    expect(screen.getByText("开放中的考试会显示在这里，开始前请确认规则。")).toHaveClass(
      "text-body-lg",
    );
  });

  it("omits the context marker when no eyebrow is provided", () => {
    render(<PageHeader title="待完成的考试" />);

    expect(screen.getByRole("heading", { level: 1, name: "待完成的考试" })).toBeInTheDocument();
    expect(screen.queryByText("EXAMS · 考试")).not.toBeInTheDocument();
    expect(document.querySelector('[aria-hidden="true"]')).not.toBeInTheDocument();
  });

  it("omits an empty eyebrow while retaining the title", () => {
    render(<PageHeader eyebrow="  " title="题库档案" />);

    expect(screen.getByRole("heading", { level: 1, name: "题库档案" })).toBeInTheDocument();
    expect(document.querySelector('[aria-hidden="true"]')).not.toBeInTheDocument();
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
