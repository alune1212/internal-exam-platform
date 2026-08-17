import { ArrowLeft, List, Send } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { ExamFocusMode } from "@/components/exam/ExamFocusMode";
import { ExamNavigator } from "@/components/exam/ExamNavigator";
import { ProgressCapsule } from "@/components/exam/ProgressCapsule";
import { PageShell } from "@/components/page";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import type { SaveStatus } from "@/features/exam/useAttemptDraftQueue";
import { candidateActionCopy, candidateSaveAnnouncementCopy } from "@/lib/pageCopy";
import type { QuestionNavItem } from "@/lib/questionNavigation";

const SAVE_STATUS_LABEL: Record<SaveStatus, string> = {
  pending: candidateActionCopy.savePending,
  saving: candidateActionCopy.savingAnswer,
  saved: candidateActionCopy.savedAnswer,
  offline: candidateActionCopy.saveOffline,
  conflict: candidateActionCopy.saveConflict,
  error: candidateActionCopy.saveFailed,
};

type Option = {
  label: string;
  content: string;
  selected: boolean;
  disabled: boolean;
};

export type NavigationWarning = {
  onStay: () => void;
  onLeave: () => void;
};

export function ExamTakingWorkspace({
  activeIndex,
  total,
  answeredCount,
  activeQuestionAnswered = false,
  remainingSeconds,
  stemChapterLabel,
  stemTitle,
  options,
  selectionType,
  navItems,
  activeQuestionId,
  isLastQuestion,
  saveStatus,
  hasUnsynchronizedWork = saveStatus !== "saved",
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
  onReturnToExamList,
  navigationWarning,
  liveAnnouncement,
}: {
  activeIndex: number;
  total: number;
  answeredCount: number;
  activeQuestionAnswered?: boolean;
  remainingSeconds: number;
  stemChapterLabel: string;
  stemTitle: string;
  options: Option[];
  selectionType: "single" | "multiple" | "judge";
  navItems: QuestionNavItem[];
  activeQuestionId: number;
  isLastQuestion: boolean;
  saveStatus: SaveStatus;
  hasUnsynchronizedWork?: boolean;
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
  onReturnToExamList?: () => void;
  navigationWarning?: NavigationWarning | null;
  liveAnnouncement?: string;
}) {
  const [sheetOpen, setSheetOpen] = useState(false);
  const previousSaveStatusRef = useRef(saveStatus);
  const navigationWarningReturnFocusRef = useRef<HTMLElement | null>(null);
  const navigationWarningWasOpenRef = useRef(false);
  const [saveAnnouncement, setSaveAnnouncement] = useState("");
  const nextQuestionLabel = isLastQuestion
    ? submitPending
      ? candidateActionCopy.submittingExam
      : candidateActionCopy.submitExam
    : "下一题";
  const saveNeedsAction =
    hasUnsynchronizedWork &&
    (saveStatus === "error" || saveStatus === "offline" || saveStatus === "conflict");

  useEffect(() => {
    if (previousSaveStatusRef.current === saveStatus) return;
    previousSaveStatusRef.current = saveStatus;
    setSaveAnnouncement(candidateSaveAnnouncementCopy[saveStatus]);
  }, [saveStatus]);

  const announcement = liveAnnouncement ?? saveAnnouncement;

  return (
    <PageShell
      density="focus"
      width="full"
      data-exam-workspace
      className="relative min-h-[100dvh] min-w-0"
    >
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-hairline pb-3">
        {onReturnToExamList ? (
          <Button
            type="button"
            variant="ghost"
            onClick={onReturnToExamList}
            disabled={submitPending}
            className="min-h-touch-target"
          >
            <ArrowLeft data-icon="inline-start" />
            {candidateActionCopy.returnExamList}
          </Button>
        ) : null}
        <div className="flex min-w-0 flex-1 flex-wrap items-center justify-end gap-3">
          <span
            data-testid="exam-save-status"
            role="status"
            aria-live="polite"
            className={
              saveStatus === "error" || saveStatus === "conflict"
                ? "text-status font-status text-error"
                : saveStatus === "saved"
                  ? "text-status font-status text-success"
                  : "text-status font-status text-muted"
            }
          >
            {SAVE_STATUS_LABEL[saveStatus]}
          </span>
          {submitErrorVisible ? (
            <span className="text-body-sm text-error">
              {candidateActionCopy.submitFailed}，请先确认答案已同步并重试。
            </span>
          ) : null}
          {saveNeedsAction ? (
            <Button
              type="button"
              variant="outline"
              onClick={saveStatus === "conflict" ? onResolveConflict : onRetrySave}
              disabled={submitPending}
            >
              {saveStatus === "conflict"
                ? candidateActionCopy.resolveSaveConflict
                : candidateActionCopy.retrySave}
            </Button>
          ) : null}
        </div>
      </header>

      <div
        className="sr-only"
        data-testid="exam-live-announcement"
        role="status"
        aria-live="polite"
        aria-atomic="true"
      >
        {announcement}
      </div>

      <Dialog
        open={Boolean(navigationWarning)}
        onOpenChange={(open) => {
          if (!open) navigationWarning?.onStay();
        }}
      >
        <DialogContent
          role="alertdialog"
          aria-describedby="exam-unsaved-navigation-description"
          onOpenAutoFocus={(event) => {
            if (!navigationWarningWasOpenRef.current) {
              const activeElement = document.activeElement;
              navigationWarningReturnFocusRef.current =
                activeElement instanceof HTMLElement && activeElement !== document.body
                  ? activeElement
                  : null;
              navigationWarningWasOpenRef.current = true;
            }
            event.preventDefault();
            const stayButton = document.querySelector<HTMLButtonElement>(
              '[data-exam-safe-exit="stay"]',
            );
            stayButton?.focus();
          }}
          onCloseAutoFocus={(event) => {
            const returnFocus = navigationWarningReturnFocusRef.current;
            if (returnFocus?.isConnected) {
              event.preventDefault();
              returnFocus.focus();
            }
            navigationWarningWasOpenRef.current = false;
            navigationWarningReturnFocusRef.current = null;
          }}
        >
          <DialogHeader>
            <DialogTitle>答案尚未同步</DialogTitle>
            <DialogDescription id="exam-unsaved-navigation-description">
              {candidateActionCopy.leaveExamWarning}你可以{candidateActionCopy.stayInExam}
              继续同步，或选择
              {candidateActionCopy.confirmLeaveExam}。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              data-exam-safe-exit="stay"
              onClick={() => navigationWarning?.onStay()}
            >
              {candidateActionCopy.stayInExam}
            </Button>
            <Button type="button" onClick={() => navigationWarning?.onLeave()}>
              {candidateActionCopy.confirmLeaveExam}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <div className="hidden flex-1 grid-cols-[1fr_240px] gap-8 lg:grid">
        <div id="exam-question-focus" className="min-w-0">
          <ExamFocusMode
            progress={{
              current: activeIndex + 1,
              total,
              answered: answeredCount,
              currentAnswered: activeQuestionAnswered,
            }}
            remainingSeconds={remainingSeconds}
            stem={{ chapterLabel: stemChapterLabel, title: stemTitle }}
            options={options}
            selectionType={selectionType}
            questionHeadingId="exam-question-heading-desktop"
            onSelectOption={onSelectOption}
            nav={{
              onPrev,
              onSave,
              onNext,
              prevDisabled: activeIndex === 0,
              nextDisabled: isLastQuestion && submitPending,
              nextLabel: nextQuestionLabel,
              saving: saveStatus === "saving" || submitPending,
            }}
          />
        </div>
        <aside className="self-start lg:sticky lg:top-24 lg:z-sticky lg:w-60">
          <ExamNavigator
            items={navItems}
            activeId={activeQuestionId}
            desktopLayout
            idPrefix="exam-nav-desktop"
            onJump={(_targetId, id) => onJump(id)}
            onSubmit={onSubmit}
            submitLabel={
              submitPending ? candidateActionCopy.submittingExam : candidateActionCopy.submitExam
            }
            submitDisabled={submitPending}
          />
        </aside>
      </div>

      <div className="flex min-w-0 flex-1 flex-col pb-[calc(6rem+env(safe-area-inset-bottom))] lg:hidden">
        <ExamFocusMode
          progress={{
            current: activeIndex + 1,
            total,
            answered: answeredCount,
            currentAnswered: activeQuestionAnswered,
          }}
          remainingSeconds={remainingSeconds}
          stem={{ chapterLabel: stemChapterLabel, title: stemTitle }}
          options={options}
          selectionType={selectionType}
          questionHeadingId="exam-question-heading-mobile"
          onSelectOption={onSelectOption}
          nav={{
            onPrev,
            onSave,
            onNext,
            prevDisabled: activeIndex === 0,
            nextDisabled: isLastQuestion && submitPending,
            nextLabel: nextQuestionLabel,
            saving: saveStatus === "saving" || submitPending,
          }}
        />

        <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
          <div className="pointer-events-none fixed inset-x-0 bottom-0 z-overlay flex justify-center px-3 pb-[max(var(--space-inline),env(safe-area-inset-bottom))] pt-3 landscape:justify-end">
            <div className="pointer-events-auto flex w-full max-w-md items-center gap-2 rounded-pill border border-footer bg-footer p-2 shadow-elevate landscape:w-auto">
              <ProgressCapsule
                current={activeIndex + 1}
                total={total}
                answered={answeredCount}
                variant="dark"
                className="min-w-0 flex-1 landscape:hidden"
              />
              <SheetTrigger asChild>
                <button
                  type="button"
                  aria-label="打开题号导航"
                  className="inline-flex size-11 shrink-0 items-center justify-center rounded-pill text-canvas focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-canvas focus-visible:ring-offset-2 focus-visible:ring-offset-footer"
                >
                  <List aria-hidden="true" />
                  <span className="sr-only">打开题号导航</span>
                </button>
              </SheetTrigger>
            </div>
          </div>

          <SheetContent
            side="bottom"
            className="flex max-h-[calc(100dvh-1rem)] min-h-0 flex-col gap-4 rounded-t-lg bg-canvas p-5 pb-[calc(1.25rem+env(safe-area-inset-bottom))]"
          >
            <SheetHeader className="border-b border-hairline pb-3">
              <SheetTitle className="font-display text-subsection-title font-subsection-title">
                题号导航
              </SheetTitle>
              <SheetDescription className="sr-only">选择题号或交卷。</SheetDescription>
            </SheetHeader>
            <div className="flex-1 overflow-y-auto overscroll-contain">
              <ExamNavigator
                items={navItems}
                activeId={activeQuestionId}
                sheetLayout
                desktopLayout={false}
                idPrefix="exam-nav-mobile"
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
