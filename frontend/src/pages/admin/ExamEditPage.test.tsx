import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getAdminExams, updateAdminExam } from "@/api/exams";
import { ExamEditPage } from "@/pages/admin/ExamEditPage";
import type { Exam } from "@/types/exam";

vi.mock("@/api/exams", () => ({
  getAdminExams: vi.fn(),
  updateAdminExam: vi.fn(),
}));

const fixedRule = {
  question_count: 50,
  total_score: 100,
  pass_score: 60,
  mode: "fixed_paper",
  type_counts: { single: 30, multiple: 10, judge: 10 },
};

const exam: Exam = {
  id: 1,
  title: "安全知识竞赛",
  description: null,
  duration_minutes: 60,
  question_rule: fixedRule,
  status: "draft",
  show_answer_after_submit: true,
  show_ranking: true,
};

function renderExamEditPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const router = createMemoryRouter(
    [{ path: "/admin/exams/:examId/edit", element: <ExamEditPage /> }],
    { initialEntries: ["/admin/exams/1/edit"] },
  );

  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("ExamEditPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getAdminExams).mockResolvedValue([exam]);
    vi.mocked(updateAdminExam).mockResolvedValue(exam);
  });

  it("loads the current exam and saves the fixed 50-question rule", async () => {
    const user = userEvent.setup();

    renderExamEditPage();

    expect(await screen.findByDisplayValue("安全知识竞赛")).toBeInTheDocument();
    expect(screen.getByDisplayValue("60")).toBeInTheDocument();
    expect(screen.getByDisplayValue(/"question_count": 50/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /保存配置/ }));

    await waitFor(() => expect(updateAdminExam).toHaveBeenCalledTimes(1));
    expect(updateAdminExam).toHaveBeenCalledWith("1", {
      title: "安全知识竞赛",
      duration_minutes: 60,
      status: "draft",
      question_rule: fixedRule,
    });
  });

  it("freezes duration and question rule after publishing", async () => {
    const user = userEvent.setup();
    vi.mocked(getAdminExams).mockResolvedValue([{ ...exam, status: "active" }]);

    renderExamEditPage();

    expect(await screen.findByDisplayValue("安全知识竞赛")).toBeInTheDocument();
    expect(screen.getByDisplayValue("60")).toBeDisabled();
    expect(screen.getByDisplayValue(/"question_count": 50/)).toBeDisabled();
    expect(screen.getByText("考试已发布，时长和抽题规则已冻结。")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /保存配置/ }));

    await waitFor(() => expect(updateAdminExam).toHaveBeenCalledTimes(1));
    expect(updateAdminExam).toHaveBeenCalledWith("1", {
      title: "安全知识竞赛",
      status: "active",
    });
  });
});
