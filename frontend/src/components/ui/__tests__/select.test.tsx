import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { Field, FieldDescription, FieldLabel } from "../field";
import { Select } from "../select";

describe("Select", () => {
  it("keeps native option keyboard semantics and shared control styling", async () => {
    const user = userEvent.setup();
    render(
      <Field>
        <FieldLabel>考试状态</FieldLabel>
        <Select defaultValue="draft">
          <option value="draft">草稿</option>
          <option value="active">已发布</option>
        </Select>
        <FieldDescription>发布后会冻结题池。</FieldDescription>
      </Field>,
    );

    const select = screen.getByRole("combobox", { name: "考试状态" });
    expect(select).toHaveClass("h-11", "rounded-md", "border-hairline", "focus-visible:ring-ink");
    expect(select).toHaveAttribute("aria-describedby");

    await user.selectOptions(select, "active");
    expect(select).toHaveValue("active");
  });

  it("exposes disabled, invalid, and success states without replacing the native element", () => {
    const { rerender } = render(
      <Field state="disabled">
        <FieldLabel>状态</FieldLabel>
        <Select defaultValue="draft">
          <option value="draft">草稿</option>
        </Select>
      </Field>,
    );
    const select = screen.getByRole("combobox", { name: "状态" });
    expect(select).toBeDisabled();
    expect(select).toHaveAttribute("data-state", "disabled");

    rerender(
      <Field state="invalid">
        <FieldLabel>状态</FieldLabel>
        <Select defaultValue="draft">
          <option value="draft">草稿</option>
        </Select>
      </Field>,
    );
    expect(screen.getByRole("combobox", { name: "状态" })).toHaveAttribute("aria-invalid", "true");

    rerender(
      <Field state="success">
        <FieldLabel>状态</FieldLabel>
        <Select defaultValue="draft">
          <option value="draft">草稿</option>
        </Select>
      </Field>,
    );
    expect(screen.getByRole("combobox", { name: "状态" })).toHaveAttribute("data-success");
  });
});
