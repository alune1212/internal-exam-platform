import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ReportToolbar } from "../ReportToolbar";

describe("ReportToolbar", () => {
  it("keeps filters, segments, notices, and actions in the shared order", () => {
    render(
      <ReportToolbar
        filters={<label htmlFor="report-filter">考试</label>}
        segments={<button type="button">全部</button>}
        notice={<p>当前筛选已更新</p>}
        actions={<button type="button">导出报表</button>}
      />,
    );

    const toolbar = screen.getByRole("group", { name: "报表筛选与操作" });
    expect(toolbar).toHaveAttribute("data-report-order", "filters-segments-notice-actions");
    expect(
      [...toolbar.querySelectorAll("[data-report-toolbar-slot]")].map((node) =>
        node.getAttribute("data-report-toolbar-slot"),
      ),
    ).toEqual(["filters", "segments", "notice", "actions"]);
  });

  it("reflows each slot without wrapping the action label", () => {
    render(<ReportToolbar actions={<button type="button">导出当前考试</button>} />);

    const toolbar = screen.getByRole("group", { name: "报表筛选与操作" });
    expect(toolbar).toHaveClass("flex-col", "lg:flex-row");
    expect(toolbar.querySelector('[data-report-toolbar-slot="actions"]')).toHaveClass("flex-wrap");
  });

  it("does not render an empty control region", () => {
    const { container } = render(<ReportToolbar />);

    expect(container).toBeEmptyDOMElement();
  });
});
