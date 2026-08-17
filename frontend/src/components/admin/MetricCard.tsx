import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/utils";

export type MetricTone = "default" | "info" | "success" | "warning" | "error";

export interface MetricCardProps extends HTMLAttributes<HTMLDivElement> {
  label: ReactNode;
  value: ReactNode;
  unit?: ReactNode;
  tone?: MetricTone;
  caption?: ReactNode;
}

const TONE_CLASS: Record<MetricTone, string> = {
  default: "text-ink",
  info: "text-ink-blue",
  success: "text-success",
  warning: "text-warning",
  error: "text-error",
};

export function MetricCard({
  label,
  value,
  unit,
  tone = "default",
  caption,
  className,
  ...props
}: MetricCardProps) {
  return (
    <div
      {...props}
      data-surface-owner="metric-card"
      data-surface-role="focus"
      data-color-independent="true"
      data-metric-tone={tone}
      className={cn(
        "min-w-0 rounded-lg border border-hairline bg-canvas p-5 shadow-card",
        className,
      )}
    >
      <p className="break-words text-caption font-medium tracking-caption text-muted">{label}</p>
      <p className="mt-3 flex min-w-0 flex-wrap items-baseline gap-1 break-words font-display text-display-md font-semibold lg:text-display-lg">
        <span className={cn(TONE_CLASS[tone])}>{value}</span>
        {unit ? <span className="text-body-sm text-muted">{unit}</span> : null}
      </p>
      {caption ? <p className="mt-3 text-caption text-muted">{caption}</p> : null}
    </div>
  );
}
