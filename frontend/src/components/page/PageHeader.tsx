import * as React from "react";

import { ContextLabel } from "@/components/editorial/ContextLabel";
import { cn } from "@/lib/utils";

import { PageActions } from "./PageActions";

export interface PageHeaderProps extends Omit<React.HTMLAttributes<HTMLElement>, "title"> {
  /**
   * Optional route/workflow context. Keep this label meaningful; when omitted
   * the header renders the title without an empty editorial marker.
   */
  eyebrow?: React.ReactNode;
  /** Preferred name for the optional route/workflow context. */
  context?: React.ReactNode;
  /** Explicit alias for callers that name the rendered label. */
  contextLabel?: React.ReactNode;
  title: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
}

function hasMeaningfulContent(value: React.ReactNode): boolean {
  if (value === null || value === undefined || typeof value === "boolean") return false;
  if (typeof value === "string") return value.trim().length > 0;
  if (Array.isArray(value)) return value.some(hasMeaningfulContent);
  return true;
}

export function PageHeader({
  eyebrow,
  context,
  contextLabel,
  title,
  description,
  actions,
  className,
  children,
  ...props
}: PageHeaderProps) {
  const resolvedContext =
    contextLabel !== undefined ? contextLabel : context !== undefined ? context : eyebrow;

  return (
    <header
      data-page-header=""
      className={cn("flex flex-col gap-4 md:flex-row md:items-end md:justify-between", className)}
      {...props}
    >
      <div className="flex min-w-0 flex-col gap-3">
        {hasMeaningfulContent(resolvedContext) ? (
          <ContextLabel data-page-context="">{resolvedContext}</ContextLabel>
        ) : null}
        <h1 className="min-w-0 break-words font-display text-display-lg font-semibold text-ink lg:text-display-xl">
          {title}
        </h1>
        {description ? (
          <p className="max-w-3xl break-words text-body-lg text-muted">{description}</p>
        ) : null}
        {children}
      </div>
      {actions ? (
        <PageActions placement="header" className="md:justify-end">
          {actions}
        </PageActions>
      ) : null}
    </header>
  );
}
