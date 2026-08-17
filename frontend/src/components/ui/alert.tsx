import * as React from "react";

import { cn } from "@/lib/utils";

export type AlertVariant = "default" | "info" | "pending" | "success" | "warning" | "error";

export interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: AlertVariant;
  /** Alias for status-oriented call sites. */
  tone?: AlertVariant;
}
export type AlertTitleProps = React.HTMLAttributes<HTMLDivElement>;
export type AlertDescriptionProps = React.HTMLAttributes<HTMLParagraphElement>;

const variantClasses: Record<AlertVariant, string> = {
  default: "border-hairline text-body",
  info: "border-ink-blue text-ink-blue",
  pending: "border-warning-border bg-warning-surface text-status-warning",
  success: "border-success-border bg-success-surface text-status-success",
  warning: "border-warning-border bg-warning-surface text-status-warning",
  error: "border-error-border bg-error-surface text-status-error",
};

export const Alert = React.forwardRef<HTMLDivElement, AlertProps>(
  ({ className, variant = "default", tone, role, ...props }, ref) => {
    const resolvedVariant = tone ?? variant;

    return (
      <div
        ref={ref}
        role={role ?? (resolvedVariant === "error" ? "alert" : "status")}
        data-feedback-kind="alert"
        data-status={resolvedVariant}
        data-alert-variant={resolvedVariant}
        data-color-independent="true"
        className={cn(
          "flex flex-col gap-1 rounded-md border bg-canvas p-3 text-body-sm",
          variantClasses[resolvedVariant],
          className,
        )}
        {...props}
      />
    );
  },
);
Alert.displayName = "Alert";

export const AlertTitle = React.forwardRef<HTMLDivElement, AlertTitleProps>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      data-slot="alert-title"
      className={cn(
        "min-w-0 break-words text-caption font-medium uppercase tracking-caption",
        className,
      )}
      {...props}
    />
  ),
);
AlertTitle.displayName = "AlertTitle";

export const AlertDescription = React.forwardRef<HTMLParagraphElement, AlertDescriptionProps>(
  ({ className, ...props }, ref) => (
    <p
      ref={ref}
      data-slot="alert-description"
      className={cn("leading-relaxed", className)}
      {...props}
    />
  ),
);
AlertDescription.displayName = "AlertDescription";
