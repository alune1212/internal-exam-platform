import * as React from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import { ChapterNumber } from "./ChapterNumber";

export type EmptyStateTone = "default" | "error";

export interface EmptyStateAction {
  label: string;
  onClick: () => void;
}

export interface EmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
  chapter: string;
  title: string;
  description: string;
  action?: EmptyStateAction;
  tone?: EmptyStateTone;
}

export function EmptyState({
  chapter,
  title,
  description,
  action,
  tone = "default",
  className,
  ...props
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "mx-auto flex max-w-md flex-col items-center gap-6 py-16 text-center",
        className,
      )}
      {...props}
    >
      <ChapterNumber className={tone === "error" ? "text-error" : undefined}>
        {chapter}
      </ChapterNumber>
      <h2 className="font-display text-display-md italic text-ink">{title}</h2>
      <p className="text-body text-muted">{description}</p>
      {action ? (
        <Button size="lg" type="button" onClick={action.onClick}>
          {action.label}
        </Button>
      ) : null}
    </div>
  );
}
