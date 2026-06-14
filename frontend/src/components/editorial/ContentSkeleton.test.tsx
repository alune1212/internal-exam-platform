import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ContentSkeleton } from "./ContentSkeleton";

describe("ContentSkeleton", () => {
  it("renders the default skeleton bars with a loading label", () => {
    const { container } = render(<ContentSkeleton />);

    expect(screen.getByRole("status")).toHaveAttribute("aria-busy", "true");
    expect(screen.getByText(/Loading/)).toBeInTheDocument();
    expect(container.querySelectorAll('[aria-hidden="true"]')).toHaveLength(3);
  });

  it("honors the rows prop", () => {
    const { container } = render(<ContentSkeleton rows={5} />);

    expect(container.querySelectorAll('[aria-hidden="true"]')).toHaveLength(5);
  });
});
