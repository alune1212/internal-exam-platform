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
    expect(screen.getByText("考试名称 · Title").closest("[data-slot='field']")).toHaveClass(
      "min-w-0",
    );
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

  it("assigns stable ids to description and error so callers can wire aria-describedby explicitly", () => {
    render(
      <Field invalid>
        <FieldLabel htmlFor="title">考试名称</FieldLabel>
        <Input id="title" aria-invalid />
        <FieldDescription>用于考生端展示。</FieldDescription>
        <FieldError>请输入考试名称</FieldError>
      </Field>,
    );

    const description = screen.getByText("用于考生端展示。");
    const error = screen.getByRole("alert");

    expect(description).toHaveAttribute("id");
    expect(error).toHaveAttribute("id");
    expect(description.getAttribute("id")).not.toEqual(error.getAttribute("id"));
  });

  it("propagates pending, success, and invalid state to the field wrapper data-state", () => {
    const { rerender } = render(
      <Field state="pending">
        <FieldLabel htmlFor="status">状态</FieldLabel>
        <Input id="status" />
      </Field>,
    );

    expect(screen.getByText("状态").closest("[data-slot='field']")).toHaveAttribute(
      "data-state",
      "pending",
    );

    rerender(
      <Field state="success">
        <FieldLabel htmlFor="status">状态</FieldLabel>
        <Input id="status" />
      </Field>,
    );

    expect(screen.getByText("状态").closest("[data-slot='field']")).toHaveAttribute(
      "data-state",
      "success",
    );
    expect(screen.getByText("状态").closest("[data-slot='field']")).toHaveAttribute("data-success");
  });
});
