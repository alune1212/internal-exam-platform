import { ChevronLeft, ChevronRight, Save } from "lucide-react";
import { useEffect, useRef, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { candidateActionCopy } from "@/lib/pageCopy";
import { cn } from "@/lib/utils";

import { ChapterNumber } from "../editorial/ChapterNumber";

import { OptionCard } from "./OptionCard";
import { ProgressCapsule } from "./ProgressCapsule";
import { Timer } from "./Timer";

export type ExamFocusModeProps = {
  progress: {
    current: number;
    total: number;
    answered: number;
    currentAnswered?: boolean;
  };
  remainingSeconds: number;
  stem: {
    chapterLabel: string;
    title: string;
  };
  options: Array<{
    label: string;
    content: string;
    selected: boolean;
    disabled?: boolean;
  }>;
  onSelectOption: (label: string) => void;
  selectionType?: "single" | "multiple" | "judge";
  nav: {
    onPrev?: () => void;
    onSave?: () => void;
    onNext?: () => void;
    prevDisabled?: boolean;
    nextDisabled?: boolean;
    saveLabel?: string;
    nextLabel?: string;
    saving?: boolean;
  };
  className?: string;
  children?: ReactNode;
  questionHeadingId?: string;
};

export function ExamFocusMode({
  progress,
  remainingSeconds,
  stem,
  options,
  onSelectOption,
  selectionType = "single",
  nav,
  className,
  children,
  questionHeadingId = "exam-question-heading",
}: ExamFocusModeProps) {
  const headingRef = useRef<HTMLHeadingElement>(null);
  const currentQuestion = progress.current;

  useEffect(() => {
    headingRef.current?.focus();
  }, [currentQuestion, stem.chapterLabel, stem.title]);

  const answeredLabel =
    (progress.currentAnswered ?? options.some((option) => option.selected)) ? "已作答" : "未作答";

  return (
    <div className={cn("flex min-w-0 flex-col gap-6", className)} data-exam-question-workspace>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <ProgressCapsule
          current={progress.current}
          total={progress.total}
          answered={progress.answered}
        />
        <Timer remainingSeconds={remainingSeconds} />
      </div>

      <article className="flex min-w-0 flex-col gap-6 rounded-lg border border-hairline bg-surface-card p-4 shadow-card sm:p-6 md:p-8">
        <header className="flex min-w-0 flex-col gap-2 border-b border-hairline pb-4">
          <ChapterNumber id={`${questionHeadingId}-eyebrow`} className="font-display">
            {stem.chapterLabel}
          </ChapterNumber>
          <h2
            id={questionHeadingId}
            ref={headingRef}
            tabIndex={-1}
            data-testid="exam-question-heading"
            aria-describedby={`${questionHeadingId}-eyebrow ${questionHeadingId}-state`}
            className="min-w-0 break-words font-display text-display-md font-semibold leading-snug text-ink focus-visible:outline-none"
          >
            {stem.title}
          </h2>
          <span id={`${questionHeadingId}-state`} className="sr-only">
            第 {progress.current} 题，{answeredLabel}。
          </span>
        </header>

        <div
          className="flex flex-col gap-3"
          role={selectionType === "multiple" ? "group" : "radiogroup"}
          aria-labelledby={questionHeadingId}
          aria-describedby={`${questionHeadingId}-state`}
        >
          {options.map((option) => (
            <OptionCard
              key={option.label}
              label={option.label}
              content={option.content}
              selected={option.selected}
              disabled={option.disabled}
              selectionRole={selectionType === "multiple" ? "checkbox" : "radio"}
              questionType={selectionType}
              onSelect={onSelectOption}
            />
          ))}
        </div>

        {children ? <div className="border-t border-hairline pt-4">{children}</div> : null}

        <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-hairline pt-4">
          <Button
            type="button"
            variant="outline"
            onClick={nav.onPrev}
            disabled={nav.prevDisabled || !nav.onPrev}
            aria-label="上一题"
          >
            <ChevronLeft data-icon="inline-start" />
            上一题
          </Button>

          <div className="flex flex-wrap items-center gap-3">
            {nav.onSave ? (
              <Button
                type="button"
                variant="outline"
                onClick={nav.onSave}
                disabled={nav.saving}
                aria-label={nav.saveLabel ?? candidateActionCopy.saveAnswer}
              >
                <Save data-icon="inline-start" />
                {nav.saving
                  ? candidateActionCopy.savingAnswer
                  : (nav.saveLabel ?? candidateActionCopy.saveAnswer)}
              </Button>
            ) : null}
            {nav.onNext ? (
              <Button
                type="button"
                onClick={nav.onNext}
                disabled={nav.nextDisabled}
                aria-label={nav.nextLabel ?? "下一题"}
              >
                {nav.nextLabel ?? "下一题"}
                <ChevronRight data-icon="inline-end" />
              </Button>
            ) : null}
          </div>
        </footer>
      </article>
    </div>
  );
}
