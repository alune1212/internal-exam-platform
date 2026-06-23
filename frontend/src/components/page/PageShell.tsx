import * as React from "react";

import { cn } from "@/lib/utils";

export type PageShellDensity = "calm" | "workbench" | "focus";
export type PageShellWidth = "default" | "wide" | "full";

export interface PageShellProps extends React.HTMLAttributes<HTMLDivElement> {
  density?: PageShellDensity;
  width?: PageShellWidth;
  stagger?: boolean;
}

const densityClassName: Record<PageShellDensity, string> = {
  calm: "gap-8",
  workbench: "gap-6",
  focus: "gap-6",
};

const widthClassName: Record<PageShellWidth, string> = {
  default: "mx-auto w-full max-w-6xl",
  wide: "mx-auto w-full max-w-7xl",
  full: "w-full",
};

export function PageShell({
  density = "calm",
  width = "default",
  stagger = false,
  className,
  children,
  ...props
}: PageShellProps) {
  return (
    <div
      data-stagger={stagger ? "" : undefined}
      className={cn("flex flex-col", densityClassName[density], widthClassName[width], className)}
      {...props}
    >
      {children}
    </div>
  );
}
