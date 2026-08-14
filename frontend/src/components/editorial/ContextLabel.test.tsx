import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ContextLabel } from "./ContextLabel";

describe("ContextLabel", () => {
  it("renders upright context without an ordinal decoration", () => {
    render(<ContextLabel>STATE · 异常状态</ContextLabel>);

    const label = screen.getByText("STATE · 异常状态").parentElement;
    expect(label).toHaveClass("font-medium", "tracking-caption");
    expect(label).not.toHaveClass("italic");
    expect(label?.querySelector('[aria-hidden="true"]')).not.toBeInTheDocument();
  });
});
