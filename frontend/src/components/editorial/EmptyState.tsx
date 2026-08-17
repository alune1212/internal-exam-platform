import * as React from "react";

import { PageActions } from "@/components/page/PageActions";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import { ContextLabel } from "./ContextLabel";

export type EmptyStateTone = "default" | "error" | "warning" | "success" | "muted";

export interface EmptyStateAction {
  label: string;
  onClick: () => void;
}

export interface EmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Optional meaningful context; page states no longer force an eyebrow. */
  chapter?: React.ReactNode;
  /** Alias for callers that use the shared context vocabulary. */
  context?: React.ReactNode;
  title: string;
  description: string;
  action?: EmptyStateAction;
  secondaryAction?: EmptyStateAction;
  tone?: EmptyStateTone;
}

export function EmptyState({
  chapter,
  context,
  title,
  description,
  action,
  secondaryAction,
  tone = "default",
  className,
  ...props
}: EmptyStateProps) {
  const resolvedContext = context !== undefined ? context : chapter;
  const chapterClassName =
    tone === "error" ? "text-error" : tone === "warning" ? "text-warning" : undefined;

  return (
    <div
      data-state-tone={tone}
      className={cn(
        "mx-auto flex max-w-md flex-col items-center gap-6 py-16 text-center",
        className,
      )}
      {...props}
    >
      {resolvedContext ? (
        <ContextLabel className={chapterClassName}>{resolvedContext}</ContextLabel>
      ) : null}
      <h2 className="min-w-0 break-words font-display text-display-md text-ink">{title}</h2>
      <p className="text-body text-muted">{description}</p>
      {action || secondaryAction ? (
        <PageActions
          aria-label="状态操作"
          align="center"
          placement="card"
          className="justify-center"
        >
          {action ? (
            <Button size="lg" type="button" onClick={action.onClick}>
              {action.label}
            </Button>
          ) : null}
          {secondaryAction ? (
            <Button size="lg" type="button" variant="outline" onClick={secondaryAction.onClick}>
              {secondaryAction.label}
            </Button>
          ) : null}
        </PageActions>
      ) : null}
    </div>
  );
}
