import * as React from "react";

import { cn } from "@/lib/utils";

export interface ChapterNumberProps extends React.HTMLAttributes<HTMLSpanElement> {
  children: React.ReactNode;
}

function hasMeaningfulContent(value: React.ReactNode): boolean {
  if (value === null || value === undefined || typeof value === "boolean") return false;
  if (typeof value === "string") return value.trim().length > 0;
  if (Array.isArray(value)) return value.some(hasMeaningfulContent);
  return true;
}

export function ChapterNumber({ children, className, ...props }: ChapterNumberProps) {
  if (!hasMeaningfulContent(children)) return null;

  return (
    <span
      data-context-label="ordinal"
      className={cn(
        "inline-flex min-w-0 max-w-full items-center text-caption font-medium uppercase tracking-caption text-muted",
        className,
      )}
      {...props}
    >
      <span
        aria-hidden="true"
        className="mr-3 inline-block h-px w-6 shrink-0 bg-current opacity-70"
      />
      <span className="min-w-0 break-words">{children}</span>
    </span>
  );
}
