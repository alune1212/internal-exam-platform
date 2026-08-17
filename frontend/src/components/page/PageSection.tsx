import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * Governed section surfaces. `card` and `table` remain compatibility aliases
 * for existing consumers; new composition can name the intended role
 * directly (`focus`, `summary`, `data`, or `overlay`).
 */
export type PageSectionVariant =
  | "plain"
  | "panel"
  | "focus"
  | "focus-summary"
  | "summary"
  | "data"
  | "overlay"
  | "card"
  | "table";

export interface PageSectionProps extends React.HTMLAttributes<HTMLElement> {
  variant?: PageSectionVariant;
  /** Alias for callers that describe the surface rather than its shape. */
  surface?: PageSectionVariant;
}

const variantClassName: Record<PageSectionVariant, string> = {
  plain: "flex flex-col gap-stack",
  panel: "flex flex-col gap-stack rounded-md border border-hairline bg-surface-card p-panel",
  focus:
    "flex flex-col gap-section rounded-lg border border-hairline bg-canvas p-panel shadow-card",
  "focus-summary":
    "flex flex-col gap-section rounded-lg border border-hairline bg-canvas p-panel shadow-card",
  summary:
    "flex flex-col gap-section rounded-lg border border-hairline bg-canvas p-panel shadow-card",
  data: "flex flex-col gap-stack overflow-hidden rounded-md border border-hairline bg-canvas",
  overlay:
    "flex flex-col gap-stack rounded-lg border border-hairline bg-surface-elev p-panel shadow-elevate",
  // Compatibility names retain their established visual contract while
  // callers migrate to the explicit role names above.
  card: "flex flex-col gap-5 rounded-lg border border-hairline bg-canvas p-6 shadow-card lg:p-7",
  table: "overflow-hidden rounded-lg border border-hairline bg-canvas shadow-card",
};

export function PageSection({
  variant = "plain",
  surface,
  className,
  children,
  ...props
}: PageSectionProps) {
  const resolvedVariant = surface ?? variant;

  return (
    <section
      {...props}
      data-surface-role={resolvedVariant}
      data-surface-owner={resolvedVariant === "plain" ? undefined : resolvedVariant}
      className={cn(variantClassName[resolvedVariant], className)}
    >
      {children}
    </section>
  );
}
