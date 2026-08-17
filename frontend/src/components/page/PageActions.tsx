import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * Shared action placement contracts. The placement is intentionally a
 * semantic hint rather than a second button component: callers keep using
 * the existing Button (or a link), while this owner controls alignment and
 * narrow-viewport reflow for the action region.
 */
export type PageActionPlacement =
  | "page"
  | "auth"
  | "header"
  | "card"
  | "form"
  | "report"
  | "destructive";

export type PageActionReflow = "wrap" | "stack";
export type PageActionAlign = "start" | "center" | "end" | "between";

export interface PageActionsProps extends React.HTMLAttributes<HTMLDivElement> {
  "aria-label"?: string;
  /** Where the action group lives in the page composition. */
  placement?: PageActionPlacement;
  /** How actions should lay out below the small-screen breakpoint. */
  reflow?: PageActionReflow;
  /** Horizontal alignment once the group has room to breathe. */
  align?: PageActionAlign;
}

export function PageActions({
  className,
  children,
  "aria-label": ariaLabel = "页面操作",
  placement = "page",
  reflow = placement === "auth" ? "stack" : "wrap",
  align = placement === "header" || placement === "destructive" ? "end" : "start",
  ...props
}: PageActionsProps) {
  const hasRenderableChildren = React.Children.toArray(children).length > 0;

  if (!hasRenderableChildren) {
    return null;
  }

  const placementClassName: Record<PageActionPlacement, string> = {
    page: "",
    auth: "w-full sm:justify-end [&>*]:w-full sm:[&>*]:w-auto",
    header: "justify-start sm:justify-end",
    card: "",
    form: "justify-start sm:justify-end [&>*]:w-full sm:[&>*]:w-auto",
    report: "",
    destructive: "justify-start sm:justify-end [&>*]:w-full sm:[&>*]:w-auto",
  };
  const alignClassName: Record<PageActionAlign, string> = {
    start: "justify-start",
    center: "justify-center",
    end: "justify-end",
    between: "justify-between",
  };

  return (
    <div
      role="group"
      aria-label={ariaLabel}
      data-action-group={placement}
      data-action-placement={placement}
      data-action-reflow={reflow}
      className={cn(
        "flex items-center gap-control-gap",
        reflow === "stack" ? "flex-col sm:flex-row" : "flex-wrap",
        alignClassName[align],
        placementClassName[placement],
        // Every child may shrink or wrap with the group. The action label
        // itself stays intact; the parent is what reflows on mobile.
        "[&>*]:min-w-0 [&>*]:whitespace-nowrap",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

/** Semantic alias for consumers that name the pattern rather than its page use. */
export const ActionGroup = PageActions;
export type ActionGroupProps = PageActionsProps;
