import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { QuestionNavItem } from "@/lib/questionNavigation";

import { ExamTakingWorkspace } from "./ExamTakingWorkspace";
import type { SaveStatus } from "./useAttemptDraftQueue";

const navItems: QuestionNavItem[] = [
  {
    id: 101,
    displayIndex: 1,
    type: "single",
    answered: false,
    targetId: "exam-question-focus",
  },
];

function renderWorkspace(
  saveStatus: SaveStatus = "saved",
  liveAnnouncement?: string,
  options: { submitPending?: boolean; submitErrorVisible?: boolean } = {},
) {
  return render(
    <ExamTakingWorkspace
      activeIndex={0}
      total={1}
      answeredCount={0}
      activeQuestionAnswered={false}
      remainingSeconds={1200}
      stemChapterLabel="QUESTION 01 · 单选 · 2 分"
      stemTitle="题目标题"
      options={[{ label: "A", content: "选项 A", selected: false, disabled: false }]}
      selectionType="single"
      navItems={navItems}
      activeQuestionId={101}
      isLastQuestion
      saveStatus={saveStatus}
      hasUnsynchronizedWork={saveStatus !== "saved"}
      submitPending={options.submitPending ?? false}
      submitErrorVisible={options.submitErrorVisible ?? false}
      onSelectOption={vi.fn()}
      onPrev={vi.fn()}
      onSave={vi.fn()}
      onNext={vi.fn()}
      onJump={vi.fn()}
      onSubmit={vi.fn()}
      onRetrySave={vi.fn()}
      onResolveConflict={vi.fn()}
      liveAnnouncement={liveAnnouncement}
    />,
  );
}

describe("ExamTakingWorkspace live persistence status", () => {
  it("keeps each persistence state visible and actionable", () => {
    const expectedLabels: Array<[SaveStatus, string]> = [
      ["pending", "待保存"],
      ["saving", "正在保存"],
      ["saved", "已保存"],
      ["offline", "网络中断，答案待同步"],
      ["conflict", "答案版本冲突，请重新接管"],
      ["error", "保存失败"],
    ];

    for (const [status, label] of expectedLabels) {
      const view = renderWorkspace(status);
      expect(screen.getByTestId("exam-save-status")).toHaveTextContent(label);
      if (status === "conflict") {
        expect(screen.getByRole("button", { name: "重新登录并接管" })).toBeInTheDocument();
      }
      if (status === "offline" || status === "error") {
        expect(screen.getByRole("button", { name: "重试保存" })).toBeInTheDocument();
      }
      view.unmount();
    }

    const pendingSubmit = renderWorkspace("saved", undefined, { submitPending: true });
    const pendingSubmitButtons = screen.getAllByRole("button", { name: "正在交卷" });
    expect(pendingSubmitButtons.length).toBeGreaterThanOrEqual(2);
    pendingSubmitButtons.forEach((button) => {
      expect(button).toBeDisabled();
    });
    pendingSubmit.unmount();

    renderWorkspace("saved", undefined, { submitErrorVisible: true });
    expect(screen.getAllByText(/交卷失败，请先确认答案已同步并重试/)).not.toHaveLength(0);
    expect(screen.getByRole("alert")).toHaveTextContent(/交卷失败/);
  });

  it("announces save, offline, conflict, and automatic-submit transitions concisely", async () => {
    const view = renderWorkspace();

    view.rerender(
      <ExamTakingWorkspace
        activeIndex={0}
        total={1}
        answeredCount={0}
        remainingSeconds={1200}
        stemChapterLabel="QUESTION 01 · 单选 · 2 分"
        stemTitle="题目标题"
        options={[{ label: "A", content: "选项 A", selected: false, disabled: false }]}
        selectionType="single"
        navItems={navItems}
        activeQuestionId={101}
        isLastQuestion
        saveStatus="pending"
        hasUnsynchronizedWork
        submitPending={false}
        submitErrorVisible={false}
        onSelectOption={vi.fn()}
        onPrev={vi.fn()}
        onSave={vi.fn()}
        onNext={vi.fn()}
        onJump={vi.fn()}
        onSubmit={vi.fn()}
        onRetrySave={vi.fn()}
        onResolveConflict={vi.fn()}
      />,
    );
    view.rerender(
      <ExamTakingWorkspace
        activeIndex={0}
        total={1}
        answeredCount={0}
        remainingSeconds={1200}
        stemChapterLabel="QUESTION 01 · 单选 · 2 分"
        stemTitle="题目标题"
        options={[{ label: "A", content: "选项 A", selected: false, disabled: false }]}
        selectionType="single"
        navItems={navItems}
        activeQuestionId={101}
        isLastQuestion
        saveStatus="offline"
        hasUnsynchronizedWork
        submitPending={false}
        submitErrorVisible={false}
        onSelectOption={vi.fn()}
        onPrev={vi.fn()}
        onSave={vi.fn()}
        onNext={vi.fn()}
        onJump={vi.fn()}
        onSubmit={vi.fn()}
        onRetrySave={vi.fn()}
        onResolveConflict={vi.fn()}
      />,
    );
    await waitFor(() =>
      expect(screen.getByTestId("exam-live-announcement")).toHaveTextContent("当前离线"),
    );

    view.rerender(
      <ExamTakingWorkspace
        activeIndex={0}
        total={1}
        answeredCount={0}
        remainingSeconds={1200}
        stemChapterLabel="QUESTION 01 · 单选 · 2 分"
        stemTitle="题目标题"
        options={[{ label: "A", content: "选项 A", selected: false, disabled: false }]}
        selectionType="single"
        navItems={navItems}
        activeQuestionId={101}
        isLastQuestion
        saveStatus="conflict"
        hasUnsynchronizedWork
        submitPending={false}
        submitErrorVisible={false}
        onSelectOption={vi.fn()}
        onPrev={vi.fn()}
        onSave={vi.fn()}
        onNext={vi.fn()}
        onJump={vi.fn()}
        onSubmit={vi.fn()}
        onRetrySave={vi.fn()}
        onResolveConflict={vi.fn()}
      />,
    );
    await waitFor(() =>
      expect(screen.getByTestId("exam-live-announcement")).toHaveTextContent("答案版本冲突"),
    );

    view.rerender(
      <ExamTakingWorkspace
        activeIndex={0}
        total={1}
        answeredCount={0}
        remainingSeconds={1200}
        stemChapterLabel="QUESTION 01 · 单选 · 2 分"
        stemTitle="题目标题"
        options={[{ label: "A", content: "选项 A", selected: false, disabled: false }]}
        selectionType="single"
        navItems={navItems}
        activeQuestionId={101}
        isLastQuestion
        saveStatus="saved"
        hasUnsynchronizedWork={false}
        submitPending={false}
        submitErrorVisible={false}
        onSelectOption={vi.fn()}
        onPrev={vi.fn()}
        onSave={vi.fn()}
        onNext={vi.fn()}
        onJump={vi.fn()}
        onSubmit={vi.fn()}
        onRetrySave={vi.fn()}
        onResolveConflict={vi.fn()}
        liveAnnouncement="考试时间已到，正在自动交卷。"
      />,
    );
    expect(screen.getByTestId("exam-live-announcement")).toHaveTextContent("正在自动交卷");
  });
});
