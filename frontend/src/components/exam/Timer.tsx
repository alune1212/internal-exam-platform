import { useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

export type TimerProps = {
  remainingSeconds: number;
  criticalThresholdSeconds?: number;
  className?: string;
};

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

  // Announce a single message the moment we cross into the critical window.
  const wasCriticalRef = useRef(false);
  const [announcement, setAnnouncement] = useState<string | null>(null);
  useEffect(() => {
    if (isCritical && !wasCriticalRef.current) {
      setAnnouncement("剩余时间不足 5 分钟。");
    }
    wasCriticalRef.current = isCritical;
  }, [isCritical]);

  return (
    <div className={cn("flex flex-col gap-1", className)}>
      <span className="text-caption uppercase tracking-[0.16em] text-muted">
        REMAINING · 剩余时间
      </span>
      <span className={cn(isCritical && "duration-pulse motion-safe:animate-pulse")}>
        <span
          aria-label={`剩余时间 ${display}`}
          className={cn(
            "font-display text-display-md font-semibold tabular-nums leading-none text-ink",
            isCritical && "text-error",
          )}
        >
          {display}
        </span>
      </span>
      <span role="status" aria-live="polite" className="sr-only">
        {announcement ?? ""}
      </span>
    </div>
  );
}
