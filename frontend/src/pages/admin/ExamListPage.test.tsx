import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const examApi = vi.hoisted(() => ({
  getAdminExams: vi.fn(),
  createAdminExam: vi.fn(),
}));

vi.mock("@/api/exams", () => examApi);

import { AdminExamListPage } from "@/pages/admin/ExamListPage";

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/admin/exams"]}>
        <Routes>
          <Route path="/admin/exams" element={<AdminExamListPage />} />
          <Route path="/admin/exams/:examId/edit" element={<div>编辑页</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("AdminExamListPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    examApi.getAdminExams.mockResolvedValue([]);
    examApi.createAdminExam.mockResolvedValue({
      id: 9,
      title: "新考试",
      description: null,
      duration_minutes: 60,
      question_rule: {},
      status: "draft",
      show_answer_after_submit: true,
    });
  });

  it("renders semantic exams copy", async () => {
    renderPage();

    expect(await screen.findByText("EXAMS · 考试")).toBeInTheDocument();
  });

  it("creates a draft exam before navigating to edit", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: /新建考试/ }));

    await waitFor(() => expect(examApi.createAdminExam).toHaveBeenCalledTimes(1));
    expect(await screen.findByText("编辑页")).toBeInTheDocument();
  });

  it("shows create errors", async () => {
    const user = userEvent.setup();
    examApi.createAdminExam.mockRejectedValue(new Error("创建失败"));
    renderPage();

    await user.click(await screen.findByRole("button", { name: /新建考试/ }));

    expect(await screen.findByRole("alert")).toHaveTextContent("创建失败");
  });

  it("shows open window and frozen pool status", async () => {
    examApi.getAdminExams.mockResolvedValue([
      {
        id: 1,
        title: "正式考试",
        description: null,
        duration_minutes: 60,
        question_rule: {},
        status: "active",
        show_answer_after_submit: true,
        available_from: "2026-06-20T01:00:00Z",
        available_until: "2026-06-20T02:00:00Z",
        availability_status: "open",
        question_pool_count: 50,
      },
    ]);

    renderPage();

    expect(await screen.findByText("正式考试")).toBeInTheDocument();
    expect(screen.getByText("可进入")).toBeInTheDocument();
    expect(screen.getByText("已冻结")).toBeInTheDocument();
    expect(screen.getByText("题池 50")).toBeInTheDocument();
  });
});
