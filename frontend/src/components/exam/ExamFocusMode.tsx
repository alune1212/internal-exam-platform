import { ChevronLeft, ChevronRight, Save } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import { OptionCard } from "./OptionCard";
import { ProgressCapsule } from "./ProgressCapsule";
import { Timer } from "./Timer";

export type ExamFocusModeProps = {
  progress: {
    current: number;
    total: number;
    answered: number;
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
  selectionType?: "single" | "multiple";
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
}: ExamFocusModeProps) {
  return (
    <div className={cn("flex flex-col gap-6", className)}>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <ProgressCapsule
          current={progress.current}
          total={progress.total}
          answered={progress.answered}
        />
        <Timer remainingSeconds={remainingSeconds} />
      </div>

      <article className="flex flex-col gap-6 rounded-lg border border-hairline bg-surface-card p-6 shadow-card md:p-8">
        <header className="flex flex-col gap-2 border-b border-hairline pb-4">
          <span className="font-display text-caption uppercase italic tracking-[0.18em] text-muted">
            {stem.chapterLabel}
          </span>
          <h2 className="font-display text-[26px] font-semibold leading-snug text-ink">
            {stem.title}
          </h2>
        </header>

        <div
          className="flex flex-col gap-3"
          role={selectionType === "single" ? "radiogroup" : "group"}
          aria-label="选项列表"
        >
          {options.map((option) => (
            <OptionCard
              key={option.label}
              label={option.label}
              content={option.content}
              selected={option.selected}
              disabled={option.disabled}
              selectionRole={selectionType === "multiple" ? "checkbox" : "radio"}
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
                aria-label={nav.saveLabel ?? "暂存答案"}
              >
                <Save data-icon="inline-start" />
                {nav.saving ? "正在暂存" : (nav.saveLabel ?? "暂存答案")}
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
