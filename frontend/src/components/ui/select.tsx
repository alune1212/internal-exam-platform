import * as React from "react";

import { cn } from "@/lib/utils";

import type { FieldState } from "./field";

const controlBaseClasses =
  "w-full rounded-md border border-hairline text-body-sm text-ink outline-none transition-[border-color,background-color,box-shadow,color] duration-fast ease-standard placeholder:text-muted hover:border-ink-soft focus-visible:border-ink focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 focus-visible:ring-offset-canvas disabled:cursor-not-allowed disabled:opacity-50 aria-[invalid=true]:border-error data-[invalid]:border-error data-[success]:border-success data-[state=success]:border-success";

const controlSelectVariant = "flex h-11 bg-canvas px-control-x";

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
    { className, id, "aria-describedby": ariaDescribedBy, "data-state": dataState, ...props },
    ref,
  ) => {
    const generatedId = React.useId();
    const resolvedId = id ?? generatedId;

    return (
      <select
        ref={ref}
        id={resolvedId}
        aria-describedby={ariaDescribedBy}
        data-state={dataState}
        className={cn(controlBaseClasses, controlSelectVariant, className)}
        {...props}
      />
    );
  },
);
Select.displayName = "Select";
