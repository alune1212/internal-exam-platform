import * as React from "react";

import { cn } from "@/lib/utils";

export type StatusPillVariant = "default" | "success" | "warning" | "error";

export interface StatusPillProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: StatusPillVariant;
  children: React.ReactNode;
}

const variantClass: Record<StatusPillVariant, string> = {
  default: "border border-hairline bg-canvas-warm text-ink",
  success: "border border-success/30 bg-canvas text-success",
  warning: "border border-warning/30 bg-canvas text-warning",
  error: "border border-error/30 bg-canvas text-error",
};

export function StatusPill({
  variant = "default",
  className,
  children,
  ...props
}: StatusPillProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-sm px-2 py-px text-[11px] uppercase tracking-[0.16em]",
        variantClass[variant],
        className,
      )}
      {...props}
    >
      {children}
    </span>
  );
}
