import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import type { QueryKey } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";

import { SimpleDataTable } from "@/components/admin/SimpleDataTable";
import { ContentSkeleton } from "@/components/editorial/ContentSkeleton";
import { PageHeader, PageSection, PageShell } from "@/components/page";
import { adminPageCopy } from "@/lib/pageCopy";

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
  chapterLabel = adminPageCopy.reports,
  description,
  rowKey,
  rowClassName,
  className,
}: ReportPageProps<TData>) {
  const resolvedQueryKey = Array.isArray(queryKey) ? queryKey : [queryKey];
  const query = useQuery({ queryKey: resolvedQueryKey, queryFn });

  return (
    <PageShell
      data-testid="report-page-shell"
      density="workbench"
      width="full"
      className={className}
    >
      <PageHeader
        eyebrow={chapterLabel}
        title={title}
        description={description}
        actions={actions}
        className="items-start"
      />

      {query.isLoading ? (
        <PageSection variant="table" data-testid="report-page-table-section">
          <ContentSkeleton rows={3} showCaption variant="table" className="p-0" />
        </PageSection>
      ) : (
        <PageSection variant="table" data-testid="report-page-table-section">
          <SimpleDataTable
            columns={columns}
            data={query.data ?? []}
            rowKey={rowKey}
            rowClassName={rowClassName}
          />
        </PageSection>
      )}
    </PageShell>
  );
}
