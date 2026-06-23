import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Button } from "@/components/ui/button";

import { PageActions } from "../PageActions";

describe("PageActions", () => {
  it("wraps actions without forcing one-line overflow", () => {
    render(
      <PageActions>
        <Button type="button">主要操作</Button>
        <Button type="button" variant="outline">
          次要操作
        </Button>
      </PageActions>,
    );

    const group = screen.getByRole("group", { name: "页面操作" });
    expect(group).toHaveClass("flex", "flex-wrap", "gap-2");
    expect(screen.getByRole("button", { name: "主要操作" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "次要操作" })).toBeInTheDocument();
  });
});
