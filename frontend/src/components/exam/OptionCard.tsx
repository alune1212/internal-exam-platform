import { Check, X } from "lucide-react";
import { useEffect, useRef } from "react";

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

function radioOptions(element: HTMLButtonElement) {
  const group = element.closest<HTMLElement>('[role="radiogroup"]');
  return group
    ? Array.from(group.querySelectorAll<HTMLButtonElement>('[role="radio"]')).filter(
        (option) => !option.disabled,
      )
    : [];
}

function syncRadioTabStops(element: HTMLButtonElement) {
  const options = radioOptions(element);
  if (!options.length) return;

  const selected = options.find((option) => option.getAttribute("aria-checked") === "true");
  const current = options.find((option) => option.tabIndex === 0);
  const tabStop = selected ?? current ?? options[0];
  options.forEach((option) => {
    option.tabIndex = option === tabStop ? 0 : -1;
  });
}

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
  const optionRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (selectionRole === "radio" && optionRef.current) {
      syncRadioTabStops(optionRef.current);
    }
  }, [content, disabled, label, selected, selectionRole]);

  function handleKeyDown(event: React.KeyboardEvent<HTMLButtonElement>) {
    if (selectionRole !== "radio") return;
    if (!(["ArrowDown", "ArrowRight", "ArrowUp", "ArrowLeft"] as string[]).includes(event.key)) {
      return;
    }

    const current = event.currentTarget;
    const options = radioOptions(current);
    if (!options.length) return;

    event.preventDefault();
    const currentIndex = options.indexOf(current);
    const movingBack = event.key === "ArrowUp" || event.key === "ArrowLeft";
    const nextIndex = (currentIndex + (movingBack ? -1 : 1) + options.length) % options.length;
    const next = options[nextIndex];
    next.focus();
    next.click();
  }

  return (
    <button
      ref={optionRef}
      type="button"
      role={selectionRole}
      aria-checked={selected}
      aria-disabled={disabled || undefined}
      aria-label={`选项 ${label}：${content}`}
      tabIndex={selectionRole === "radio" ? (selected ? 0 : undefined) : 0}
      disabled={disabled}
      onClick={() => onSelect(label)}
      onKeyDown={handleKeyDown}
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
            "inline-grid size-6 shrink-0 place-items-center text-center align-middle",
            "font-mono text-action font-action tabular-nums leading-none tracking-normal",
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
      <span className="min-w-0 flex-1 break-words text-body leading-relaxed text-ink">
        {content}
      </span>
    </button>
  );
}
