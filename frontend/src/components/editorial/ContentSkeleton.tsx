import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface ContentSkeletonProps {
  rows?: number;
  /**
   * When true, renders the bilingual "Loading · 加载中" caption. Most
   * skeletons should stay silent — only enable this when a delayed load
   * needs an explicit affordance.
   */
  showCaption?: boolean;
  className?: string;
}

export function ContentSkeleton({
  rows = 3,
  showCaption = false,
  className,
}: ContentSkeletonProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-busy="true"
      className={cn("flex flex-col gap-3 p-6", className)}
    >
      {Array.from({ length: rows }).map((_, index) => (
        <Skeleton key={index} className={cn("h-4", index % 2 === 0 ? "w-3/4" : "w-1/2")} />
      ))}
      {showCaption ? (
        <p className="mt-2 text-caption font-medium uppercase tracking-[0.16em] text-muted">
          Loading · 加载中
        </p>
      ) : null}
    </div>
  );
}
