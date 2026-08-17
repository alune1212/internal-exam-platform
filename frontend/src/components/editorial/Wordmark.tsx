import * as React from "react";

import { cn } from "@/lib/utils";

import { BrandMark } from "./BrandMark";

export type WordmarkSize = "sm" | "md";
export type WordmarkVariant = "light" | "dark";

export interface WordmarkProps extends React.HTMLAttributes<HTMLDivElement> {
  size?: WordmarkSize;
  variant?: WordmarkVariant;
  tone?: WordmarkVariant;
  subtitle?: string;
  label?: string;
}

const sizeStyles: Record<WordmarkSize, { text: string; subtitle: string }> = {
  sm: {
    text: "text-body-lg",
    subtitle: "text-caption",
  },
  md: {
    text: "text-display-sm",
    subtitle: "text-caption",
  },
};

export function Wordmark({
  size = "md",
  variant,
  tone,
  subtitle,
  label = "知试",
  className,
  ...props
}: WordmarkProps) {
  const resolvedVariant = variant ?? tone ?? "light";
  const styles = sizeStyles[size];
  const isDark = resolvedVariant === "dark";

  return (
    <div className={cn("inline-flex min-w-0 items-center gap-2.5", className)} {...props}>
      <BrandMark size={size} variant={resolvedVariant} />
      <span className="flex min-w-0 flex-col leading-none">
        <span
          className={cn(
            "break-words font-display font-semibold",
            styles.text,
            isDark ? "text-canvas" : "text-ink",
          )}
        >
          {label}
        </span>
        {subtitle ? (
          <span className={cn("mt-1 break-words text-muted", styles.subtitle)}>{subtitle}</span>
        ) : null}
      </span>
    </div>
  );
}
