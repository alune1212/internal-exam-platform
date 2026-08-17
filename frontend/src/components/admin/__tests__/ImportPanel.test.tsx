import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ImportPanel } from "../ImportPanel";

const baseProps = {
  fileInputId: "question-file",
  fileLabel: "题目文件",
  selectedFile: null,
  uploadLabel: "开始导入",
  pendingLabel: "正在导入",
  pendingAriaLabel: "正在导入题目",
  isPending: false,
  onFileChange: vi.fn(),
  onUpload: vi.fn(),
};

describe("ImportPanel", () => {
  it("keeps the panel as the only containment owner for file selection", () => {
    render(<ImportPanel {...baseProps} />);

    const panel = screen.getByText("题目文件").closest('[data-surface-owner="panel"]');
    expect(panel).toBeInTheDocument();
    expect(panel?.querySelectorAll("[data-surface-owner]")).toHaveLength(0);
    expect(screen.getByRole("button", { name: "选择文件" })).toBeInTheDocument();
  });

  it("exposes the selected file and inherited pending state", async () => {
    const user = userEvent.setup();
    const onFileChange = vi.fn();
    const file = new File(["question"], "题目.xlsx", {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });

    const { rerender } = render(<ImportPanel {...baseProps} onFileChange={onFileChange} />);
    await user.upload(screen.getByLabelText("题目文件"), file);

    expect(onFileChange).toHaveBeenCalledWith(file);

    rerender(
      <ImportPanel {...baseProps} selectedFile={file} isPending onFileChange={onFileChange} />,
    );

    expect(screen.getByTestId("import-panel")).toHaveAttribute("data-import-state", "pending");
    expect(screen.getByRole("button", { name: "正在导入题目" })).toHaveAttribute(
      "aria-busy",
      "true",
    );
    expect(screen.getByRole("button", { name: "正在导入题目" })).toBeDisabled();
  });
});
