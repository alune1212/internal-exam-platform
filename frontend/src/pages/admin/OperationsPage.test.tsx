import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getOperationsSnapshot } from "@/api/operations";
import { OperationsPage } from "@/pages/admin/OperationsPage";
import type { OperationalSignalStatus, OperationsSnapshot } from "@/types/operations";

vi.mock("@/api/operations", () => ({ getOperationsSnapshot: vi.fn() }));

function signal(status: OperationalSignalStatus, summary: string) {
  return { status, summary, checked_at: "2026-07-21T09:00:00Z", details: {} };
}

const snapshot: OperationsSnapshot = {
  checked_at: "2026-07-21T09:00:00Z",
  version: signal("current", "1.0.0 · abcdef"),
  migration: signal("current", "202607210001"),
  service_health: signal("degraded", "媒体目录只读"),
  worker_health: signal("stale", "心跳陈旧"),
  operational_lock: signal("current", "无活动写冻结"),
  disk_reserve: signal("current", "水位充足"),
  backup: signal("current", "配对备份已验证"),
  second_copy: signal("failed", "第二存储不可用"),
  restore_drill: signal("skipped", "尚未到季度演练"),
  retention: signal("current", "暂无到期考试"),
  security_scan: signal("current", "安全扫描通过"),
};

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <OperationsPage />
    </QueryClientProvider>,
  );
}

describe("OperationsPage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("keeps degraded stale skipped and failed signals distinct", async () => {
    vi.mocked(getOperationsSnapshot).mockResolvedValue(snapshot);
    renderPage();

    expect(await screen.findByText("1.0.0 · abcdef")).toBeInTheDocument();
    expect(screen.getByText("降级")).toBeInTheDocument();
    expect(screen.getByText("陈旧")).toBeInTheDocument();
    expect(screen.getByText("已跳过")).toBeInTheDocument();
    expect(screen.getByText("失败")).toBeInTheDocument();
    expect(screen.getByText("第二存储不可用")).toBeInTheDocument();
    expect(screen.getByTestId("operations-page-shell")).toHaveAttribute(
      "data-density",
      "workbench",
    );
    expect(screen.getByRole("heading", { name: "正式主机状态" })).toBeInTheDocument();
    expect(screen.queryByText("OPERATIONS · 运维")).not.toBeInTheDocument();
    expect(screen.getAllByText("当前").length).toBeGreaterThan(0);
  });

  it("shows an explicit page error when the snapshot cannot load", async () => {
    vi.mocked(getOperationsSnapshot).mockRejectedValue(new Error("offline"));
    renderPage();

    expect(await screen.findByRole("heading", { name: "运维状态加载失败。" })).toBeInTheDocument();
  });
});
