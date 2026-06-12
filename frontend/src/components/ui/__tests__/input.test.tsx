import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Input } from "../input";

describe("Input", () => {
  it("renders with rounded-md + h-11 + bg-canvas", () => {
    render(<Input placeholder="姓名" />);
    const el = screen.getByPlaceholderText("姓名");
    expect(el.className).toContain("rounded-md");
    expect(el.className).toContain("h-11");
    expect(el.className).toContain("bg-canvas");
    expect(el.className).toContain("border-hairline");
  });

  it("focus styling uses ring-ink", () => {
    render(<Input placeholder="x" />);
    const el = screen.getByPlaceholderText("x");
    expect(el.className).toContain("focus-visible:ring-ink");
  });
});
