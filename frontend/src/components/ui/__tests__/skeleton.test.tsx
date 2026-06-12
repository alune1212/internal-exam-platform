import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Skeleton } from "../skeleton";

describe("Skeleton", () => {
  it("renders with rounded-md + bg-hairline + animate-shimmer", () => {
    render(<Skeleton data-testid="s" />);
    const el = screen.getByTestId("s");
    expect(el.className).toContain("rounded-md");
    expect(el.className).toContain("bg-hairline");
    expect(el.className).toMatch(/animate-shimmer|animate-pulse/);
  });

  it("accepts custom className and merges", () => {
    render(<Skeleton className="h-4 w-32" data-testid="s" />);
    const el = screen.getByTestId("s");
    expect(el.className).toContain("h-4");
    expect(el.className).toContain("w-32");
  });
});
