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
  title: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  className,
  children,
  ...props
}: PageHeaderProps) {
  return (
    <header
      className={cn("flex flex-col gap-4 md:flex-row md:items-end md:justify-between", className)}
      {...props}
    >
      <div className="flex min-w-0 flex-col gap-3">
        {eyebrow ? <ContextLabel>{eyebrow}</ContextLabel> : null}
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
