import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ContentSkeleton } from "./ContentSkeleton";

describe("ContentSkeleton", () => {
  it("renders the default skeleton bars without a loading label", () => {
    const { container } = render(<ContentSkeleton />);

    expect(screen.getByRole("status")).toHaveAttribute("aria-busy", "true");
    expect(screen.queryByText(/Loading/)).not.toBeInTheDocument();
    expect(container.querySelectorAll('[aria-hidden="true"]')).toHaveLength(3);
  });

  it("renders the loading label when showCaption is true", () => {
    render(<ContentSkeleton showCaption />);

    expect(screen.getByText(/Loading/)).toBeInTheDocument();
  });

  it("honors the rows prop", () => {
    const { container } = render(<ContentSkeleton rows={5} />);

    expect(container.querySelectorAll('[aria-hidden="true"]')).toHaveLength(5);
  });
});
