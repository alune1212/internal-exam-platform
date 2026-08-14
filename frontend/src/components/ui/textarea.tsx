import * as React from "react";

import { cn } from "@/lib/utils";
import { useFieldControl, type FieldState } from "./field";

export type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement> & {
  "data-state"?: FieldState | string;
};

const textareaControlClasses =
  "min-h-32 w-full resize-y rounded-md border border-hairline bg-canvas-warm px-4 py-3 text-body-sm leading-relaxed text-ink outline-none transition-[border-color,background-color,box-shadow,color] duration-fast ease-standard placeholder:text-muted hover:border-ink-soft focus-visible:border-ink focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 focus-visible:ring-offset-canvas disabled:cursor-not-allowed disabled:opacity-50 aria-[invalid=true]:border-error data-[invalid]:border-error data-[success]:border-success data-[state=success]:border-success";

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
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
      <textarea
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
        className={cn(textareaControlClasses, className)}
        {...props}
      />
    );
  },
);
Textarea.displayName = "Textarea";
