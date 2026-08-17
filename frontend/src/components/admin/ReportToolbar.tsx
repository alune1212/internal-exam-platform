import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/utils";

export interface ReportToolbarProps extends HTMLAttributes<HTMLDivElement> {
  /** Primary report filters, kept first in both desktop and mobile order. */
  filters?: ReactNode;
  /** Optional segmented or view-state controls. */
  segments?: ReactNode;
  /** Non-actionable feedback associated with the current report controls. */
  notice?: ReactNode;
  /** Export and other report actions, kept last in both layouts. */
  actions?: ReactNode;
}

function hasContent(value: ReactNode): boolean {
  return value !== null && value !== undefined && value !== false;
}

/**
 * Shared report control order. The toolbar intentionally owns reflow only;
 * filters, segments, notices, and actions retain their native semantics.
 */
export function ReportToolbar({
  filters,
  segments,
  notice,
  actions,
  className,
  ...props
}: ReportToolbarProps) {
  if (![filters, segments, notice, actions].some(hasContent)) {
    return null;
  }

  return (
    <div
      {...props}
      data-report-toolbar=""
      data-report-order="filters-segments-notice-actions"
      role="group"
      aria-label={props["aria-label"] ?? "报表筛选与操作"}
      className={cn(
        "flex min-w-0 flex-col gap-3 border-b border-hairline-soft pb-4",
        "lg:flex-row lg:flex-wrap lg:items-end lg:gap-4",
        className,
      )}
    >
      {hasContent(filters) ? (
        <div
          data-report-toolbar-slot="filters"
          className="flex min-w-0 flex-1 flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end"
        >
          {filters}
        </div>
      ) : null}
      {hasContent(segments) ? (
        <div data-report-toolbar-slot="segments" className="flex min-w-0 flex-wrap items-end gap-2">
          {segments}
        </div>
      ) : null}
      {hasContent(notice) ? (
        <div data-report-toolbar-slot="notice" className="min-w-0 flex-1 break-words">
          {notice}
        </div>
      ) : null}
      {hasContent(actions) ? (
        <div
          data-report-toolbar-slot="actions"
          className="flex min-w-0 flex-wrap items-end gap-2 [&>*]:min-w-0 [&>*]:max-w-full"
        >
          {actions}
        </div>
      ) : null}
    </div>
  );
}
