import * as React from "react";

import { cn } from "@/lib/utils";

export type WordmarkSize = "sm" | "md";
export type WordmarkVariant = "light" | "dark";

export interface WordmarkProps extends React.HTMLAttributes<HTMLDivElement> {
  size?: WordmarkSize;
  variant?: WordmarkVariant;
  tone?: WordmarkVariant;
  subtitle?: string;
  label?: string;
}

const sizeStyles: Record<WordmarkSize, { circle: string; text: string; subtitle: string }> = {
  sm: {
    circle: "size-7 text-[12px]",
    text: "text-[18px]",
    subtitle: "text-[11px]",
  },
  md: {
    circle: "size-9 text-[14px]",
    text: "text-[24px]",
    subtitle: "text-[11px]",
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
    <div className={cn("inline-flex items-center gap-2.5", className)} {...props}>
      <span
        aria-hidden="true"
        className={cn(
          "inline-flex shrink-0 items-center justify-center rounded-full font-display font-semibold",
          styles.circle,
          isDark ? "bg-canvas text-ink" : "bg-ink text-canvas",
        )}
      >
        Z
      </span>
      <span className="flex flex-col leading-none">
        <span
          className={cn(
            "font-display font-semibold",
            styles.text,
            isDark ? "text-canvas" : "text-ink",
          )}
        >
          {label}
        </span>
        {subtitle ? (
          <span className={cn("mt-1 italic text-muted", styles.subtitle)}>{subtitle}</span>
        ) : null}
      </span>
    </div>
  );
}
