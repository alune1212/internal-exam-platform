import * as React from "react";

import { ChapterNumber } from "@/components/editorial/ChapterNumber";
import { cn } from "@/lib/utils";

import { PageActions } from "./PageActions";

export interface PageHeaderProps extends Omit<React.HTMLAttributes<HTMLElement>, "title"> {
  eyebrow: string;
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
        <ChapterNumber>{eyebrow}</ChapterNumber>
        <h1 className="font-display text-display-lg font-semibold text-ink lg:text-display-xl">
          {title}
        </h1>
        {description ? <p className="max-w-3xl text-body text-body-lg">{description}</p> : null}
        {children}
      </div>
      {actions ? <PageActions className="md:justify-end">{actions}</PageActions> : null}
    </header>
  );
}
