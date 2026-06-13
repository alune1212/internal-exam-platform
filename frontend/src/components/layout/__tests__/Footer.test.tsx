import { render, screen } from "@testing-library/react";

import { Footer } from "@/components/layout/Footer";

describe("Footer", () => {
  it("renders the platform wordmark text", () => {
    render(<Footer />);
    expect(screen.getByText("知试")).toBeInTheDocument();
  });

  it("renders the subtitle internal exam platform", () => {
    render(<Footer />);
    expect(screen.getByText(/internal exam platform/i)).toBeInTheDocument();
  });

  it("applies the dark footer background color", () => {
    const { container } = render(<Footer />);
    const footer = container.querySelector("footer");
    expect(footer).toHaveClass("bg-footer");
    expect(footer).toHaveClass("text-footer-soft");
  });

  it("contains a copyright line with the current year", () => {
    render(<Footer />);
    const year = new Date().getFullYear();
    expect(screen.getByText(new RegExp(`${year}`))).toBeInTheDocument();
  });
});
