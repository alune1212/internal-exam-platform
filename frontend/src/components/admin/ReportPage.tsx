import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import type { QueryKey } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";

import { SimpleDataTable } from "@/components/admin/SimpleDataTable";
import { ChapterNumber } from "@/components/editorial/ChapterNumber";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface ReportPageProps<TData> {
  title: string;
  queryKey: string | QueryKey;
  queryFn: () => Promise<TData[]>;
  columns: ColumnDef<TData>[];
  actions?: ReactNode;
  chapterLabel?: string;
  description?: string;
  rowKey?: (row: TData) => string | number;
  rowClassName?: (row: TData) => string | undefined;
  className?: string;
}

export function ReportPage<TData>({
  title,
  queryKey,
  queryFn,
  columns,
  actions,
  chapterLabel = "CHAPTER · REPORTS",
  description,
  rowKey,
  rowClassName,
  className,
}: ReportPageProps<TData>) {
  const resolvedQueryKey = Array.isArray(queryKey) ? queryKey : [queryKey];
  const { data = [], isLoading } = useQuery({ queryKey: resolvedQueryKey, queryFn });

  return (
    <section data-stagger className={cn("flex flex-col gap-8", className)}>
      <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="flex flex-col gap-3">
          <ChapterNumber>{chapterLabel}</ChapterNumber>
          <h1 className="font-display text-display-lg font-semibold italic tracking-[-0.04em] text-ink lg:text-display-xl">
            {title}
          </h1>
          {description ? <p className="max-w-2xl text-body-lg">{description}</p> : null}
        </div>
        {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
      </header>

      {isLoading ? (
        <div className="flex flex-col gap-3" aria-busy="true">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <p className="text-caption uppercase tracking-[0.16em] text-muted">Loading · 加载中...</p>
        </div>
      ) : (
        <SimpleDataTable
          columns={columns}
          data={data}
          rowKey={rowKey}
          rowClassName={rowClassName}
        />
      )}
    </section>
  );
}
