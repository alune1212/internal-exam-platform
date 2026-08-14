import * as React from "react";

import { cn } from "@/lib/utils";

export interface ChapterNumberProps extends React.HTMLAttributes<HTMLSpanElement> {
  children: React.ReactNode;
}

export function ChapterNumber({ children, className, ...props }: ChapterNumberProps) {
  return (
    <span
      className={cn(
        "inline-flex min-w-0 max-w-full items-center text-caption font-medium uppercase tracking-[0.18em] text-muted",
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
