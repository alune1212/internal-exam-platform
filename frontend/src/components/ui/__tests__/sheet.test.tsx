import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "../sheet";

describe("Sheet", () => {
  it("renders content when opened", async () => {
    const user = userEvent.setup();
    render(
      <Sheet>
        <SheetTrigger>唤起</SheetTrigger>
        <SheetContent side="bottom">
          <SheetHeader chapter="CHAPTER">
            <SheetTitle>导航</SheetTitle>
            <SheetDescription>移动端导航</SheetDescription>
          </SheetHeader>
        </SheetContent>
      </Sheet>,
    );
    await user.click(screen.getByText("唤起"));
    expect(await screen.findByText("导航")).toBeInTheDocument();
    expect(screen.getByText("CHAPTER")).toBeInTheDocument();
  });

  it("SheetContent side=bottom has slide-in-from-bottom class", async () => {
    const user = userEvent.setup();
    render(
      <Sheet>
        <SheetTrigger>唤起</SheetTrigger>
        <SheetContent side="bottom" data-testid="sc">
          <SheetTitle>x</SheetTitle>
          <SheetDescription>描述</SheetDescription>
        </SheetContent>
      </Sheet>,
    );
    await user.click(screen.getByText("唤起"));
    const content = await screen.findByTestId("sc");
    expect(content.className).toContain("slide-in-from-bottom");
  });

  it("SheetContent side=right has slide-in-from-right class", async () => {
    const user = userEvent.setup();
    render(
      <Sheet>
        <SheetTrigger>唤起</SheetTrigger>
        <SheetContent side="right" data-testid="sc">
          <SheetTitle>x</SheetTitle>
          <SheetDescription>描述</SheetDescription>
        </SheetContent>
      </Sheet>,
    );
    await user.click(screen.getByText("唤起"));
    const content = await screen.findByTestId("sc");
    expect(content.className).toContain("slide-in-from-right");
  });
});
