import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ExamFocusMode } from "./ExamFocusMode";

describe("ExamFocusMode accessibility", () => {
  it("labels the option group by a focusable question heading", () => {
    render(
      <ExamFocusMode
        progress={{ current: 2, total: 4, answered: 1, currentAnswered: true }}
        remainingSeconds={1200}
        stem={{ chapterLabel: "第 02 题 · 单选 · 2 分", title: "题目标题" }}
        options={[{ label: "A", content: "选项 A", selected: true }]}
        onSelectOption={vi.fn()}
        questionHeadingId="question-heading-test"
        nav={{}}
      />,
    );

    const heading = screen.getByRole("heading", { name: "题目标题" });
    const group = screen.getByRole("radiogroup");
    expect(heading).toHaveAttribute("id", "question-heading-test");
    expect(heading).toHaveAttribute("tabindex", "-1");
    expect(heading).toHaveClass("min-w-0", "break-words");
    expect(group).toHaveAttribute("aria-labelledby", "question-heading-test");
    expect(group).toHaveAttribute("aria-describedby", "question-heading-test-state");
    expect(document.activeElement).toBe(heading);
    expect(screen.getByText("第 02 题 · 单选 · 2 分").parentElement).not.toHaveClass("italic");
    expect(screen.getByText("第 2 题，已作答。")).toBeInTheDocument();
  });

  it("moves focus to the new question heading when the active question changes", () => {
    const view = render(
      <ExamFocusMode
        progress={{ current: 1, total: 2, answered: 0 }}
        remainingSeconds={1200}
        stem={{ chapterLabel: "第 01 题 · 单选 · 2 分", title: "第一题" }}
        options={[{ label: "A", content: "选项 A", selected: false }]}
        onSelectOption={vi.fn()}
        questionHeadingId="question-heading-change"
        nav={{}}
      />,
    );

    view.rerender(
      <ExamFocusMode
        progress={{ current: 2, total: 2, answered: 1, currentAnswered: true }}
        remainingSeconds={900}
        stem={{ chapterLabel: "第 02 题 · 单选 · 2 分", title: "第二题" }}
        options={[{ label: "B", content: "选项 B", selected: true }]}
        onSelectOption={vi.fn()}
        questionHeadingId="question-heading-change"
        nav={{}}
      />,
    );

    expect(screen.getByRole("heading", { name: "第二题" })).toHaveFocus();
  });
});
