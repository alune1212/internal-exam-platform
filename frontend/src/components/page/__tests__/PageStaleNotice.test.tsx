import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PageStaleNotice } from "../PageStaleNotice";

describe("PageStaleNotice", () => {
  it("discloses cached data and the last successful update time", () => {
    render(<PageStaleNotice lastSuccessfulAt="2026-08-14T01:02:03.000Z" onRetry={vi.fn()} />);

    expect(screen.getByTestId("page-stale-warning")).toHaveTextContent(
      "当前显示上一次成功的数据。",
    );
    expect(screen.getByTestId("page-stale-warning")).toHaveTextContent("上次成功更新于");
    expect(screen.getByRole("button", { name: "重试" })).toBeInTheDocument();
  });

  it("does not retry until the user asks", () => {
    const retry = vi.fn();
    render(<PageStaleNotice onRetry={retry} />);

    expect(retry).not.toHaveBeenCalled();
    screen.getByRole("button", { name: "重试" }).click();
    expect(retry).toHaveBeenCalledTimes(1);
  });
});
