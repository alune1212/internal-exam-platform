import * as React from "react";

import { cn } from "@/lib/utils";

export type ActivityDotStatus = "neutral" | "success" | "warning" | "error" | "info";

export interface ActivityDotProps extends React.HTMLAttributes<HTMLSpanElement> {
  status?: ActivityDotStatus;
  /** Visible text is preferred; this label covers the dot-only case. */
  label?: string;
}

const statusClass: Record<ActivityDotStatus, string> = {
  neutral: "bg-muted",
  success: "bg-success",
  warning: "bg-warning",
  error: "bg-error",
  info: "bg-ink-blue",
};

const defaultLabel: Record<ActivityDotStatus, string> = {
  neutral: "一般状态",
  success: "已完成",
  warning: "需要关注",
  error: "异常",
  info: "提示",
};

/**
 * A compact activity/status marker. It is intentionally not a pill or a page
 * state: the dot communicates timeline/row activity while the optional label
 * supplies a non-color meaning for assistive technology and narrow layouts.
 */
export function ActivityDot({
  status = "neutral",
  label,
  className,
  role,
  "aria-label": ariaLabel,
  children,
  ...props
}: ActivityDotProps) {
  const resolvedLabel = ariaLabel ?? label ?? (children ? undefined : defaultLabel[status]);

  return (
    <span
      {...props}
      role={role ?? (resolvedLabel || children ? "status" : undefined)}
      aria-label={resolvedLabel}
      data-feedback-kind="activity-dot"
      data-status={status}
      data-status-dot={status}
      data-color-independent="true"
      className={cn("inline-flex min-w-0 items-center gap-2 text-body-sm text-muted", className)}
    >
      <span
        aria-hidden="true"
        className={cn("size-2 shrink-0 rounded-full", statusClass[status])}
      />
      {label || children ? <span className="min-w-0 break-words">{label ?? children}</span> : null}
    </span>
  );
}

/** Alias for status-oriented call sites; both names share one owner. */
export const StatusDot = ActivityDot;
