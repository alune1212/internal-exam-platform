import * as React from "react";

import {
  EmptyState,
  type EmptyStateAction,
  type EmptyStateTone,
} from "@/components/editorial/EmptyState";
import { ContentSkeleton } from "@/components/editorial/ContentSkeleton";
import { cn } from "@/lib/utils";

export type PageStateKind =
  | "loading"
  | "empty"
  | "error"
  | "notLoggedIn"
  | "notStarted"
  | "submitted";

export interface PageStateProps extends React.HTMLAttributes<HTMLDivElement> {
  state: PageStateKind;
  eyebrow?: string;
  title?: string;
  description?: string;
  action?: EmptyStateAction;
  secondaryAction?: EmptyStateAction;
  /** Convenience action for recoverable first-load failures. */
  onRetry?: () => void;
  retryLabel?: string;
  rows?: number;
  skeletonVariant?: "default" | "page" | "table" | "card";
  showLoadingCaption?: boolean;
  /**
   * Use `inherit` when the state is already contained by a PageSection. This
   * keeps the parent as the only border/background/shadow owner.
   */
  surface?: "standalone" | "inherit";
}

const stateTone: Record<PageStateKind, EmptyStateTone> = {
  loading: "default",
  empty: "default",
  error: "error",
  notLoggedIn: "muted",
  notStarted: "muted",
  submitted: "default",
};

const defaultStateCopy: Record<
  Exclude<PageStateKind, "loading">,
  { title: string; description: string }
> = {
  empty: { title: "暂无内容", description: "这里还没有可显示的数据。" },
  error: { title: "加载失败", description: "请稍后重试。" },
  notLoggedIn: { title: "请先登录", description: "登录后才能继续当前操作。" },
  notStarted: { title: "尚未开始", description: "当前内容还没有开始。" },
  submitted: { title: "已提交", description: "这项操作已经完成。" },
};

export function PageState({
  state,
  eyebrow,
  title,
  description,
  action,
  secondaryAction,
  onRetry,
  retryLabel = "重试",
  rows = 4,
  skeletonVariant = "page",
  showLoadingCaption = true,
  surface = "standalone",
  className,
  ...props
}: PageStateProps) {
  if (state === "loading") {
    const skeleton = ContentSkeleton({
      rows,
      variant: skeletonVariant,
      showCaption: showLoadingCaption,
      className: cn(
        surface === "standalone"
          ? "rounded-lg border border-hairline bg-canvas shadow-card"
          : "bg-transparent",
        className,
      ),
    });

    return React.cloneElement(skeleton, {
      ...props,
      "data-state-surface": surface,
      role: "status",
      "aria-live": "polite",
      "aria-busy": true,
      "data-page-state": state,
      "data-state-kind": state,
      "data-color-independent": "true",
    });
  }

  const defaults = defaultStateCopy[state];
  const resolvedAction = action ?? (onRetry ? { label: retryLabel, onClick: onRetry } : undefined);

  return (
    <EmptyState
      chapter={eyebrow}
      title={title ?? defaults.title}
      description={description ?? defaults.description}
      action={resolvedAction}
      secondaryAction={secondaryAction}
      tone={stateTone[state]}
      className={cn(surface === "inherit" && "bg-transparent", className)}
      data-page-state={state}
      data-state-kind={state}
      data-color-independent="true"
      data-state-surface={surface}
      {...props}
    />
  );
}
