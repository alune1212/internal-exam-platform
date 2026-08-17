import { cn } from "@/lib/utils";

export type ProgressCapsuleProps = {
  current: number;
  total: number;
  answered: number;
  variant?: "light" | "dark";
  className?: string;
};

export function ProgressCapsule({
  current,
  total,
  answered,
  variant = "light",
  className,
}: ProgressCapsuleProps) {
  const safeTotal = total > 0 ? total : 0;
  const percent = safeTotal > 0 ? Math.round((answered / safeTotal) * 100) : 0;
  const paddedCurrent = String(current).padStart(2, "0");
  const paddedTotal = String(safeTotal).padStart(2, "0");
  const isDark = variant === "dark";

  return (
    <div
      role="status"
      aria-label={`进度：第 ${current} 题，共 ${total} 题，已答 ${answered} 题`}
      className={cn(
        "inline-flex items-center gap-3 rounded-pill border px-4 py-2 font-mono text-status font-status tabular-nums",
        isDark ? "border-footer bg-footer text-canvas" : "border-hairline bg-canvas text-ink",
        className,
      )}
    >
      <span>
        Q&nbsp;{paddedCurrent}&nbsp;/&nbsp;{paddedTotal}
      </span>
      <span
        aria-hidden="true"
        className={cn("h-3 w-px", isDark ? "bg-footer-soft" : "bg-hairline")}
      />
      <span
        aria-hidden="true"
        className={cn(
          "relative h-1 w-24 overflow-hidden rounded-pill",
          isDark ? "bg-footer" : "bg-hairline",
        )}
        style={
          isDark
            ? { backgroundColor: "color-mix(in srgb, var(--footer-soft) 40%, transparent)" }
            : undefined
        }
      >
        <span
          className={cn("absolute inset-y-0 left-0 rounded-pill", isDark ? "bg-canvas" : "bg-ink")}
          style={{ width: `${percent}%` }}
        />
      </span>
      <span>{percent}%</span>
    </div>
  );
}
