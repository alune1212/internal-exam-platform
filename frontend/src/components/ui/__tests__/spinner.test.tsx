import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Spinner } from "../spinner";

describe("Spinner", () => {
  it("renders an accessible loading indicator", () => {
    render(<Spinner />);

    const spinner = screen.getByRole("status");
    expect(spinner).toHaveAttribute("aria-label", "加载中");
    expect(spinner.className).toContain("animate-spin");
    expect(spinner.className).toContain("size-4");
  });

  it("can be used as a button inline icon", () => {
    render(<Spinner data-icon="inline-start" />);

    expect(screen.getByRole("status")).toHaveAttribute("data-icon", "inline-start");
  });
});
