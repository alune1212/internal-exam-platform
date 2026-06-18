import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Separator } from "../separator";

describe("Separator", () => {
  it("renders a decorative horizontal hairline by default", () => {
    render(<Separator data-testid="separator" />);

    const separator = screen.getByTestId("separator");
    expect(separator).toHaveAttribute("aria-hidden", "true");
    expect(separator.className).toContain("h-px");
    expect(separator.className).toContain("bg-hairline-soft");
  });

  it("renders a semantic separator when decorative is false", () => {
    render(<Separator decorative={false} data-testid="separator" />);

    expect(screen.getByRole("separator")).toBeInTheDocument();
  });
});
