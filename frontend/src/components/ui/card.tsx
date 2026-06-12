import * as React from "react";

import { cn } from "@/lib/utils";

type DivProps = React.HTMLAttributes<HTMLDivElement>;
type HeadingProps = React.HTMLAttributes<HTMLHeadingElement>;
type ParaProps = React.HTMLAttributes<HTMLParagraphElement>;

export const Card = React.forwardRef<HTMLDivElement, DivProps>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("rounded-lg border border-hairline bg-canvas text-ink shadow-card", className)}
    {...props}
  />
));
Card.displayName = "Card";

export interface CardHeaderProps extends DivProps {
  chapter?: string;
}

export const CardHeader = React.forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ className, chapter, children, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("flex flex-col gap-2 border-b border-hairline-soft p-5 lg:p-8", className)}
      {...props}
    >
      {chapter ? (
        <span
          data-slot="card-chapter"
          className="text-caption font-medium uppercase tracking-[0.16em] text-muted"
        >
          {chapter}
        </span>
      ) : null}
      {children}
    </div>
  ),
);
CardHeader.displayName = "CardHeader";

export const CardTitle = React.forwardRef<HTMLHeadingElement, HeadingProps>(
  ({ className, ...props }, ref) => (
    <h3
      ref={ref}
      className={cn(
        "font-display text-[22px] font-semibold leading-tight tracking-[-0.02em] text-ink lg:text-display-sm",
        className,
      )}
      {...props}
    />
  ),
);
CardTitle.displayName = "CardTitle";

export const CardDescription = React.forwardRef<HTMLParagraphElement, ParaProps>(
  ({ className, ...props }, ref) => (
    <p ref={ref} className={cn("text-body text-body-sm leading-relaxed", className)} {...props} />
  ),
);
CardDescription.displayName = "CardDescription";

export const CardContent = React.forwardRef<HTMLDivElement, DivProps>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("p-5 lg:p-8", className)} {...props} />
  ),
);
CardContent.displayName = "CardContent";

export const CardFooter = React.forwardRef<HTMLDivElement, DivProps>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("flex items-center gap-3 border-t border-hairline-soft p-5 lg:p-8", className)}
      {...props}
    />
  ),
);
CardFooter.displayName = "CardFooter";
