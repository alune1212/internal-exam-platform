import * as React from "react";

import { cn } from "@/lib/utils";

import type { FieldState } from "./field";

const controlBaseClasses =
  "w-full rounded-md border border-hairline text-body-sm text-ink outline-none transition-[border-color,background-color,box-shadow,color] duration-fast ease-standard placeholder:text-muted hover:border-ink-soft focus-visible:border-ink focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 focus-visible:ring-offset-canvas disabled:cursor-not-allowed disabled:opacity-50 aria-[invalid=true]:border-error data-[invalid]:border-error data-[success]:border-success data-[state=success]:border-success";

const controlInputVariant =
  "flex h-11 bg-canvas px-control-x file:border-0 file:bg-transparent file:text-body-sm file:font-medium";

export type InputProps = React.InputHTMLAttributes<HTMLInputElement> & {
  "data-state"?: FieldState | string;
};

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    { className, type, id, "aria-describedby": ariaDescribedBy, "data-state": dataState, ...props },
    ref,
  ) => {
    const generatedId = React.useId();
    const resolvedId = id ?? generatedId;

    return (
      <input
        ref={ref}
        id={resolvedId}
        type={type}
        aria-describedby={ariaDescribedBy}
        data-state={dataState}
        className={cn(controlBaseClasses, controlInputVariant, className)}
        {...props}
      />
    );
  },
);
Input.displayName = "Input";
