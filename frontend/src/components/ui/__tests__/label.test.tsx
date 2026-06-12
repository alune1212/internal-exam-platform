import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Label } from "../label";

describe("Label", () => {
  it("renders with text-body-sm + tracking + semibold", () => {
    render(<Label>姓名 · Name</Label>);
    const el = screen.getByText("姓名 · Name");
    expect(el.tagName).toBe("LABEL");
    expect(el.className).toMatch(/text-\[13px\]|text-body-sm/);
    expect(el.className).toContain("font-semibold");
    expect(el.className).toContain("tracking-[0.04em]");
  });
});
