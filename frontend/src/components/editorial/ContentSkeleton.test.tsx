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

    expect(screen.getByText("加载中...")).toBeInTheDocument();
  });

  it("honors the rows prop", () => {
    const { container } = render(<ContentSkeleton rows={5} />);

    expect(container.querySelectorAll('[aria-hidden="true"]')).toHaveLength(5);
  });

  it("renders table variant rows with dense table height", () => {
    const { container } = render(<ContentSkeleton variant="table" rows={2} />);

    const skeletons = container.querySelectorAll('[aria-hidden="true"]');
    expect(skeletons).toHaveLength(2);
    expect(skeletons[0]?.className).toContain("h-12");
  });

  it("renders page variant with wider editorial blocks", () => {
    const { container } = render(<ContentSkeleton variant="page" />);

    const firstSkeleton = container.querySelector('[aria-hidden="true"]');
    expect(firstSkeleton?.className).toContain("h-8");
  });
});
