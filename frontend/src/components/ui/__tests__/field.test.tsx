import { render, screen, waitFor } from "@testing-library/react";
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

  it("associates generated descriptions and errors with its control", async () => {
    render(
      <Field invalid>
        <FieldLabel>考试名称</FieldLabel>
        <Input />
        <FieldDescription>用于考生端展示。</FieldDescription>
        <FieldError>请输入考试名称</FieldError>
      </Field>,
    );

    const input = screen.getByRole("textbox", { name: "考试名称" });
    const description = screen.getByText("用于考生端展示。");
    const error = screen.getByRole("alert");

    expect(screen.getByText("考试名称")).toHaveAttribute("for", input.id);
    expect(input).toHaveAttribute("aria-invalid", "true");
    await waitFor(() =>
      expect(input).toHaveAttribute(
        "aria-describedby",
        expect.stringContaining(description.getAttribute("id") ?? ""),
      ),
    );
    expect(input).toHaveAttribute(
      "aria-describedby",
      expect.stringContaining(error.getAttribute("id") ?? ""),
    );
    expect(screen.getByText("考试名称").closest("[data-slot='field']")).toHaveAttribute(
      "data-invalid",
    );
  });

  it("propagates pending and success state semantics to native controls", () => {
    const { rerender } = render(
      <Field state="pending">
        <FieldLabel>状态</FieldLabel>
        <Input />
      </Field>,
    );

    const pendingInput = screen.getByRole("textbox", { name: "状态" });
    expect(pendingInput).toBeDisabled();
    expect(pendingInput).toHaveAttribute("aria-busy", "true");
    expect(pendingInput).toHaveAttribute("data-state", "pending");

    rerender(
      <Field state="success">
        <FieldLabel>状态</FieldLabel>
        <Input />
      </Field>,
    );

    expect(screen.getByRole("textbox", { name: "状态" })).toHaveAttribute("data-state", "success");
    expect(screen.getByRole("textbox", { name: "状态" })).toHaveAttribute("data-success");
  });
});
