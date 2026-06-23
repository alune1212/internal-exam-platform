import * as React from "react";

import { cn } from "@/lib/utils";

export type PageSectionVariant = "plain" | "card" | "panel" | "table";

export interface PageSectionProps extends React.HTMLAttributes<HTMLElement> {
  variant?: PageSectionVariant;
}

const variantClassName: Record<PageSectionVariant, string> = {
  plain: "flex flex-col gap-4",
  card: "flex flex-col gap-5 rounded-lg border border-hairline bg-canvas p-6 shadow-card lg:p-7",
  panel: "flex flex-col gap-5 rounded-md border border-hairline bg-surface-card p-5 lg:p-6",
  table: "overflow-hidden rounded-lg border border-hairline bg-canvas shadow-card",
};

export function PageSection({
  variant = "plain",
  className,
  children,
  ...props
}: PageSectionProps) {
  return (
    <section className={cn(variantClassName[variant], className)} {...props}>
      {children}
    </section>
  );
}
