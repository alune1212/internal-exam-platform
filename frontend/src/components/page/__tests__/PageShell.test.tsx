import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PageShell } from "../PageShell";

describe("PageShell", () => {
  it("renders children with calm page rhythm by default", () => {
    render(<PageShell>内容</PageShell>);

    const shell = screen.getByText("内容");
    expect(shell).toHaveClass("flex", "flex-col", "gap-8");
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

  it("can opt into stagger entrance", () => {
    render(<PageShell stagger>动效页</PageShell>);

    expect(screen.getByText("动效页")).toHaveAttribute("data-stagger");
  });
});
