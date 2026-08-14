import { cva } from "class-variance-authority";

export const buttonVariants = cva(
  `
    inline-flex items-center justify-center gap-2 whitespace-nowrap
    rounded-pill font-medium
    transition-[background-color,border-color,box-shadow,color,opacity] duration-fast ease-standard
    focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink
    focus-visible:ring-offset-2 focus-visible:ring-offset-canvas
    active:duration-instant disabled:pointer-events-none
    disabled:opacity-50
    data-[pending]:pointer-events-none data-[pending]:cursor-wait data-[success]:border-success
    data-[success]:text-success data-[pending]:opacity-70
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
        `,
        outline: `
          border border-ink bg-canvas text-ink
          hover:bg-canvas-warm
        `,
        ghost: `
          bg-transparent text-ink
          hover:bg-surface-card
        `,
        link: `
          bg-transparent text-ink underline underline-offset-4
          hover:text-ink-soft
        `,
      },
      size: {
        sm: "h-9 px-4 text-[13px]",
        default: "h-11 px-6 text-sm",
        lg: "h-12 px-8 text-[15px]",
        icon: "size-9 p-0",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);
