import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PageShell } from "../PageShell";

describe("PageShell", () => {
  it("renders children with calm page rhythm by default", () => {
    render(<PageShell>内容</PageShell>);

    const shell = screen.getByText("内容");
    expect(shell).toHaveClass("flex", "flex-col", "min-w-0", "gap-8", "py-page-block");
    expect(shell).toHaveClass("px-page-inline", "md:px-page-inline-lg");
    expect(shell).toHaveAttribute("data-width", "standard");
  });

  it("supports workbench density for admin pages", () => {
    render(
      <PageShell density="workbench" stagger>
        管理页
      </PageShell>,
    );

    expect(screen.getByText("管理页")).toHaveClass("gap-6");
    expect(screen.getByText("管理页")).toHaveAttribute("data-density", "workbench");
    expect(screen.getByText("管理页")).not.toHaveAttribute("data-stagger");
  });

  it("supports focus density for exam and practice pages", () => {
    render(
      <PageShell density="focus" stagger>
        作答页
      </PageShell>,
    );

    expect(screen.getByText("作答页")).toHaveClass("gap-6");
    expect(screen.getByText("作答页")).not.toHaveAttribute("data-stagger");
  });

  it.each([
    ["reading", "max-w-reading"],
    ["standard", "max-w-standard"],
    ["wide", "max-w-wide"],
    ["full", "max-w-full"],
    ["focus", "max-w-full"],
  ] as const)("assigns the %s semantic frame width", (width, maxWidth) => {
    render(<PageShell width={width}>{width}</PageShell>);

    const shell = screen.getByText(width);
    expect(shell).toHaveAttribute("data-width", width);
    expect(shell).toHaveClass("mx-auto", "w-full", maxWidth);
  });

  it("keeps the legacy default width as a standard-frame alias", () => {
    render(<PageShell width="default">兼容页</PageShell>);

    expect(screen.getByText("兼容页")).toHaveAttribute("data-width", "standard");
    expect(screen.getByText("兼容页")).toHaveClass("max-w-standard");
  });

  it("can opt into stagger entrance", () => {
    render(<PageShell stagger>动效页</PageShell>);

    expect(screen.getByText("动效页")).toHaveAttribute("data-stagger");
  });
});
