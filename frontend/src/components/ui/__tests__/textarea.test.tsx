import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Textarea } from "../textarea";

describe("Textarea", () => {
  it("uses dense editorial form styling", () => {
    render(<Textarea aria-label="抽题规则" />);

    const textarea = screen.getByLabelText("抽题规则");
    expect(textarea.className).toContain("rounded-md");
    expect(textarea.className).toContain("border-hairline");
    expect(textarea.className).toContain("bg-canvas-warm");
    expect(textarea.className).toContain("focus-visible:ring-ink");
  });

  it("supports invalid state styling", () => {
    render(<Textarea aria-invalid aria-label="抽题规则" />);

    const textarea = screen.getByLabelText("抽题规则");
    expect(textarea).toHaveAttribute("aria-invalid", "true");
    expect(textarea.className).toContain("aria-[invalid=true]:border-error");
  });
});
