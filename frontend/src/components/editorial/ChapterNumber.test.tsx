import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ChapterNumber } from "./ChapterNumber";

describe("ChapterNumber", () => {
  it("renders the chapter text", () => {
    render(<ChapterNumber>CHAPTER 01 · WELCOME</ChapterNumber>);

    expect(screen.getByText("CHAPTER 01 · WELCOME")).toBeInTheDocument();
  });

  it("renders the leading horizontal-line marker as a decorative rule", () => {
    render(<ChapterNumber>CHAPTER 01 · WELCOME</ChapterNumber>);

    // Marker is now a 1px CSS rule (decorative) and an empty span with role separator.
    const container = screen.getByText("CHAPTER 01 · WELCOME").parentElement;
    expect(container?.querySelector('span[aria-hidden="true"]')).toBeInTheDocument();
    expect(screen.queryByText("———")).not.toBeInTheDocument();
  });

  it("applies upright caption size, tracking, and muted color classes", () => {
    render(<ChapterNumber data-testid="cn">CHAPTER 02 · EXAM</ChapterNumber>);

    const el = screen.getByTestId("cn");
    expect(el).not.toHaveClass("italic");
    expect(el).toHaveClass("font-medium");
    expect(el.className).toMatch(/text-caption|text-\[11px\]/);
    expect(el.className).toMatch(/tracking-\[0\.18em\]/);
    expect(el.className).toMatch(/text-muted/);
  });

  it("uppercases the chapter text", () => {
    render(<ChapterNumber data-testid="cn">chapter 03 · result</ChapterNumber>);

    expect(screen.getByTestId("cn")).toHaveClass("uppercase");
  });

  it("forwards additional className", () => {
    render(
      <ChapterNumber className="text-error" data-testid="cn">
        CHAPTER 99
      </ChapterNumber>,
    );

    expect(screen.getByTestId("cn")).toHaveClass("text-error");
  });
});
