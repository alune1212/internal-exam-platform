import * as React from "react";

import { cn } from "@/lib/utils";

export interface ChapterNumberProps extends React.HTMLAttributes<HTMLSpanElement> {
  children: React.ReactNode;
}

export function ChapterNumber({ children, className, ...props }: ChapterNumberProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center text-[11px] uppercase italic tracking-[0.18em] text-muted",
        className,
      )}
      {...props}
    >
      <span aria-hidden="true" className="mr-3">
        ———
      </span>
      <span>{children}</span>
    </span>
  );
}
