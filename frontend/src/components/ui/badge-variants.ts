import { cva } from "class-variance-authority";

export const badgeVariants = cva(
  `
    inline-flex items-center gap-1 rounded-sm px-2 py-0.5
    text-caption font-medium uppercase tracking-caption
    transition-colors
  `,
  {
    variants: {
      variant: {
        default: "bg-ink text-canvas",
        outline: "border border-ink bg-canvas text-ink",
        // Muted shares its neutral surface with StatusPill's default so the
        // two chip families look like one continuous "neutral" tier.
        muted: "bg-canvas-warm text-ink",
        info: "border border-ink-blue bg-canvas text-ink-blue",
        pending: "border border-warning-border bg-warning-surface text-status-warning",
        success: "border border-success-border bg-success-surface text-status-success",
        warning: "border border-warning-border bg-warning-surface text-status-warning",
        error: "border border-error-border bg-error-surface text-status-error",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);
