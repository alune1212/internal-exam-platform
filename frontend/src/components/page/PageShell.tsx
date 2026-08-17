import * as React from "react";

import { cn } from "@/lib/utils";

export type PageShellDensity = "calm" | "workbench" | "focus";
/**
 * Intentional content-measure roles. Keep the width decision at the page
 * frame rather than repeating a max-width utility in each page.
 *
 * `default` is retained as a compatibility alias for the existing standard
 * frame. `focus` is the full-bleed frame used by active question workspaces.
 */
export type PageShellWidth = "reading" | "standard" | "wide" | "full" | "focus" | "default";

export interface PageShellProps extends React.HTMLAttributes<HTMLDivElement> {
  density?: PageShellDensity;
  width?: PageShellWidth;
  stagger?: boolean;
}

const densityClassName: Record<PageShellDensity, string> = {
  calm: "gap-8 py-page-block",
  workbench: "gap-6 py-page-block",
  focus: "gap-6 py-page-block",
};

const widthClassName: Record<PageShellWidth, string> = {
  reading: "mx-auto w-full max-w-reading",
  standard: "mx-auto w-full max-w-standard",
  wide: "mx-auto w-full max-w-wide",
  full: "mx-auto w-full max-w-full",
  focus: "mx-auto w-full max-w-full",
  default: "mx-auto w-full max-w-standard",
};

const normalizedWidth: Record<PageShellWidth, Exclude<PageShellWidth, "default">> = {
  reading: "reading",
  standard: "standard",
  wide: "wide",
  full: "full",
  focus: "focus",
  default: "standard",
};

export function PageShell({
  density = "calm",
  width = "default",
  stagger = false,
  className,
  children,
  ...props
}: PageShellProps) {
  const allowsOrientationMotion = density === "calm";

  return (
    <div
      data-density={density}
      data-width={normalizedWidth[width]}
      data-stagger={stagger && allowsOrientationMotion ? "" : undefined}
      className={cn(
        "flex min-w-0 flex-col px-page-inline md:px-page-inline-lg",
        densityClassName[density],
        widthClassName[width],
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}
