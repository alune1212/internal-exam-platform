import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  createAdminQuestion,
  deleteAdminQuestion,
  getAdminQuestions,
  updateAdminQuestion,
} from "@/api/questions";
import { QuestionListPage } from "@/pages/admin/QuestionListPage";
import type { Question } from "@/types/question";

vi.mock("@/api/questions", () => ({
  getAdminQuestions: vi.fn(),
  createAdminQuestion: vi.fn(),
  updateAdminQuestion: vi.fn(),
  deleteAdminQuestion: vi.fn(),
}));

const question: Question = {
  id: 1,
  question_type: "single",
  stem: "安全题目",
  analysis: "解析",
  category_1: "制度",
  category_2: null,
  difficulty: "easy",
  score: 2,
  status: "active",
  source: null,
  source_no: null,
  remark: null,
  options: [
    { id: 1, label: "A", content: "正确", is_correct: true, sort_order: 1 },
    { id: 2, label: "B", content: "错误", is_correct: false, sort_order: 2 },
  ],
};

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <QuestionListPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("QuestionListPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getAdminQuestions).mockResolvedValue([question]);
    vi.mocked(createAdminQuestion).mockResolvedValue({ ...question, id: 2, stem: "新题目" });
    vi.mocked(updateAdminQuestion).mockResolvedValue({ ...question, stem: "更新题目" });
    vi.mocked(deleteAdminQuestion).mockResolvedValue({ deleted_id: 1 });
  });

  it("renders semantic library copy", async () => {
    renderPage();

    expect(await screen.findByText("LIBRARY · 题库")).toBeInTheDocument();
  });

  it("uses semantic library copy in question dialogs", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: /新增题目/ }));
    expect(screen.getAllByText("LIBRARY · 题库")).toHaveLength(2);

    await user.click(screen.getByRole("button", { name: "取消" }));
    await user.click(await screen.findByRole("button", { name: /删除/ }));
    expect(screen.getAllByText("LIBRARY · 题库")).toHaveLength(2);
  });

  it("creates a question from the dialog and shows feedback", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: /新增题目/ }));
    const dialog = screen.getByRole("dialog");
    await user.clear(within(dialog).getByLabelText("题干"));
    await user.type(within(dialog).getByLabelText("题干"), "新题目");
    await user.click(within(dialog).getByRole("button", { name: "保存题目" }));

    await waitFor(() => expect(createAdminQuestion).toHaveBeenCalledTimes(1));
    expect(await screen.findByRole("status")).toHaveTextContent("题目已保存");
  });

  it("updates an existing question", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: /编辑/ }));
    const dialog = screen.getByRole("dialog");
    await user.clear(within(dialog).getByLabelText("题干"));
    await user.type(within(dialog).getByLabelText("题干"), "更新题目");
    await user.click(within(dialog).getByRole("button", { name: "保存题目" }));

    await waitFor(() =>
      expect(updateAdminQuestion).toHaveBeenCalledWith(
        1,
        expect.objectContaining({ stem: "更新题目" }),
      ),
    );
  });

  it("confirms before deleting a question", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: /删除/ }));
    await user.click(screen.getByRole("button", { name: "确认删除" }));

    await waitFor(() => expect(deleteAdminQuestion).toHaveBeenCalledWith(1));
  });
});
