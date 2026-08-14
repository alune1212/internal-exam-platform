import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "../dialog";

describe("Dialog", () => {
  it("does not render content when closed", () => {
    render(
      <Dialog open={false}>
        <DialogContent>
          <DialogTitle>标题</DialogTitle>
        </DialogContent>
      </Dialog>,
    );
    expect(screen.queryByText("标题")).toBeNull();
  });

  it("renders content when open", async () => {
    const user = userEvent.setup();
    render(
      <Dialog>
        <DialogTrigger>打开</DialogTrigger>
        <DialogContent>
          <DialogHeader chapter="CHAPTER">
            <DialogTitle>确认</DialogTitle>
            <DialogDescription>说明文字</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <button>取消</button>
            <button>确认</button>
          </DialogFooter>
        </DialogContent>
      </Dialog>,
    );
    await user.click(screen.getByText("打开"));
    const title = await screen.findByRole("heading", { name: "确认" });
    expect(title).toBeInTheDocument();
    expect(screen.getByText("CHAPTER")).toBeInTheDocument();
  });

  it("DialogContent applies rounded-lg + surface-elev + shadow-pop", async () => {
    render(
      <Dialog defaultOpen>
        <DialogContent data-testid="dc">
          <DialogTitle>x</DialogTitle>
          <DialogDescription>描述</DialogDescription>
        </DialogContent>
      </Dialog>,
    );
    const content = await screen.findByTestId("dc");
    expect(content.className).toContain("rounded-lg");
    expect(content.className).toContain("shadow-pop");
    expect(content).toHaveClass("z-modal", "duration-normal", "ease-standard");
    expect(document.querySelector(".z-overlay")).toHaveClass(
      "z-overlay",
      "duration-normal",
      "ease-standard",
    );
  });
});
