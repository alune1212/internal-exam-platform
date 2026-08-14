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
  /** Alias for callers that describe the same content as page context. */
  context?: React.ReactNode;
  title: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
}

function hasMeaningfulContent(content: React.ReactNode) {
  if (typeof content === "string") {
    return content.trim().length > 0;
  }

  return content !== null && content !== undefined && content !== false;
}

export function PageHeader({
  eyebrow,
  context,
  title,
  description,
  actions,
  className,
  children,
  ...props
}: PageHeaderProps) {
  const contextContent = eyebrow ?? context;

  return (
    <header
      className={cn("flex flex-col gap-4 md:flex-row md:items-end md:justify-between", className)}
      {...props}
    >
      <div className="flex min-w-0 flex-col gap-3">
        {hasMeaningfulContent(contextContent) ? (
          <ContextLabel>{contextContent}</ContextLabel>
        ) : null}
        <h1 className="min-w-0 break-words font-display text-display-lg font-semibold text-ink lg:text-display-xl">
          {title}
        </h1>
        {description ? (
          <p className="max-w-3xl break-words text-body-lg text-muted">{description}</p>
        ) : null}
        {children}
      </div>
      {actions ? <PageActions className="md:justify-end">{actions}</PageActions> : null}
    </header>
  );
}
