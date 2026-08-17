import * as React from "react";

import { cn } from "@/lib/utils";

export type StatusPillVariant =
  | "default"
  | "neutral"
  | "info"
  | "pending"
  | "success"
  | "warning"
  | "error";

export interface StatusPillProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: StatusPillVariant;
  /** Alias for callers that use the broader status vocabulary. */
  tone?: StatusPillVariant;
  children: React.ReactNode;
}

const variantClass: Record<StatusPillVariant, string> = {
  default: "border border-hairline bg-canvas-warm text-ink",
  neutral: "border border-hairline bg-canvas-warm text-ink",
  info: "border border-ink-blue bg-canvas text-ink-blue",
  pending: "border border-warning-border bg-warning-surface text-status-warning",
  success: "border border-success-border bg-success-surface text-status-success",
  warning: "border border-warning-border bg-warning-surface text-status-warning",
  error: "border border-error-border bg-error-surface text-status-error",
};

export function StatusPill({
  variant = "default",
  tone,
  className,
  children,
  role,
  "aria-label": ariaLabel,
  ...props
}: StatusPillProps) {
  const resolvedVariant = tone ?? variant;

  return (
    <span
      role={role ?? "status"}
      aria-label={ariaLabel}
      data-feedback-kind="status-pill"
      data-status={resolvedVariant}
      data-status-variant={resolvedVariant}
      data-color-independent="true"
      className={cn(
        "inline-flex items-center rounded-sm px-2 py-px text-caption uppercase tracking-caption",
        variantClass[resolvedVariant],
        className,
      )}
      {...props}
    >
      {children}
    </span>
  );
}
