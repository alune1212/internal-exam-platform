import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { getAdminExams } from "@/api/exams";
import { getAdminQuestions } from "@/api/questions";
import { getAbsentCandidates, getScoreReport } from "@/api/reports";
import { AdminDashboardPage } from "@/pages/admin/AdminDashboardPage";

vi.mock("@/api/exams", () => ({
  getAdminExams: vi.fn(),
}));

vi.mock("@/api/questions", () => ({
  getAdminQuestions: vi.fn(),
}));

vi.mock("@/api/reports", () => ({
  getAbsentCandidates: vi.fn(),
  getScoreReport: vi.fn(),
}));

function renderDashboard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <AdminDashboardPage />
    </QueryClientProvider>,
  );
}

describe("AdminDashboardPage", () => {
  it("renders semantic overview and empty-state copy", async () => {
    vi.mocked(getAdminQuestions).mockResolvedValue([]);
    vi.mocked(getAdminExams).mockResolvedValue([]);
    vi.mocked(getScoreReport).mockResolvedValue([]);
    vi.mocked(getAbsentCandidates).mockResolvedValue([]);

    renderDashboard();

    expect(screen.queryByText("DASHBOARD · 仪表盘")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "仪表盘" })).toHaveClass(
      "font-display",
      "text-display-lg",
    );
    expect(screen.getByText("关键数据已就绪。")).toHaveAttribute("role", "status");
    expect(screen.getByTestId("admin-dashboard-shell")).toHaveClass("gap-6");
    expect(screen.getByTestId("admin-dashboard-shell")).toHaveAttribute(
      "data-density",
      "workbench",
    );
    expect(
      screen
        .getByRole("heading", { level: 1, name: "仪表盘" })
        .compareDocumentPosition(screen.getByRole("heading", { level: 2, name: "最近活动" })),
    ).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    expect(await screen.findByRole("heading", { name: "暂无活动记录。" })).toBeInTheDocument();
    expect(screen.getByTestId("admin-dashboard-shell")).toHaveAttribute("data-width", "wide");
    expect(screen.getByTestId("admin-dashboard-shell")).not.toHaveClass("lg:grid-cols-4");
    expect(screen.getByTestId("admin-dashboard-shell")).toContainElement(
      screen.getByTestId("admin-dashboard-shell").querySelector("[data-dashboard-activity]")!,
    );
  });

  it("keeps activity heading typography within the design system tracking scale", () => {
    vi.mocked(getAdminQuestions).mockResolvedValue([]);
    vi.mocked(getAdminExams).mockResolvedValue([]);
    vi.mocked(getScoreReport).mockResolvedValue([]);
    vi.mocked(getAbsentCandidates).mockResolvedValue([]);

    renderDashboard();

    expect(screen.getByRole("heading", { name: "最近活动" })).not.toHaveClass("tracking-[-0.04em]");
  });

  it("does not collapse failed activity and metrics into empty or zero states", async () => {
    vi.mocked(getAdminQuestions).mockResolvedValue([]);
    vi.mocked(getAdminExams).mockResolvedValue([]);
    vi.mocked(getScoreReport).mockRejectedValue(new Error("score report unavailable"));
    vi.mocked(getAbsentCandidates).mockResolvedValue([]);

    renderDashboard();

    expect(await screen.findByRole("heading", { name: "最近活动加载失败。" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "仪表盘" })).toBeInTheDocument();
    expect(screen.getByText(/部分数据暂不可用/)).toHaveAttribute("role", "status");
    expect(screen.getByRole("alert")).toHaveTextContent("部分仪表盘指标加载失败");
    expect(screen.queryByText("暂无活动记录。")).not.toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  });

  it("shows explicit metric errors when question or exam queries fail", async () => {
    vi.mocked(getAdminQuestions).mockRejectedValue(new Error("questions unavailable"));
    vi.mocked(getAdminExams).mockRejectedValue(new Error("exams unavailable"));
    vi.mocked(getScoreReport).mockResolvedValue([]);
    vi.mocked(getAbsentCandidates).mockResolvedValue([]);

    renderDashboard();

    expect(await screen.findByText(/部分数据暂不可用/)).toHaveAttribute("role", "status");
    expect(screen.getByRole("heading", { level: 1, name: "仪表盘" })).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("部分仪表盘指标加载失败");
    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(2);
  });
});
