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
    expect(alert.className).toContain("bg-canvas");
    expect(alert.className).toContain("border-success");
    expect(alert.className).toContain("text-success");
    expect(screen.getByText("保存成功").className).toContain("tracking-[0.16em]");
  });

  it("renders an error alert as role alert", () => {
    render(
      <Alert variant="error">
        <AlertDescription>保存考试失败</AlertDescription>
      </Alert>,
    );

    const alert = screen.getByRole("alert");
    expect(alert.className).toContain("border-error");
    expect(alert.className).toContain("text-error");
  });
});
