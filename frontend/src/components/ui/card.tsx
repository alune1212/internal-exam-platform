import * as React from "react";

import { ContextLabel } from "@/components/editorial/ContextLabel";
import { cn } from "@/lib/utils";

type DivProps = React.HTMLAttributes<HTMLDivElement>;
type HeadingProps = React.HTMLAttributes<HTMLHeadingElement>;
type ParaProps = React.HTMLAttributes<HTMLParagraphElement>;

export type CardSurface =
  | "card"
  | "focus"
  | "focus-summary"
  | "summary"
  | "panel"
  | "data"
  | "overlay"
  | "plain";

export interface CardProps extends DivProps {
  /** Governed surface role; `card` remains the compatibility default. */
  surface?: CardSurface;
  /** Alias for surface-oriented call sites. */
  variant?: CardSurface;
}

const surfaceClassName: Record<CardSurface, string> = {
  card: "rounded-lg border border-hairline bg-canvas shadow-card",
  focus: "rounded-lg border border-hairline bg-canvas shadow-card",
  "focus-summary": "rounded-lg border border-hairline bg-canvas shadow-card",
  summary: "rounded-lg border border-hairline bg-canvas shadow-card",
  panel: "rounded-md border border-hairline bg-surface-card",
  data: "rounded-md border border-hairline bg-canvas",
  overlay: "rounded-lg border border-hairline bg-surface-elev shadow-elevate",
  plain: "",
};

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, surface, variant, ...props }, ref) => {
    const resolvedSurface = surface ?? variant ?? "card";

    return (
      <div
        ref={ref}
        className={cn(surfaceClassName[resolvedSurface], "text-ink", className)}
        {...props}
        data-surface-role={resolvedSurface}
        data-surface-owner={resolvedSurface}
      />
    );
  },
);
Card.displayName = "Card";

export interface CardHeaderProps extends DivProps {
  chapter?: React.ReactNode;
  context?: React.ReactNode;
}

export const CardHeader = React.forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ className, chapter, context, children, ...props }, ref) => {
    const resolvedContext = context !== undefined ? context : chapter;

    return (
      <div
        ref={ref}
        data-slot="card-header"
        className={cn("flex flex-col gap-2 border-b border-hairline-soft p-5 lg:p-8", className)}
        {...props}
      >
        {resolvedContext ? (
          <ContextLabel data-slot="card-context">{resolvedContext}</ContextLabel>
        ) : null}
        {children}
      </div>
    );
  },
);
CardHeader.displayName = "CardHeader";

export interface CardTitleProps extends HeadingProps {
  as?: "h2" | "h3" | "h4";
}

export const CardTitle = React.forwardRef<HTMLHeadingElement, CardTitleProps>(
  ({ as: Heading = "h3", className, ...props }, ref) => (
    <Heading
      ref={ref}
      className={cn(
        "min-w-0 break-words font-display text-display-sm font-semibold leading-tight tracking-display-tight text-ink",
        className,
      )}
      {...props}
    />
  ),
);
CardTitle.displayName = "CardTitle";

export const CardDescription = React.forwardRef<HTMLParagraphElement, ParaProps>(
  ({ className, ...props }, ref) => (
    <p
      ref={ref}
      data-slot="card-description"
      className={cn("text-body-sm leading-relaxed", className)}
      {...props}
    />
  ),
);
CardDescription.displayName = "CardDescription";

export const CardContent = React.forwardRef<HTMLDivElement, DivProps>(
  ({ className, ...props }, ref) => (
    <div ref={ref} data-slot="card-content" className={cn("p-5 lg:p-8", className)} {...props} />
  ),
);
CardContent.displayName = "CardContent";

export const CardFooter = React.forwardRef<HTMLDivElement, DivProps>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      data-slot="card-footer"
      className={cn("flex items-center gap-3 border-t border-hairline-soft p-5 lg:p-8", className)}
      {...props}
    />
  ),
);
CardFooter.displayName = "CardFooter";
