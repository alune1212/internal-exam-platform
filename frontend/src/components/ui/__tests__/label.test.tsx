import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Label } from "../label";

describe("Label", () => {
  it("renders with the shared semantic label role", () => {
    render(<Label>姓名 · Name</Label>);
    const el = screen.getByText("姓名 · Name");
    expect(el.tagName).toBe("LABEL");
    expect(el.className).toContain("text-body-sm");
    expect(el.className).toContain("font-medium");
    expect(el.className).toContain("leading-snug");
  });
});
