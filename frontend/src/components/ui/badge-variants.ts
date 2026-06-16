import { cva } from "class-variance-authority";

export const badgeVariants = cva(
  `
    inline-flex items-center gap-1 rounded-sm px-2 py-0.5
    text-[11px] font-medium uppercase tracking-[0.16em]
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
        success: "border border-success bg-canvas text-success",
        warning: "border border-warning bg-canvas text-warning",
        error: "border border-error bg-canvas text-error",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);
