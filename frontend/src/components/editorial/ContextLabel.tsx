import * as React from "react";

import { hasMeaningfulContent } from "@/lib/children";
import { cn } from "@/lib/utils";

export interface ContextLabelProps extends React.HTMLAttributes<HTMLSpanElement> {
  children: React.ReactNode;
}

/**
 * A quiet, upright label for real route, workflow, and state context. Unlike
 * ChapterNumber it carries no ordinal rule and must not imply fake sequence.
 */
export function ContextLabel({ children, className, ...props }: ContextLabelProps) {
  if (!hasMeaningfulContent(children)) return null;

  return (
    <span
      data-context-label=""
      className={cn(
        "inline-flex min-w-0 max-w-full text-caption font-medium tracking-caption text-muted",
        className,
      )}
      {...props}
    >
      <span className="min-w-0 break-words">{children}</span>
    </span>
  );
}
