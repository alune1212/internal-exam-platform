import * as React from "react";

import { useFieldControl, type FieldState } from "./field";
import { controlClasses } from "./control-base";

export type SelectProps = React.SelectHTMLAttributes<HTMLSelectElement> & {
  "data-state"?: FieldState | string;
};

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
        className={controlClasses("select", className)}
        {...props}
      />
    );
  },
);
Select.displayName = "Select";
