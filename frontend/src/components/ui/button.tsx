import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import type { VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

import { buttonVariants } from "./button-variants";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  /** Prevents a mutation action while preserving a visible busy state. */
  pending?: boolean;
  /** Marks a completed action with an explicit semantic state. */
  success?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant,
      size,
      asChild = false,
      pending = false,
      success = false,
      disabled,
      "aria-busy": ariaBusy,
      "aria-disabled": ariaDisabled,
      ...props
    },
    ref,
  ) => {
    const Comp = asChild ? Slot : "button";
    const resolvedDisabled = disabled || pending;
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        disabled={resolvedDisabled}
        aria-busy={pending ? true : ariaBusy}
        aria-disabled={resolvedDisabled ? true : ariaDisabled}
        data-pending={pending || undefined}
        data-success={success || undefined}
        data-state={pending ? "pending" : success ? "success" : undefined}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";

export { Button };
