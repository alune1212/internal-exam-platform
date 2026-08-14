import * as React from "react";

import { cn } from "@/lib/utils";

export type FieldGroupProps = React.HTMLAttributes<HTMLDivElement>;

export type FieldState = "default" | "disabled" | "pending" | "invalid" | "success";

export interface FieldProps extends React.HTMLAttributes<HTMLDivElement> {
  orientation?: "vertical" | "horizontal";
  /** A semantic state for the field and its associated native control. */
  state?: FieldState;
  /** Marks all controls in the field unavailable while preserving native semantics. */
  disabled?: boolean;
  /** Marks the field as waiting for a mutation or async validation. */
  pending?: boolean;
  /** Marks the field and its control as invalid. */
  invalid?: boolean;
  /** Marks the field as successfully validated or saved. */
  success?: boolean;
  "data-disabled"?: string | boolean;
  "data-pending"?: string | boolean;
  "data-invalid"?: string | boolean;
  "data-success"?: string | boolean;
  "data-state"?: string;
}

export type FieldLabelProps = React.LabelHTMLAttributes<HTMLLabelElement>;
export type FieldDescriptionProps = React.HTMLAttributes<HTMLParagraphElement>;
export type FieldErrorProps = React.HTMLAttributes<HTMLParagraphElement>;

interface FieldContextValue {
  fieldId: string;
  controlId: string;
  labelId: string;
  descriptionIds: string[];
  errorIds: string[];
  state: FieldState;
  disabled: boolean;
  pending: boolean;
  invalid: boolean;
  success: boolean;
  registerControlId: (id: string) => void;
  registerDescription: (id: string) => void;
  unregisterDescription: (id: string) => void;
  registerError: (id: string) => void;
  unregisterError: (id: string) => void;
}

const FieldContext = React.createContext<FieldContextValue | null>(null);

const useSafeId = (prefix: string) => {
  const id = React.useId();
  return `${prefix}-${id.replace(/:/g, "")}`;
};

function mergeIds(...values: Array<string | undefined | null>) {
  const ids = values.flatMap((value) => (value ? value.split(/\s+/) : []));
  return Array.from(new Set(ids.filter(Boolean))).join(" ") || undefined;
}

const hasDataFlag = (value: string | boolean | undefined) => value !== undefined && value !== false;

const dataFlagValue = (enabled: boolean, value: string | boolean | undefined) =>
  enabled ? (typeof value === "string" && value ? value : "true") : undefined;

export interface FieldControlOptions {
  id?: string;
  disabled?: boolean;
  ariaInvalid?: React.AriaAttributes["aria-invalid"];
  ariaDescribedBy?: React.AriaAttributes["aria-describedby"];
  ariaBusy?: React.AriaAttributes["aria-busy"];
}

export interface FieldControlState {
  id?: string;
  disabled?: boolean;
  ariaInvalid?: React.AriaAttributes["aria-invalid"];
  ariaDescribedBy?: string;
  ariaBusy?: React.AriaAttributes["aria-busy"];
  state?: FieldState;
  dataDisabled?: boolean;
  dataPending?: boolean;
  dataInvalid?: boolean;
  dataSuccess?: boolean;
}

/**
 * Connects a native control to the surrounding Field without requiring a
 * schema-specific wrapper. Input, Textarea, and Select use this hook so their
 * labels, descriptions, and errors remain associated even when a field state
 * changes after the first render.
 */
