import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PASTEL_COLORS, pickPastel } from "@/lib/pastelPalette";

import { NamePlate } from "./NamePlate";

describe("NamePlate", () => {
  it("renders the name and subtitle", () => {
    render(<NamePlate name="张三" subtitle="EMP-001 · 研发部" />);

    expect(screen.getByText("张三")).toBeInTheDocument();
    expect(screen.getByText("EMP-001 · 研发部")).toBeInTheDocument();
  });

  it("omits subtitle paragraph when subtitle is empty", () => {
    render(<NamePlate name="李四" subtitle="" />);

    expect(screen.getByText("李四")).toBeInTheDocument();
    expect(screen.queryByText(/EMP-001/)).not.toBeInTheDocument();
  });

  it("uses the first uppercase character as the avatar letter", () => {
    render(<NamePlate name="alice" />);

    expect(screen.getByText("A")).toBeInTheDocument();
  });

  it("applies one of the pastel palette colors as avatar background", () => {
    render(<NamePlate name="张三" />);

    const avatar = screen.getByText("张");
    const inlineStyle = (avatar as HTMLElement).style.backgroundColor;
    const hex = PASTEL_COLORS.find((color) => {
      const red = parseInt(color.slice(1, 3), 16);
      const green = parseInt(color.slice(3, 5), 16);
      const blue = parseInt(color.slice(5, 7), 16);

      return `rgb(${red}, ${green}, ${blue})` === inlineStyle;
    });
    expect(hex).toBeDefined();
  });

  it("pickPastel is deterministic for the same seed", () => {
    expect(pickPastel("张三")).toBe(pickPastel("张三"));
  });

  it("name text uses font-display and 14px size", () => {
    render(<NamePlate name="张三" subtitle="x" />);

    const name = screen.getByText("张三");
    expect(name.className).toMatch(/font-display/);
    expect(name.className).toMatch(/text-body-sm/);
    expect(screen.getByText("x")).not.toHaveClass("italic");
  });

  it("can render from candidate input", () => {
    render(<NamePlate candidate={{ displayName: "王五", subtitle: "用户" }} />);

    expect(screen.getByText("王五")).toBeInTheDocument();
    expect(screen.getByText("用户")).toBeInTheDocument();
  });

  it("lets explicit name and subtitle override candidate input", () => {
    render(
      <NamePlate
        candidate={{ displayName: "王五", subtitle: "用户" }}
        name="赵六"
        subtitle="用户"
      />,
    );

    expect(screen.getByText("赵六")).toBeInTheDocument();
    expect(screen.getByText("用户")).toBeInTheDocument();
  });
});
