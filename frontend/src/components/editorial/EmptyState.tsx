import * as React from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import { ChapterNumber } from "./ChapterNumber";

export type EmptyStateTone = "default" | "error" | "muted";

export interface EmptyStateAction {
  label: string;
  onClick: () => void;
}

export interface EmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
  chapter: string;
  title: string;
  description: string;
  action?: EmptyStateAction;
  secondaryAction?: EmptyStateAction;
  tone?: EmptyStateTone;
}

export function EmptyState({
  chapter,
  title,
  description,
  action,
  secondaryAction,
  tone = "default",
  className,
  ...props
}: EmptyStateProps) {
  const chapterClassName = tone === "error" ? "text-error" : undefined;

  return (
    <div
      className={cn(
        "mx-auto flex max-w-md flex-col items-center gap-6 py-16 text-center",
        className,
      )}
      {...props}
    >
      <ChapterNumber className={chapterClassName}>{chapter}</ChapterNumber>
      <h2 className="font-display text-display-md text-ink">{title}</h2>
      <p className="text-body text-muted">{description}</p>
      {action || secondaryAction ? (
        <div className="flex flex-wrap justify-center gap-3">
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
        </div>
      ) : null}
    </div>
  );
}
