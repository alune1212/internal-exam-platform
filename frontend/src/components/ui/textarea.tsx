import * as React from "react";

import { cn } from "@/lib/utils";

import type { FieldState } from "./field";

const controlBaseClasses =
  "w-full rounded-md border border-hairline text-body-sm text-ink outline-none transition-[border-color,background-color,box-shadow,color] duration-fast ease-standard placeholder:text-muted hover:border-ink-soft focus-visible:border-ink focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 focus-visible:ring-offset-canvas disabled:cursor-not-allowed disabled:opacity-50 aria-[invalid=true]:border-error data-[invalid]:border-error data-[success]:border-success data-[state=success]:border-success";

const controlTextareaVariant = "min-h-32 resize-y bg-canvas-warm px-4 py-3 leading-relaxed";

export type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement> & {
  "data-state"?: FieldState | string;
};

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  (
    { className, id, "aria-describedby": ariaDescribedBy, "data-state": dataState, ...props },
    ref,
  ) => {
    const generatedId = React.useId();
    const resolvedId = id ?? generatedId;

    return (
      <textarea
        ref={ref}
        id={resolvedId}
        aria-describedby={ariaDescribedBy}
        data-state={dataState}
        className={cn(controlBaseClasses, controlTextareaVariant, className)}
        {...props}
      />
    );
  },
);
Textarea.displayName = "Textarea";
