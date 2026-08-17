import * as React from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface PageStaleNoticeProps extends React.HTMLAttributes<HTMLDivElement> {
  /** The last time the query returned usable data, as a Date, timestamp, or ISO string. */
  lastSuccessfulAt?: Date | number | string;
  /** Re-run the query when the user asks for a fresh result. */
  onRetry?: () => void | Promise<unknown>;
  retrying?: boolean;
  title?: string;
  description?: string;
}

function resolveTimestamp(value: PageStaleNoticeProps["lastSuccessfulAt"]): Date | null {
  if (value === undefined) {
    return null;
  }
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) || date.getTime() <= 0 ? null : date;
}

/**
 * Keep usable cached content visible while making a failed background refresh
 * explicit.  This deliberately has no automatic retry; recovery is always a
 * user action so a broken connection cannot create a request loop.
 */
export function PageStaleNotice({
  lastSuccessfulAt,
  onRetry,
  retrying = false,
  title = "更新失败",
  description = "当前显示上一次成功的数据。",
  className,
  ...props
}: PageStaleNoticeProps) {
  const timestamp = resolveTimestamp(lastSuccessfulAt);

  return (
    <Alert
      variant="warning"
      data-testid="page-stale-warning"
      data-state="stale"
      data-alert-kind="stale"
      aria-live="polite"
      aria-busy={retrying || undefined}
      className={cn("items-start gap-2 sm:flex-row sm:items-center sm:justify-between", className)}
      {...props}
    >
      <div className="flex min-w-0 flex-col gap-1">
        <AlertTitle>{title}</AlertTitle>
        <AlertDescription>
          {description}
          {timestamp ? (
            <time className="ml-1" dateTime={timestamp.toISOString()}>
              上次成功更新于 {timestamp.toLocaleString("zh-CN")}。
            </time>
          ) : null}
        </AlertDescription>
      </div>
      {onRetry ? (
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() => void onRetry()}
          pending={retrying}
          className="shrink-0 self-start sm:self-auto"
        >
          {retrying ? "正在重试" : "重试"}
        </Button>
      ) : null}
    </Alert>
  );
}
