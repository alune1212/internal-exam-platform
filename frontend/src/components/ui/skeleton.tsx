import * as React from "react";

import { cn } from "@/lib/utils";

export const Skeleton = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      aria-hidden
      className={cn("animate-shimmer rounded-md bg-hairline", className)}
      {...props}
    />
  ),
);
Skeleton.displayName = "Skeleton";