// eslint-disable-next-line react-refresh/only-export-components
export function useFieldControl({
  id,
  disabled,
  ariaInvalid,
  ariaDescribedBy,
  ariaBusy,
}: FieldControlOptions = {}): FieldControlState {
  const context = React.useContext(FieldContext);
  const controlId = id ?? context?.controlId;
  const registerControlId = context?.registerControlId;

  React.useEffect(() => {
    if (registerControlId && controlId) {
      registerControlId(controlId);
    }
  }, [controlId, registerControlId]);

  if (!context) {
    return {
      id,
      disabled,
      ariaInvalid,
      ariaDescribedBy: typeof ariaDescribedBy === "string" ? ariaDescribedBy : undefined,
      ariaBusy,
    };
  }

  const fieldDisabled = context.disabled || context.pending;
  const resolvedInvalid = ariaInvalid ?? (context.invalid ? true : undefined);
  const resolvedBusy = ariaBusy ?? (context.pending ? true : undefined);

  return {
    id: controlId,
    disabled: disabled ?? fieldDisabled,
    ariaInvalid: resolvedInvalid,
    ariaDescribedBy: mergeIds(
      typeof ariaDescribedBy === "string" ? ariaDescribedBy : undefined,
      ...context.descriptionIds,
      ...context.errorIds,
    ),
    ariaBusy: resolvedBusy,
    state: context.state,
    dataDisabled: fieldDisabled,
    dataPending: context.pending,
    dataInvalid: context.invalid,
    dataSuccess: context.success,
  };
}

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
    const generatedFieldId = useSafeId("field");
    const fieldId = id ?? generatedFieldId;
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
    const [controlId, setControlId] = React.useState(`${fieldId}-control`);
    const [descriptionIds, setDescriptionIds] = React.useState<string[]>([]);
    const [errorIds, setErrorIds] = React.useState<string[]>([]);

    React.useEffect(() => {
      setControlId((current) =>
        current.startsWith(`${fieldId}-`) ? `${fieldId}-control` : current,
      );
    }, [fieldId]);

    const registerControlId = React.useCallback((nextId: string) => {
      setControlId(nextId);
    }, []);
    const registerDescription = React.useCallback((nextId: string) => {
      setDescriptionIds((current) => (current.includes(nextId) ? current : [...current, nextId]));
    }, []);
    const unregisterDescription = React.useCallback((nextId: string) => {
      setDescriptionIds((current) => current.filter((idValue) => idValue !== nextId));
    }, []);
    const registerError = React.useCallback((nextId: string) => {
      setErrorIds((current) => (current.includes(nextId) ? current : [...current, nextId]));
    }, []);
    const unregisterError = React.useCallback((nextId: string) => {
      setErrorIds((current) => current.filter((idValue) => idValue !== nextId));
    }, []);

    const contextValue = React.useMemo<FieldContextValue>(
      () => ({
        fieldId,
        controlId,
        labelId: `${fieldId}-label`,
        descriptionIds,
        errorIds,
        state: resolvedState,
        disabled: resolvedDisabled,
        pending: resolvedPending,
        invalid: resolvedInvalid,
        success: resolvedSuccess,
        registerControlId,
        registerDescription,
        unregisterDescription,
        registerError,
        unregisterError,
      }),
      [
        controlId,
        descriptionIds,
        errorIds,
        fieldId,
        registerControlId,
        registerDescription,
        unregisterDescription,
        registerError,
        unregisterError,
        resolvedDisabled,
        resolvedInvalid,
        resolvedPending,
        resolvedState,
        resolvedSuccess,
      ],
    );

    return (
      <FieldContext.Provider value={contextValue}>
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
            "flex flex-col gap-2",
            orientation === "horizontal" && "md:flex-row md:items-center md:justify-between",
            "data-[invalid]:text-error data-[success]:text-success data-[disabled]:opacity-70 data-[pending]:opacity-90",
            className,
          )}
          {...props}
        />
      </FieldContext.Provider>
    );
  },
);
Field.displayName = "Field";

export const FieldLabel = React.forwardRef<HTMLLabelElement, FieldLabelProps>(
  ({ className, id, htmlFor, ...props }, ref) => {
    const context = React.useContext(FieldContext);
    const labelId = id ?? (context ? context.labelId : undefined);
    const registerControlId = context?.registerControlId;

    React.useEffect(() => {
      if (registerControlId && htmlFor) {
        registerControlId(htmlFor);
      }
    }, [htmlFor, registerControlId]);

    return (
      <label
        ref={ref}
        id={labelId}
        htmlFor={htmlFor ?? context?.controlId}
        className={cn("text-caption font-medium uppercase tracking-caption text-muted", className)}
        {...props}
      />
    );
  },
);
FieldLabel.displayName = "FieldLabel";

export const FieldDescription = React.forwardRef<HTMLParagraphElement, FieldDescriptionProps>(
  ({ className, id, ...props }, ref) => {
    const context = React.useContext(FieldContext);
    const generatedId = useSafeId("field-description");
    const descriptionId =
      id ?? (context ? `${context.fieldId}-description-${generatedId}` : undefined);
    const registerDescription = context?.registerDescription;
    const unregisterDescription = context?.unregisterDescription;

    React.useEffect(() => {
      if (!registerDescription || !unregisterDescription || !descriptionId) return;
      registerDescription(descriptionId);
      return () => unregisterDescription(descriptionId);
    }, [descriptionId, registerDescription, unregisterDescription]);

    return (
      <p
        ref={ref}
        id={descriptionId}
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
    const context = React.useContext(FieldContext);
    const generatedId = useSafeId("field-error");
    const errorId = id ?? (context ? `${context.fieldId}-error-${generatedId}` : undefined);
    const registerError = context?.registerError;
    const unregisterError = context?.unregisterError;

    React.useEffect(() => {
      if (!registerError || !unregisterError || !errorId) return;
      registerError(errorId);
      return () => unregisterError(errorId);
    }, [errorId, registerError, unregisterError]);

    return (
      <p
        ref={ref}
        id={errorId}
        data-slot="field-error"
        role="alert"
        className={cn("text-body-sm leading-relaxed text-error", className)}
        {...props}
      />
    );
  },
);
FieldError.displayName = "FieldError";
