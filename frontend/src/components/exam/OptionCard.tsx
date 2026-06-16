import { cn } from "@/lib/utils";

export type OptionCardProps = {
  label: string;
  content: string;
  selected: boolean;
  onSelect: (label: string) => void;
  disabled?: boolean;
  selectionRole?: "radio" | "checkbox";
};

export function OptionCard({
  label,
  content,
  selected,
  onSelect,
  disabled,
  selectionRole = "radio",
}: OptionCardProps) {
  return (
    <button
      type="button"
      role={selectionRole}
      aria-checked={selected}
      aria-label={`选项 ${label}：${content}`}
      disabled={disabled}
      onClick={() => onSelect(label)}
      className={cn(
        "flex min-h-12 w-full items-center gap-3 rounded-md border px-4 py-3 text-left md:min-h-14",
        "transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2",
        "disabled:cursor-not-allowed disabled:opacity-50",
        selected ? "border-ink bg-surface-card ring-1 ring-ink" : "border-hairline bg-canvas",
      )}
    >
      <span
        aria-hidden="true"
        className={cn(
          "inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full",
          "font-mono text-caption font-semibold tabular-nums",
          selected ? "bg-ink text-canvas" : "border border-hairline bg-canvas text-ink",
        )}
      >
        {label}
      </span>
      <span className="flex-1 text-body leading-relaxed text-ink">{content}</span>
    </button>
  );
}
