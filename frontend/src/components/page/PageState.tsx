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
  rows?: number;
  skeletonVariant?: "default" | "page" | "table" | "card";
  showLoadingCaption?: boolean;
}

const stateTone: Record<PageStateKind, EmptyStateTone> = {
  loading: "default",
  empty: "default",
  error: "error",
  notLoggedIn: "muted",
  notStarted: "muted",
  submitted: "default",
};

export function PageState({
  state,
  eyebrow = state === "error" ? "STATE · 异常状态" : "STATE · 空状态",
  title = state === "error" ? "加载失败" : "暂无内容",
  description = state === "error" ? "请稍后重试。" : "这里还没有可显示的数据。",
  action,
  secondaryAction,
  rows = 4,
  skeletonVariant = "page",
  showLoadingCaption = true,
  className,
  ...props
}: PageStateProps) {
  if (state === "loading") {
    const skeleton = ContentSkeleton({
      rows,
      variant: skeletonVariant,
      showCaption: showLoadingCaption,
      className: cn("rounded-lg border border-hairline bg-canvas shadow-card", className),
    });

    return React.cloneElement(skeleton, {
      ...props,
      role: "status",
      "aria-live": "polite",
      "aria-busy": true,
    });
  }

  return (
    <EmptyState
      chapter={eyebrow}
      title={title}
      description={description}
      action={action}
      secondaryAction={secondaryAction}
      tone={stateTone[state]}
      className={className}
      {...props}
    />
  );
}
