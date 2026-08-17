import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Alert, AlertDescription, AlertTitle } from "../alert";

describe("Alert", () => {
  it("renders a success alert with canvas surface and status color", () => {
    render(
      <Alert variant="success">
        <AlertTitle>保存成功</AlertTitle>
        <AlertDescription>考试配置已保存。</AlertDescription>
      </Alert>,
    );

    const alert = screen.getByRole("status");
    expect(alert.className).toContain("bg-success-surface");
    expect(alert.className).toContain("border-success-border");
    expect(alert.className).toContain("text-status-success");
    expect(screen.getByText("保存成功").className).toContain("tracking-caption");
    expect(alert).toHaveAttribute("data-alert-variant", "success");
    expect(alert).toHaveAttribute("data-feedback-kind", "alert");
    expect(alert).toHaveAttribute("data-color-independent", "true");
    expect(screen.queryByRole("heading", { name: "保存成功" })).not.toBeInTheDocument();
  });

  it("renders an error alert as role alert", () => {
    render(
      <Alert variant="error">
        <AlertDescription>保存考试失败</AlertDescription>
      </Alert>,
    );

    const alert = screen.getByRole("alert");
    expect(alert.className).toContain("border-error-border");
    expect(alert.className).toContain("text-status-error");
  });

  it("supports a tone alias without changing the alert semantics", () => {
    render(<Alert tone="warning">请检查配置</Alert>);

    const alert = screen.getByRole("status");
    expect(alert).toHaveAttribute("data-alert-variant", "warning");
  });
});
