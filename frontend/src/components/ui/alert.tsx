import * as React from "react";

import { cn } from "@/lib/utils";

export type AlertVariant = "default" | "success" | "warning" | "error";

export interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: AlertVariant;
}
export type AlertTitleProps = React.HTMLAttributes<HTMLDivElement>;
export type AlertDescriptionProps = React.HTMLAttributes<HTMLParagraphElement>;

const variantClasses: Record<AlertVariant, string> = {
  default: "border-hairline text-body",
  success: "border-success text-success",
  warning: "border-warning text-warning",
  error: "border-error text-error",
};

export const Alert = React.forwardRef<HTMLDivElement, AlertProps>(
  ({ className, variant = "default", role, ...props }, ref) => (
    <div
      ref={ref}
      role={role ?? (variant === "error" ? "alert" : "status")}
      className={cn(
        "flex flex-col gap-1 rounded-md border bg-canvas p-3 text-body-sm",
        variantClasses[variant],
        className,
      )}
      {...props}
    />
  ),
);
Alert.displayName = "Alert";

export const AlertTitle = React.forwardRef<HTMLDivElement, AlertTitleProps>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "min-w-0 break-words text-caption font-medium uppercase tracking-[0.16em]",
        className,
      )}
      {...props}
    />
  ),
);
AlertTitle.displayName = "AlertTitle";

export const AlertDescription = React.forwardRef<HTMLParagraphElement, AlertDescriptionProps>(
  ({ className, ...props }, ref) => (
    <p ref={ref} className={cn("leading-relaxed", className)} {...props} />
  ),
);
AlertDescription.displayName = "AlertDescription";
