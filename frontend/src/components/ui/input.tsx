import * as React from "react";

import { cn } from "@/lib/utils";
import { useFieldControl, type FieldState } from "./field";

export type InputProps = React.InputHTMLAttributes<HTMLInputElement> & {
  "data-state"?: FieldState | string;
};

const inputControlClasses =
  "flex h-11 w-full rounded-md border border-hairline bg-canvas px-3.5 text-body-sm text-ink outline-none transition-[border-color,background-color,box-shadow,color] duration-fast ease-standard file:border-0 file:bg-transparent file:text-body-sm file:font-medium placeholder:text-muted hover:border-ink-soft focus-visible:border-ink focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 focus-visible:ring-offset-canvas disabled:cursor-not-allowed disabled:opacity-50 aria-[invalid=true]:border-error data-[invalid]:border-error data-[success]:border-success data-[state=success]:border-success";

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    {
      className,
      type,
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
      <input
        ref={ref}
        id={fieldControl.id}
        type={type}
        disabled={fieldControl.disabled}
        aria-describedby={fieldControl.ariaDescribedBy}
        aria-invalid={fieldControl.ariaInvalid}
        aria-busy={fieldControl.ariaBusy}
        data-state={dataState ?? fieldControl.state}
        data-disabled={fieldControl.dataDisabled || undefined}
        data-pending={fieldControl.dataPending || undefined}
        data-invalid={fieldControl.dataInvalid || undefined}
        data-success={fieldControl.dataSuccess || undefined}
        className={cn(inputControlClasses, className)}
        {...props}
      />
    );
  },
);
Input.displayName = "Input";
