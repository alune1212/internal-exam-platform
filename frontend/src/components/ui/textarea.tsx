import * as React from "react";

import { cn } from "@/lib/utils";

export type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement>;

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        "min-h-32 w-full resize-y rounded-md border border-hairline bg-canvas-warm px-4 py-3 text-body-sm leading-relaxed text-ink shadow-sm",
        "placeholder:text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 focus-visible:ring-offset-canvas",
        "disabled:cursor-not-allowed disabled:opacity-60 aria-[invalid=true]:border-error",
        className,
      )}
      {...props}
    />
  ),
);
Textarea.displayName = "Textarea";
