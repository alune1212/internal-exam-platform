import { cva } from "class-variance-authority";

export const buttonVariants = cva(
  `
    inline-flex items-center justify-center gap-2 whitespace-nowrap
    rounded-pill font-medium
    transition-[background-color,border-color,box-shadow,color,opacity] duration-fast ease-standard
    focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink
    focus-visible:ring-offset-2 focus-visible:ring-offset-canvas
    active:shadow-inner active:duration-instant
    disabled:pointer-events-none
    disabled:opacity-50
    aria-[pressed=true]:shadow-inner
    data-[pending]:pointer-events-none data-[pending]:cursor-wait data-[pending]:opacity-70
    [&_[data-icon="inline-end"]]:-mr-0.5
    [&_[data-icon="inline-start"]]:-ml-0.5
    [&_[data-icon]]:size-4
    [&_[data-icon]]:shrink-0
  `,
  {
    variants: {
      variant: {
        default: `
          bg-ink text-canvas
          hover:bg-footer
          aria-[pressed=true]:bg-footer
          data-[success]:bg-success-action data-[success]:text-success-action-foreground
          data-[success]:hover:bg-success-action-hover
        `,
        outline: `
          border border-ink bg-canvas text-ink
          hover:bg-canvas-warm
          aria-[pressed=true]:bg-surface-card
          data-[success]:border-success-border data-[success]:bg-success-surface data-[success]:text-success
          data-[success]:hover:bg-success-surface
        `,
        ghost: `
          bg-transparent text-ink
          hover:bg-surface-card
          aria-[pressed=true]:bg-surface-card
          data-[success]:bg-success-surface data-[success]:text-success
          data-[success]:hover:bg-success-surface
        `,
        link: `
          bg-transparent text-ink underline underline-offset-4
          hover:text-ink-soft
          aria-[pressed=true]:text-ink-soft
          data-[success]:text-success data-[success]:hover:text-success
        `,
      },
      size: {
        sm: "h-9 px-4 text-body-sm",
        default: "h-11 px-6 text-sm",
        lg: "h-12 px-8 text-body",
        icon: "size-9 p-0",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);
