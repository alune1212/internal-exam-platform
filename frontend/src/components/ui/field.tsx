import * as React from "react";

import { cn } from "@/lib/utils";

export type FieldGroupProps = React.HTMLAttributes<HTMLDivElement>;
export interface FieldProps extends React.HTMLAttributes<HTMLDivElement> {
  orientation?: "vertical" | "horizontal";
}
export type FieldLabelProps = React.LabelHTMLAttributes<HTMLLabelElement>;
export type FieldDescriptionProps = React.HTMLAttributes<HTMLParagraphElement>;
export type FieldErrorProps = React.HTMLAttributes<HTMLParagraphElement>;

export const FieldGroup = React.forwardRef<HTMLDivElement, FieldGroupProps>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("flex flex-col gap-5", className)} {...props} />
  ),
);
FieldGroup.displayName = "FieldGroup";

export const Field = React.forwardRef<HTMLDivElement, FieldProps>(
  ({ className, orientation = "vertical", ...props }, ref) => (
    <div
      ref={ref}
      data-slot="field"
      className={cn(
        "flex flex-col gap-2",
        orientation === "horizontal" && "md:flex-row md:items-center md:justify-between",
        "data-[invalid]:text-error data-[disabled]:opacity-70",
        className,
      )}
      {...props}
    />
  ),
);
Field.displayName = "Field";

export const FieldLabel = React.forwardRef<HTMLLabelElement, FieldLabelProps>(
  ({ className, ...props }, ref) => (
    <label
      ref={ref}
      className={cn("text-caption font-medium uppercase tracking-[0.16em] text-muted", className)}
      {...props}
    />
  ),
);
FieldLabel.displayName = "FieldLabel";

export const FieldDescription = React.forwardRef<HTMLParagraphElement, FieldDescriptionProps>(
  ({ className, ...props }, ref) => (
    <p ref={ref} className={cn("text-body-sm leading-relaxed text-muted", className)} {...props} />
  ),
);
FieldDescription.displayName = "FieldDescription";

export const FieldError = React.forwardRef<HTMLParagraphElement, FieldErrorProps>(
  ({ className, ...props }, ref) => (
    <p
      ref={ref}
      role="alert"
      className={cn("text-body-sm leading-relaxed text-error", className)}
      {...props}
    />
  ),
);
FieldError.displayName = "FieldError";
