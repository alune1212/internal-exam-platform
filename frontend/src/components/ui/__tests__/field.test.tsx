import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from "../field";
import { Input } from "../input";

describe("Field", () => {
  it("groups label, control, description, and error with editorial spacing", () => {
    render(
      <FieldGroup>
        <Field data-invalid>
          <FieldLabel htmlFor="title">考试名称 · Title</FieldLabel>
          <Input id="title" aria-invalid />
          <FieldDescription>用于考生端展示。</FieldDescription>
          <FieldError>请输入考试名称</FieldError>
        </Field>
      </FieldGroup>,
    );

    expect(screen.getByText("考试名称 · Title")).toHaveAttribute("for", "title");
    expect(screen.getByText("用于考生端展示。").className).toContain("text-muted");
    expect(screen.getByText("请输入考试名称")).toHaveAttribute("role", "alert");
    expect(screen.getByText("请输入考试名称").className).toContain("text-error");
  });

  it("supports horizontal layout and disabled state", () => {
    render(
      <Field orientation="horizontal" data-disabled>
        <FieldLabel htmlFor="published">已发布</FieldLabel>
        <Input id="published" disabled />
      </Field>,
    );

    const field = screen.getByText("已发布").closest("[data-slot='field']");
    expect(field?.className).toContain("md:flex-row");
    expect(field).toHaveAttribute("data-disabled");
  });
});
