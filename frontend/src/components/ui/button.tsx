import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  `
    inline-flex items-center justify-center gap-2 whitespace-nowrap
    rounded-pill font-medium
    transition-colors duration-150 ease-out
    focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink
    focus-visible:ring-offset-2 focus-visible:ring-offset-canvas
    active:duration-75 disabled:pointer-events-none
    disabled:opacity-50
    [&_[data-icon="inline-end"]]:-mr-0.5
    [&_[data-icon="inline-start"]]:-ml-0.5
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

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
