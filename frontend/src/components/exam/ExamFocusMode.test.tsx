import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ExamFocusMode } from "./ExamFocusMode";

describe("ExamFocusMode accessibility", () => {
  it("labels the option group by a focusable question heading", () => {
    render(
      <ExamFocusMode
        progress={{ current: 2, total: 4, answered: 1, currentAnswered: true }}
        remainingSeconds={1200}
        stem={{ chapterLabel: "QUESTION 02 · 单选 · 2 分", title: "题目标题" }}
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
    expect(group).toHaveAttribute("aria-labelledby", "question-heading-test");
    expect(group).toHaveAttribute("aria-describedby", "question-heading-test-state");
    expect(document.activeElement).toBe(heading);
    expect(screen.getByText("第 2 题，已作答。")).toBeInTheDocument();
  });
});
