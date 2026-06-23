import * as React from "react";

import { cn } from "@/lib/utils";

export interface PageActionsProps extends React.HTMLAttributes<HTMLDivElement> {
  "aria-label"?: string;
}

export function PageActions({
  className,
  children,
  "aria-label": ariaLabel = "页面操作",
  ...props
}: PageActionsProps) {
  const hasRenderableChildren = React.Children.toArray(children).length > 0;

  if (!hasRenderableChildren) {
    return null;
  }

  return (
    <div
      role="group"
      aria-label={ariaLabel}
      className={cn("flex flex-wrap items-center gap-2", className)}
      {...props}
    >
      {children}
    </div>
  );
}
