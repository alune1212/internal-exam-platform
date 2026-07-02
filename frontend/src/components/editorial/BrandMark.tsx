import * as React from "react";

import { cn } from "@/lib/utils";

export type BrandMarkSize = "sm" | "md";
export type BrandMarkVariant = "light" | "dark";

export interface BrandMarkProps extends React.HTMLAttributes<HTMLSpanElement> {
  size?: BrandMarkSize;
  variant?: BrandMarkVariant;
  tone?: BrandMarkVariant;
}

const sizeClassName: Record<BrandMarkSize, string> = {
  sm: "size-7",
  md: "size-9",
};

export function BrandMark({ size = "md", variant, tone, className, ...props }: BrandMarkProps) {
  const resolvedVariant = variant ?? tone ?? "light";
  const isDark = resolvedVariant === "dark";

  return (
    <span
      aria-hidden="true"
      data-brand-mark=""
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-md",
        sizeClassName[size],
        isDark ? "bg-canvas text-ink" : "bg-ink text-canvas",
        className,
      )}
      {...props}
    >
      <svg viewBox="0 0 64 64" focusable="false" className="size-full">
        <path fill="currentColor" d="M18 17h28v6L29 41h18v6H17v-6l17-18H18v-6Z" />
        <path fill="currentColor" opacity="0.72" d="M17 52h30v3H17z" />
      </svg>
    </span>
  );
}
