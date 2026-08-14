import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import type { QueryKey } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";

import { SimpleDataTable } from "@/components/admin/SimpleDataTable";
import { PageHeader, PageSection, PageShell, PageStaleNotice, PageState } from "@/components/page";
import { adminPageCopy } from "@/lib/pageCopy";

interface ReportPageProps<TData> {
  title: string;
  queryKey: string | QueryKey;
  queryFn: () => Promise<TData[]>;
  queryEnabled?: boolean;
  isLoading?: boolean;
  /** Refresh prerequisite data before retrying the report query itself. */
  onRetry?: () => void | Promise<unknown>;
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
  queryEnabled = true,
  isLoading = false,
  onRetry,
  columns,
  actions,
  chapterLabel = adminPageCopy.reports,
  description,
  rowKey,
  rowClassName,
  className,
}: ReportPageProps<TData>) {
  const resolvedQueryKey = Array.isArray(queryKey) ? queryKey : [queryKey];
  const query = useQuery({
    queryKey: resolvedQueryKey,
    queryFn,
    enabled: queryEnabled,
    retry: false,
  });
  const showLoading = isLoading || query.isLoading;
  const hasLoadError = query.isError && !query.data;
  const hasStaleError = query.isError && Boolean(query.data);

  const retryQuery = async () => {
    await onRetry?.();
    await query.refetch();
  };

  return (
    <PageShell
      data-testid="report-page-shell"
      density="workbench"
      width="full"
      stagger
      className={className}
    >
      <PageHeader
        eyebrow={chapterLabel}
        title={title}
        description={description}
        actions={actions}
        className="items-start"
      />

      {hasStaleError ? (
        <PageStaleNotice
          lastSuccessfulAt={query.dataUpdatedAt}
          onRetry={retryQuery}
          retrying={query.isFetching}
        />
      ) : null}

      {showLoading ? (
        <PageSection variant="table" data-testid="report-page-table-section">
          <PageState
            state="loading"
            surface="inherit"
            rows={3}
            skeletonVariant="table"
            className="p-0"
          />
        </PageSection>
      ) : hasLoadError ? (
        <PageSection variant="table" data-testid="report-page-table-section">
          <PageState
            state="error"
            surface="inherit"
            eyebrow={adminPageCopy.error}
            title="报表加载失败。"
            description="请稍后重试，或确认后台服务与筛选条件是否可用。"
            onRetry={() => void retryQuery()}
            className="py-10"
          />
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
