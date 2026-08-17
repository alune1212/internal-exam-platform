import * as React from "react";

import { useFieldControl, type FieldState } from "./field";
import { controlClasses } from "./control-base";

export type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement> & {
  "data-state"?: FieldState | string;
};

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
        className={controlClasses("textarea", className)}
        {...props}
      />
    );
  },
);
Textarea.displayName = "Textarea";
