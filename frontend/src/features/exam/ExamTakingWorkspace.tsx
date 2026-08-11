import { List, Send } from "lucide-react";
import { useState } from "react";

import { ExamFocusMode } from "@/components/exam/ExamFocusMode";
import { ExamNavigator } from "@/components/exam/ExamNavigator";
import { ProgressCapsule } from "@/components/exam/ProgressCapsule";
import { PageShell } from "@/components/page";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import type { SaveStatus } from "@/features/exam/useAttemptDraftQueue";
import { candidateActionCopy } from "@/lib/pageCopy";
import type { QuestionNavItem } from "@/lib/questionNavigation";

const SAVE_STATUS_LABEL: Record<SaveStatus, string> = {
  pending: candidateActionCopy.savePending,
  saving: candidateActionCopy.savingAnswer,
  saved: candidateActionCopy.savedAnswer,
  offline: "网络中断，答案待同步",
  conflict: "答案版本冲突，请重新接管",
  error: candidateActionCopy.saveFailed,
};

type Option = {
  label: string;
  content: string;
  selected: boolean;
  disabled: boolean;
};

export function ExamTakingWorkspace({
  activeIndex,
  total,
  answeredCount,
  remainingSeconds,
  stemChapterLabel,
  stemTitle,
  options,
  selectionType,
  navItems,
  activeQuestionId,
  isLastQuestion,
  saveStatus,
  submitPending,
  submitErrorVisible,
  onSelectOption,
  onPrev,
  onSave,
  onNext,
  onJump,
  onSubmit,
  onRetrySave,
  onResolveConflict,
}: {
  activeIndex: number;
  total: number;
  answeredCount: number;
  remainingSeconds: number;
  stemChapterLabel: string;
  stemTitle: string;
  options: Option[];
  selectionType: "single" | "multiple" | "judge";
  navItems: QuestionNavItem[];
  activeQuestionId: number;
  isLastQuestion: boolean;
  saveStatus: SaveStatus;
  submitPending: boolean;
  submitErrorVisible: boolean;
  onSelectOption: (label: string) => void;
  onPrev: () => void;
  onSave: () => void;
  onNext: () => void;
  onJump: (id: number) => void;
  onSubmit: () => void;
  onRetrySave: () => void;
  onResolveConflict: () => void;
}) {
  const [sheetOpen, setSheetOpen] = useState(false);
  const nextQuestionLabel = isLastQuestion
    ? submitPending
      ? candidateActionCopy.submittingExam
      : candidateActionCopy.submitExam
    : "下一题";
  const saveNeedsAction =
    saveStatus === "error" || saveStatus === "offline" || saveStatus === "conflict";

  return (
    <PageShell density="focus" width="full" stagger className="relative min-h-[calc(100vh-10rem)]">
      <div
        className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-hairline bg-canvas px-4 py-3 text-body-sm shadow-card"
        aria-live="polite"
      >
        <span
          className={
            saveStatus === "error" || saveStatus === "conflict"
              ? "font-medium text-error"
              : saveStatus === "saved"
                ? "font-medium text-success"
                : "font-medium text-muted"
          }
        >
          {SAVE_STATUS_LABEL[saveStatus]}
        </span>
        <div className="flex flex-wrap items-center gap-3">
          {submitErrorVisible ? (
            <span className="text-error">
              {candidateActionCopy.submitFailed}，请先确认答案已同步并重试。
            </span>
          ) : null}
          {saveNeedsAction ? (
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={saveStatus === "conflict" ? onResolveConflict : onRetrySave}
              disabled={submitPending}
            >
              {saveStatus === "conflict" ? "重新登录并接管" : candidateActionCopy.retrySave}
            </Button>
          ) : null}
        </div>
      </div>

      <div className="hidden flex-1 grid-cols-[1fr_240px] gap-8 lg:grid">
        <div id="exam-question-focus">
          <ExamFocusMode
            progress={{ current: activeIndex + 1, total, answered: answeredCount }}
            remainingSeconds={remainingSeconds}
            stem={{ chapterLabel: stemChapterLabel, title: stemTitle }}
            options={options}
            selectionType={selectionType}
            onSelectOption={onSelectOption}
            nav={{
              onPrev,
              onSave,
              onNext,
              prevDisabled: activeIndex === 0,
              nextDisabled: isLastQuestion && submitPending,
              nextLabel: nextQuestionLabel,
              saving: saveStatus === "saving",
            }}
          />
        </div>
        <aside className="self-start lg:sticky lg:top-24 lg:z-30 lg:w-60">
          <ExamNavigator
            items={navItems}
            activeId={activeQuestionId}
            desktopLayout
            onJump={(_targetId, id) => onJump(id)}
            onSubmit={onSubmit}
            submitLabel={
              submitPending ? candidateActionCopy.submittingExam : candidateActionCopy.submitExam
            }
            submitDisabled={submitPending}
          />
        </aside>
      </div>

      <div className="flex flex-1 flex-col pb-24 lg:hidden">
        <ExamFocusMode
          progress={{ current: activeIndex + 1, total, answered: answeredCount }}
          remainingSeconds={remainingSeconds}
          stem={{ chapterLabel: stemChapterLabel, title: stemTitle }}
          options={options}
          selectionType={selectionType}
          onSelectOption={onSelectOption}
          nav={{
            onPrev,
            onNext,
            prevDisabled: activeIndex === 0,
            nextDisabled: isLastQuestion && submitPending,
            nextLabel: nextQuestionLabel,
          }}
        />

        <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
          <div className="fixed inset-x-0 bottom-3 z-40 flex justify-center px-3">
            <div className="flex w-full max-w-md items-center gap-2 rounded-pill border border-footer bg-footer p-2 shadow-elevate">
              <ProgressCapsule
                current={activeIndex + 1}
                total={total}
                answered={answeredCount}
                variant="dark"
                className="flex-1"
              />
              <SheetTrigger asChild>
                <button
                  type="button"
                  className="inline-flex size-9 shrink-0 items-center justify-center rounded-pill text-canvas"
                >
                  <List aria-hidden="true" />
                  <span className="sr-only">打开题号导航</span>
                </button>
              </SheetTrigger>
            </div>
          </div>

          <SheetContent
            side="bottom"
            className="flex h-[80vh] flex-col gap-4 rounded-t-lg bg-canvas p-5"
          >
            <SheetHeader className="border-b border-hairline pb-3">
              <SheetTitle className="font-display text-display-sm">题号导航</SheetTitle>
              <SheetDescription className="sr-only">选择题号或交卷。</SheetDescription>
            </SheetHeader>
            <div className="flex-1 overflow-y-auto overscroll-contain">
              <ExamNavigator
                items={navItems}
                activeId={activeQuestionId}
                sheetLayout
                desktopLayout={false}
                onJump={(_targetId, id) => {
                  onJump(id);
                  setSheetOpen(false);
                }}
              />
            </div>
            <Button
              type="button"
              onClick={() => {
                setSheetOpen(false);
                onSubmit();
              }}
              disabled={submitPending}
              className="w-full"
            >
              <Send data-icon="inline-start" />
              {submitPending ? candidateActionCopy.submittingExam : candidateActionCopy.submitExam}
            </Button>
          </SheetContent>
        </Sheet>
      </div>

      {submitErrorVisible ? (
        <p className="sr-only" role="alert">
          {candidateActionCopy.submitFailed}，请确认考试仍在进行中。
        </p>
      ) : null}
    </PageShell>
  );
}
