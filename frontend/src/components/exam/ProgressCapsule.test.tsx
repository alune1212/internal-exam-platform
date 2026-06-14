import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ProgressCapsule } from "./ProgressCapsule";

describe("ProgressCapsule", () => {
  it("renders the question index label Q 03 / 10", () => {
    render(<ProgressCapsule current={3} total={10} answered={3} />);
    expect(screen.getByText(/Q\s*03\s*\/\s*10/)).toBeInTheDocument();
  });

  it("renders the percentage derived from answered/total", () => {
    render(<ProgressCapsule current={3} total={10} answered={3} />);
    expect(screen.getByText(/30%/)).toBeInTheDocument();
  });

  it("renders 0% when nothing is answered", () => {
    render(<ProgressCapsule current={1} total={10} answered={0} />);
    expect(screen.getByText(/0%/)).toBeInTheDocument();
  });

  it("renders 100% when all answered", () => {
    render(<ProgressCapsule current={10} total={10} answered={10} />);
    expect(screen.getByText(/100%/)).toBeInTheDocument();
  });

  it("renders 0% when total is 0 without throwing", () => {
    render(<ProgressCapsule current={0} total={0} answered={0} />);
    expect(screen.getByText(/0%/)).toBeInTheDocument();
  });
});
