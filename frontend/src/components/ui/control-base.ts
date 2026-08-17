import { cn } from "@/lib/utils";

/**
 * Shared native-control contract. Input, select, and textarea intentionally
 * share state, focus, and validation treatment; their size/surface differences
 * live in the small variant map below rather than in three drifting strings.
 */
export const controlBaseClasses =
  "w-full rounded-md border border-hairline text-body-sm text-ink outline-none transition-[border-color,background-color,box-shadow,color] duration-fast ease-standard placeholder:text-muted hover:border-ink-soft focus-visible:border-ink focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-offset-2 focus-visible:ring-offset-canvas disabled:cursor-not-allowed disabled:opacity-50 aria-[invalid=true]:border-error data-[invalid]:border-error data-[success]:border-success data-[state=success]:border-success";

export type ControlVariant = "input" | "select" | "textarea";

/**
 * Multiline controls retain a warm paper surface and resize affordance. The
 * other variants remain native one-line controls so browser keyboard and
 * mobile picker behavior is unchanged.
 */
export const controlVariantClasses: Record<ControlVariant, string> = {
  input:
    "flex h-11 bg-canvas px-control-x file:border-0 file:bg-transparent file:text-body-sm file:font-medium",
  select: "flex h-11 bg-canvas px-control-x",
  textarea: "min-h-32 resize-y bg-canvas-warm px-4 py-3 leading-relaxed",
};

export function controlClasses(variant: ControlVariant, className?: string) {
  return cn(controlBaseClasses, controlVariantClasses[variant], className);
}
