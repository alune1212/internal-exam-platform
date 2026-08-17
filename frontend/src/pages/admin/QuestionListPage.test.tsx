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

    expect(await screen.findByText("题库")).toBeInTheDocument();
    expect(screen.queryByText("QUESTION BANK · 题库")).not.toBeInTheDocument();
  });

  it("uses semantic library copy in question dialogs", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: /新增题目/ }));
    expect(screen.getAllByText("题库")).toHaveLength(1);

    await user.click(screen.getByRole("button", { name: "取消" }));
    await user.click(await screen.findByRole("button", { name: /删除/ }));
    expect(screen.getAllByText("题库")).toHaveLength(1);
  });

  it("keeps the create form keyboard reachable and restores focus after Escape", async () => {
    const user = userEvent.setup();
    renderPage();

    const createButton = await screen.findByRole("button", { name: /新增题目/ });
    await user.click(createButton);
    const dialog = screen.getByRole("dialog");
    const keyboardTargets = [
      within(dialog).getByLabelText("题干"),
      within(dialog).getByLabelText("题型"),
      within(dialog).getByLabelText("分值"),
      within(dialog).getByLabelText("解析"),
      within(dialog).getByRole("button", { name: "取消" }),
      within(dialog).getByRole("button", { name: "保存题目" }),
    ];
    const unreached = new Set(keyboardTargets);

    for (let index = 0; index < keyboardTargets.length * 8 && unreached.size > 0; index += 1) {
      await user.tab();
      const activeElement = document.activeElement;
      if (activeElement instanceof HTMLElement) {
        unreached.delete(activeElement);
      }
    }

    expect(unreached.size).toBe(0);

    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(createButton).toHaveFocus();
  });

  it("marks the save action busy and disabled while the create mutation is pending", async () => {
    const user = userEvent.setup();
    let resolveCreate: (value: Question) => void = () => undefined;
    vi.mocked(createAdminQuestion).mockImplementation(
      () =>
        new Promise<Question>((resolve) => {
          resolveCreate = resolve;
        }),
    );

    renderPage();

    await user.click(await screen.findByRole("button", { name: /新增题目/ }));
    const dialog = screen.getByRole("dialog");
    await user.type(within(dialog).getByLabelText("题干"), "等待保存");
    await user.click(within(dialog).getByRole("button", { name: "保存题目" }));

    const saveButton = await within(dialog).findByRole("button", { name: "保存中" });
    expect(saveButton).toHaveAttribute("aria-busy", "true");
    expect(saveButton).toBeDisabled();
    expect(dialog.querySelector("[data-question-form]")).toHaveAttribute("aria-busy", "true");

    resolveCreate({ ...question, id: 2, stem: "等待保存" });
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("shows a save error without closing or discarding the form", async () => {
    const user = userEvent.setup();
    vi.mocked(createAdminQuestion).mockRejectedValueOnce(new Error("保存接口失败"));

    renderPage();

    await user.click(await screen.findByRole("button", { name: /新增题目/ }));
    const dialog = screen.getByRole("dialog");
    await user.type(within(dialog).getByLabelText("题干"), "失败后仍保留");
    await user.click(within(dialog).getByRole("button", { name: "保存题目" }));

    expect(await screen.findByRole("alert", { hidden: true })).toHaveTextContent("保存接口失败");
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(within(screen.getByRole("dialog")).getByLabelText("题干")).toHaveValue("失败后仍保留");
  });

  it("invalidates and refetches questions after a successful save", async () => {
    const user = userEvent.setup();
    const savedQuestion = { ...question, id: 2, stem: "保存后的题目" };
    vi.mocked(getAdminQuestions).mockReset();
    vi.mocked(getAdminQuestions)
      .mockResolvedValueOnce([question])
      .mockResolvedValueOnce([savedQuestion]);

    renderPage();

    await user.click(await screen.findByRole("button", { name: /新增题目/ }));
    const dialog = screen.getByRole("dialog");
    await user.type(within(dialog).getByLabelText("题干"), "保存后的题目");
    await user.click(within(dialog).getByRole("button", { name: "保存题目" }));

    await waitFor(() => expect(createAdminQuestion).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getAdminQuestions).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("保存后的题目")).toBeInTheDocument();
  });

  it.each(["single", "multiple"] as const)(
    "submits only non-empty options for %s questions",
    async (questionType) => {
      const user = userEvent.setup();
      renderPage();

      await user.click(await screen.findByRole("button", { name: /新增题目/ }));
      const dialog = screen.getByRole("dialog");
      await user.type(within(dialog).getByLabelText("题干"), "有内容选项");
      await user.selectOptions(within(dialog).getByLabelText("题型"), questionType);
      await user.type(within(dialog).getByLabelText("选项 C 内容"), "第三项");
      await user.click(within(dialog).getByRole("button", { name: "保存题目" }));

      await waitFor(() => expect(createAdminQuestion).toHaveBeenCalledTimes(1));
      expect(createAdminQuestion).toHaveBeenCalledWith(
        expect.objectContaining({ question_type: questionType, stem: "有内容选项" }),
      );
      const payload = vi.mocked(createAdminQuestion).mock.calls[0]?.[0];
      expect(payload?.options).toHaveLength(3);
      expect(payload?.options.map((option) => option.label)).toEqual(["A", "B", "C"]);
      expect(payload?.options.every((option) => option.content.trim().length > 0)).toBe(true);
    },
  );

  it("submits only A and B options for judge questions", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: /新增题目/ }));
    const dialog = screen.getByRole("dialog");
    await user.type(within(dialog).getByLabelText("题干"), "判断题");
    await user.selectOptions(within(dialog).getByLabelText("题型"), "judge");
    expect(screen.queryByLabelText("选项 C 内容")).not.toBeInTheDocument();
    await user.clear(within(dialog).getByLabelText("选项 A 内容"));
    await user.clear(within(dialog).getByLabelText("选项 B 内容"));
    await user.click(within(dialog).getByRole("button", { name: "保存题目" }));

    await waitFor(() => expect(createAdminQuestion).toHaveBeenCalledTimes(1));
    expect(createAdminQuestion).toHaveBeenCalledWith(
      expect.objectContaining({ question_type: "judge", stem: "判断题" }),
    );
    const payload = vi.mocked(createAdminQuestion).mock.calls[0]?.[0];
    expect(payload?.options).toHaveLength(2);
    expect(payload?.options.map((option) => option.label)).toEqual(["A", "B"]);
    expect(payload?.options.map((option) => option.content)).toEqual(["正确", "错误"]);
  });

  it("updates an existing question", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: /编辑/ }));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByLabelText("解析")).toHaveClass("bg-canvas-warm", "rounded-md");
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
