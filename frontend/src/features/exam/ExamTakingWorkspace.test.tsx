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

function renderWorkspace(saveStatus: SaveStatus = "saved", liveAnnouncement?: string) {
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
      liveAnnouncement={liveAnnouncement}
    />,
  );
}

describe("ExamTakingWorkspace live persistence status", () => {
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
