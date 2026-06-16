import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Badge } from "../badge";
import { badgeVariants } from "../badge-variants";

describe("Badge", () => {
  it("default variant uses bg-ink + text-canvas", () => {
    render(<Badge>DEFAULT</Badge>);
    const el = screen.getByText("DEFAULT");
    expect(el.className).toContain("bg-ink");
    expect(el.className).toContain("text-canvas");
    expect(el.className).toContain("rounded-sm");
    expect(el.className).toContain("uppercase");
    expect(el.className).toContain("tracking-[0.16em]");
  });

  it("outline variant uses border-ink", () => {
    render(<Badge variant="outline">DRAFT</Badge>);
    const el = screen.getByText("DRAFT");
    expect(el.className).toContain("border-ink");
  });

  it("muted variant shares the neutral surface with StatusPill (bg-canvas-warm)", () => {
    render(<Badge variant="muted">ARCHIVED</Badge>);
    const el = screen.getByText("ARCHIVED");
    expect(el.className).toContain("bg-canvas-warm");
    expect(el.className).toContain("text-ink");
  });

  it("badgeVariants() returns correct class strings", () => {
    expect(badgeVariants({ variant: "default" })).toContain("bg-ink");
    expect(badgeVariants({ variant: "outline" })).toContain("border-ink");
    expect(badgeVariants({ variant: "muted" })).toContain("bg-canvas-warm");
  });
});
