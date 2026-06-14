import { cn } from "@/lib/utils";

export type TimerProps = {
  remainingSeconds: number;
  criticalThresholdSeconds?: number;
  className?: string;
};

const PULSE_DURATION_MS = 1000;

function formatMmSs(totalSeconds: number): string {
  if (!Number.isFinite(totalSeconds)) {
    return "--:--";
  }
  const safe = Math.max(0, Math.floor(totalSeconds));
  const minutes = Math.floor(safe / 60);
  const seconds = safe % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

export function Timer({ remainingSeconds, criticalThresholdSeconds = 300, className }: TimerProps) {
  const isCritical =
    Number.isFinite(remainingSeconds) && remainingSeconds <= criticalThresholdSeconds;
  const display = formatMmSs(remainingSeconds);

  return (
    <div className={cn("flex flex-col gap-1", className)}>
      <span className="text-caption uppercase tracking-[0.16em] text-muted">
        REMAINING · 剩余时间
      </span>
      <span
        className={cn(isCritical && "animate-pulse")}
        style={isCritical ? { animationDuration: `${PULSE_DURATION_MS}ms` } : undefined}
      >
        <span
          aria-live="polite"
          aria-atomic="true"
          className={cn(
            "font-display text-[32px] font-semibold tabular-nums leading-none text-ink",
            isCritical && "text-error",
          )}
        >
          {display}
        </span>
      </span>
    </div>
  );
}
