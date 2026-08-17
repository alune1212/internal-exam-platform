import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface ContentSkeletonProps {
  rows?: number;
  variant?: "default" | "page" | "table" | "card";
  /**
   * When true, renders the established loading caption. Most skeletons should
   * stay silent — only enable this when a delayed load needs an explicit
   * affordance.
   */
  showCaption?: boolean;
  className?: string;
}

export function ContentSkeleton({
  rows = 3,
  variant = "default",
  showCaption = false,
  className,
}: ContentSkeletonProps) {
  const rowClassName = {
    default: (index: number) => cn("h-4", index % 2 === 0 ? "w-3/4" : "w-1/2"),
    page: (index: number) =>
      cn(index === 0 ? "h-8 w-2/3" : "h-5", index % 2 === 0 ? "w-3/4" : "w-1/2"),
    table: () => "h-12 w-full",
    card: (index: number) => cn("h-5", index % 2 === 0 ? "w-full" : "w-2/3"),
  }[variant];

  return (
    <div
      role="status"
      aria-live="polite"
      aria-busy="true"
      className={cn("flex flex-col gap-3 p-6", className)}
    >
      {Array.from({ length: rows }).map((_, index) => (
        <Skeleton key={index} className={rowClassName(index)} />
      ))}
      {showCaption ? <p className="mt-2 text-caption font-medium text-muted">加载中...</p> : null}
    </div>
  );
}
