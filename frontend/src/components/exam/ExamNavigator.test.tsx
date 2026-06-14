import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ExamNavigator } from "@/components/exam/ExamNavigator";
import type { QuestionNavItem } from "@/lib/questionNavigation";

function buildItems(count: number): QuestionNavItem[] {
  return Array.from({ length: count }, (_, index) => ({
    id: index + 1,
    displayIndex: index + 1,
    type: "single",
    answered: index % 2 === 0,
    targetId: "question-focus",
  }));
}

describe("ExamNavigator", () => {
  it("keeps long question lists inside an internal scroll region with ring padding", () => {
    const items = buildItems(80);

    render(<ExamNavigator items={items} activeId={1} onJump={vi.fn()} />);

    const navigator = screen.getByRole("region", { name: "题号导航" });
    expect(navigator).toHaveClass("max-h-[calc(100vh-7rem)]");

    const list = screen.getByTestId("exam-navigator-list");
    expect(list).toHaveClass("min-h-0", "overflow-y-auto", "p-1");
  });

  it("uses inset active state so selected question borders are not clipped", () => {
    const items = buildItems(3);

    render(<ExamNavigator items={items} activeId={1} onJump={vi.fn()} />);

    const activeButton = screen.getByRole("button", { name: "跳转到第 1 题" });
    expect(activeButton).toHaveClass("outline", "outline-2", "outline-offset-[-3px]");
    expect(activeButton).not.toHaveClass("ring-2");
  });
});
