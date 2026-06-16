import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { cva, type VariantProps } from "class-variance-authority";
import { X } from "lucide-react";

import { cn } from "@/lib/utils";

const Sheet = DialogPrimitive.Root;
const SheetTrigger = DialogPrimitive.Trigger;
const SheetClose = DialogPrimitive.Close;
const SheetPortal = DialogPrimitive.Portal;

const SheetOverlay = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Overlay>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Overlay
    ref={ref}
    className={cn(
      "fixed inset-0 z-50 bg-overlay backdrop-blur-[2px]",
      "data-[state=open]:animate-in data-[state=closed]:animate-out",
      "data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
      className,
    )}
    {...props}
  />
));
SheetOverlay.displayName = DialogPrimitive.Overlay.displayName;

const sheetVariants = cva(
  `
    fixed z-50 gap-4 bg-surface-elev shadow-pop
    transition-transform duration-200
    ease-out
    data-[state=open]:animate-in data-[state=closed]:animate-out
  `,
  {
    variants: {
      side: {
        top: `
          inset-x-0 top-0 border-b border-hairline
          data-[state=closed]:slide-out-to-top data-[state=open]:slide-in-from-top
        `,
        bottom: `
          inset-x-0 bottom-0 rounded-t-2xl border-t border-hairline
          data-[state=closed]:slide-out-to-bottom data-[state=open]:slide-in-from-bottom
        `,
        left: `
          inset-y-0 left-0 h-full w-3/4 max-w-sm border-r border-hairline
          data-[state=closed]:slide-out-to-left data-[state=open]:slide-in-from-left
        `,
        right: `
          inset-y-0 right-0 h-full w-3/4 max-w-sm border-l border-hairline
          data-[state=closed]:slide-out-to-right data-[state=open]:slide-in-from-right
        `,
      },
    },
    defaultVariants: { side: "bottom" },
  },
);

export type SheetOverlayProps = React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>;

export interface SheetContentProps
  extends
    React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content>,
    VariantProps<typeof sheetVariants> {}

const SheetContent = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Content>,
  SheetContentProps
>(({ className, side, children, ...props }, ref) => (
  <SheetPortal>
    <SheetOverlay />
    <DialogPrimitive.Content
      ref={ref}
      className={cn(sheetVariants({ side }), "p-6", className)}
      {...props}
    >
      {children}
      <DialogPrimitive.Close
        aria-label="关闭"
        className={cn(
          `absolute right-4 top-4 inline-flex size-8 items-center justify-center rounded-pill text-muted transition-colors hover:bg-surface-card hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink`,
        )}
      >
        <X data-icon="inline-end" className="size-4" aria-hidden />
      </DialogPrimitive.Close>
    </DialogPrimitive.Content>
  </SheetPortal>
));
SheetContent.displayName = DialogPrimitive.Content.displayName;

export interface SheetHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  chapter?: string;
}
export type SheetTitleProps = React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>;
export type SheetDescriptionProps = React.ComponentPropsWithoutRef<
  typeof DialogPrimitive.Description
>;

const SheetHeader = React.forwardRef<HTMLDivElement, SheetHeaderProps>(
  ({ className, chapter, children, ...props }, ref) => (
    <div ref={ref} className={cn("flex flex-col gap-2 text-left", className)} {...props}>
      {chapter ? (
        <span className="text-caption font-medium uppercase tracking-[0.16em] text-muted">
          {chapter}
        </span>
      ) : null}
      {children}
    </div>
  ),
);
SheetHeader.displayName = "SheetHeader";

const SheetTitle = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Title>,
  SheetTitleProps
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Title
    ref={ref}
    className={cn(
      "font-display text-display-sm font-semibold leading-tight tracking-[-0.02em] text-ink",
      className,
    )}
    {...props}
  />
));
SheetTitle.displayName = DialogPrimitive.Title.displayName;

const SheetDescription = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Description>,
  SheetDescriptionProps
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Description
    ref={ref}
    className={cn("text-body-sm leading-relaxed", className)}
    {...props}
  />
));
SheetDescription.displayName = DialogPrimitive.Description.displayName;

export { Sheet, SheetTrigger, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetClose };
