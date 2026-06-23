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

    expect(screen.getByText("OVERVIEW · 仪表盘")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "一切就绪。" })).toHaveClass(
      "font-display",
      "text-display-lg",
    );
    expect(screen.getByTestId("admin-dashboard-shell")).toHaveClass("gap-6");
    expect(await screen.findByText("STATE · 空状态")).toBeInTheDocument();
  });

  it("keeps activity heading typography within the design system tracking scale", () => {
    vi.mocked(getAdminQuestions).mockResolvedValue([]);
    vi.mocked(getAdminExams).mockResolvedValue([]);
    vi.mocked(getScoreReport).mockResolvedValue([]);
    vi.mocked(getAbsentCandidates).mockResolvedValue([]);

    renderDashboard();

    expect(screen.getByRole("heading", { name: "提交与未开始" })).not.toHaveClass(
      "tracking-[-0.04em]",
    );
  });
});
