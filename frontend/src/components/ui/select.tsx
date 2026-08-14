import * as React from "react";

import { cn } from "@/lib/utils";
import { useFieldControl, type FieldState } from "./field";

export type SelectProps = React.SelectHTMLAttributes<HTMLSelectElement> & {
  "data-state"?: FieldState | string;
};

const selectControlClasses =
  "flex h-11 w-full rounded-md border border-hairline bg-canvas px-3.5 text-body-sm text-ink outline-none transition-[border-color,background-color,box-shadow,color] duration-fast ease-standard hover:border-ink-soft focus-visible:border-ink focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 focus-visible:ring-offset-canvas disabled:cursor-not-allowed disabled:opacity-50 aria-[invalid=true]:border-error data-[invalid]:border-error data-[success]:border-success data-[state=success]:border-success";

/**
 * Native select control shared by filters and forms. Keeping the native
 * element preserves browser keyboard operation, option semantics, and mobile
 * picker behavior while Field supplies label and feedback associations.
 */
export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  (
    {
      className,
      id,
      disabled,
      "aria-describedby": ariaDescribedBy,
      "aria-invalid": ariaInvalid,
      "aria-busy": ariaBusy,
      "data-state": dataState,
      ...props
    },
    ref,
  ) => {
    const fieldControl = useFieldControl({
      id,
      disabled,
      ariaInvalid,
      ariaDescribedBy,
      ariaBusy,
    });

    return (
      <select
        ref={ref}
        id={fieldControl.id}
        disabled={fieldControl.disabled}
        aria-describedby={fieldControl.ariaDescribedBy}
        aria-invalid={fieldControl.ariaInvalid}
        aria-busy={fieldControl.ariaBusy}
        data-state={dataState ?? fieldControl.state}
        data-disabled={fieldControl.dataDisabled || undefined}
        data-pending={fieldControl.dataPending || undefined}
        data-invalid={fieldControl.dataInvalid || undefined}
        data-success={fieldControl.dataSuccess || undefined}
        className={cn(selectControlClasses, className)}
        {...props}
      />
    );
  },
);
Select.displayName = "Select";
