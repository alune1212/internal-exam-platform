import * as React from "react";

import { cn } from "@/lib/utils";

export type FieldGroupProps = React.HTMLAttributes<HTMLDivElement>;

export type FieldState = "default" | "disabled" | "pending" | "invalid" | "success";

export interface FieldProps extends React.HTMLAttributes<HTMLDivElement> {
  orientation?: "vertical" | "horizontal";
  /** Marks all controls in the field unavailable while preserving native semantics. */
  disabled?: boolean;
  /** Marks the field as waiting for a mutation or async validation. */
  pending?: boolean;
  /** Marks the field as invalid. */
  invalid?: boolean;
  /** Marks the field as successfully validated or saved. */
  success?: boolean;
  /** A semantic state for the field and its associated native control. */
  state?: FieldState;
  "data-disabled"?: string | boolean;
  "data-pending"?: string | boolean;
  "data-invalid"?: string | boolean;
  "data-success"?: string | boolean;
  "data-state"?: string;
}

export type FieldLabelProps = React.LabelHTMLAttributes<HTMLLabelElement>;
export type FieldDescriptionProps = React.HTMLAttributes<HTMLParagraphElement>;
export type FieldErrorProps = React.HTMLAttributes<HTMLParagraphElement>;

const hasDataFlag = (value: string | boolean | undefined) => value !== undefined && value !== false;

const dataFlagValue = (enabled: boolean, value: string | boolean | undefined) =>
  enabled ? (typeof value === "string" && value ? value : "true") : undefined;

export const FieldGroup = React.forwardRef<HTMLDivElement, FieldGroupProps>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("flex flex-col gap-5", className)} {...props} />
  ),
);
FieldGroup.displayName = "FieldGroup";

export const Field = React.forwardRef<HTMLDivElement, FieldProps>(
  (
    {
      className,
      id,
      orientation = "vertical",
      state,
      disabled = false,
      pending = false,
      invalid = false,
      success = false,
      "data-disabled": dataDisabled,
      "data-pending": dataPending,
      "data-invalid": dataInvalid,
      "data-success": dataSuccess,
      "data-state": dataState,
      "aria-disabled": ariaDisabled,
      "aria-busy": ariaBusy,
      ...props
    },
    ref,
  ) => {
    const resolvedDisabled = disabled || hasDataFlag(dataDisabled) || state === "disabled";
    const resolvedPending = pending || hasDataFlag(dataPending) || state === "pending";
    const resolvedInvalid = invalid || hasDataFlag(dataInvalid) || state === "invalid";
    const resolvedSuccess = success || hasDataFlag(dataSuccess) || state === "success";
    const resolvedState: FieldState =
      state ??
      (resolvedPending
        ? "pending"
        : resolvedInvalid
          ? "invalid"
          : resolvedSuccess
            ? "success"
            : resolvedDisabled
              ? "disabled"
              : "default");

    return (
      <div
        ref={ref}
        id={id}
        data-slot="field"
        data-state={dataState ?? resolvedState}
        data-disabled={dataFlagValue(resolvedDisabled, dataDisabled)}
        data-pending={dataFlagValue(resolvedPending, dataPending)}
        data-invalid={dataFlagValue(resolvedInvalid, dataInvalid)}
        data-success={dataFlagValue(resolvedSuccess, dataSuccess)}
        aria-disabled={ariaDisabled ?? (resolvedDisabled ? true : undefined)}
        aria-busy={ariaBusy ?? (resolvedPending ? true : undefined)}
        className={cn(
          "flex min-w-0 flex-col gap-2",
          orientation === "horizontal" && "md:flex-row md:items-center md:justify-between",
          "data-[invalid]:text-error data-[success]:text-success data-[disabled]:opacity-70 data-[pending]:opacity-90",
          className,
        )}
        {...props}
      />
    );
  },
);
Field.displayName = "Field";

export const FieldLabel = React.forwardRef<HTMLLabelElement, FieldLabelProps>(
  ({ className, ...props }, ref) => (
    <label
      ref={ref}
      className={cn("text-body-sm font-medium leading-snug text-ink", className)}
      {...props}
    />
  ),
);
FieldLabel.displayName = "FieldLabel";

export const FieldDescription = React.forwardRef<HTMLParagraphElement, FieldDescriptionProps>(
  ({ className, id, ...props }, ref) => {
    const generatedId = React.useId();
    const resolvedId = id ?? generatedId;

    return (
      <p
        ref={ref}
        id={resolvedId}
        data-slot="field-description"
        className={cn("text-body-sm leading-relaxed text-muted", className)}
        {...props}
      />
    );
  },
);
FieldDescription.displayName = "FieldDescription";

export const FieldError = React.forwardRef<HTMLParagraphElement, FieldErrorProps>(
  ({ className, id, ...props }, ref) => {
    const generatedId = React.useId();
    const resolvedId = id ?? generatedId;

    return (
      <p
        ref={ref}
        id={resolvedId}
        data-slot="field-error"
        role="alert"
        className={cn("text-body-sm leading-relaxed text-error", className)}
        {...props}
      />
    );
  },
);
FieldError.displayName = "FieldError";
