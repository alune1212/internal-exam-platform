import { Check, X } from "lucide-react";

import { cn } from "@/lib/utils";

export type OptionCardProps = {
  label: string;
  content: string;
  selected: boolean;
  onSelect: (label: string) => void;
  disabled?: boolean;
  selectionRole?: "radio" | "checkbox";
  questionType?: "single" | "multiple" | "judge";
};

export function OptionCard({
  label,
  content,
  selected,
  onSelect,
  disabled,
  selectionRole = "radio",
  questionType = "single",
}: OptionCardProps) {
  const isJudge = questionType === "judge";

  return (
    <button
      type="button"
      role={selectionRole}
      aria-checked={selected}
      aria-label={`选项 ${label}：${content}`}
      disabled={disabled}
      onClick={() => onSelect(label)}
      className={cn(
        "flex w-full items-center gap-3 border px-4 py-3 text-left",
        "transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2",
        "disabled:cursor-not-allowed disabled:opacity-50",
        isJudge
          ? "min-h-14 justify-center rounded-lg border-[1.5px] text-center md:min-h-16"
          : "min-h-12 rounded-md md:min-h-14",
        selected ? "border-ink bg-surface-card ring-1 ring-ink" : "border-hairline bg-canvas",
      )}
    >
      {isJudge ? (
        <span
          aria-hidden="true"
          className={cn(
            "inline-flex size-5 shrink-0 items-center justify-center rounded-full [&_[data-icon]]:size-3 [&_[data-icon]]:shrink-0",
            selected ? "bg-ink text-canvas" : "border border-hairline bg-canvas text-muted",
          )}
        >
          {label === "A" ? (
            <Check data-icon="inline-start" strokeWidth={3} />
          ) : (
            <X data-icon="inline-start" strokeWidth={3} />
          )}
        </span>
      ) : (
        <span
          aria-hidden="true"
          className={cn(
            "inline-flex size-6 shrink-0 items-center justify-center",
            "font-mono text-caption font-semibold tabular-nums",
            selectionRole === "checkbox"
              ? cn(
                  "rounded-sm",
                  selected ? "bg-ink text-canvas" : "border border-hairline bg-canvas text-ink",
                )
              : cn(
                  "rounded-full",
                  selected ? "bg-ink text-canvas" : "border border-hairline bg-canvas text-ink",
                ),
          )}
        >
          {label}
        </span>
      )}
      <span className="flex-1 text-body leading-relaxed text-ink">{content}</span>
    </button>
  );
}
