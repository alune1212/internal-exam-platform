import * as React from "react";

import { cn } from "@/lib/utils";

export type SpinnerProps = React.HTMLAttributes<HTMLSpanElement>;

export const Spinner = React.forwardRef<HTMLSpanElement, SpinnerProps>(
  ({ className, "aria-label": ariaLabel = "加载中", ...props }, ref) => (
    <span
      ref={ref}
      role="status"
      aria-label={ariaLabel}
      className={cn(
        "inline-block size-4 shrink-0 animate-spin rounded-full border-2 border-current border-r-transparent",
        className,
      )}
      {...props}
    />
  ),
);
Spinner.displayName = "Spinner";
