import { useQuery } from "@tanstack/react-query";

import { getOperationsSnapshot } from "@/api/operations";
import { PageHeader, PageShell, PageStaleNotice, PageState } from "@/components/page";
import { cn } from "@/lib/utils";
import type { OperationalSignal, OperationalSignalStatus } from "@/types/operations";

const SIGNALS = [
  ["version", "发布版本"],
  ["migration", "数据库迁移"],
  ["service_health", "服务健康"],
  ["worker_health", "自动交卷 Worker"],
  ["operational_lock", "运维写冻结"],
  ["disk_reserve", "磁盘安全水位"],
  ["backup", "本机配对备份"],
  ["second_copy", "独立第二副本"],
  ["restore_drill", "隔离恢复演练"],
  ["retention", "12 个月保留"],
  ["security_scan", "安全扫描"],
] as const;

const STATUS_COPY: Record<OperationalSignalStatus, string> = {
  loading: "加载中",
  current: "当前",
  degraded: "降级",
  stale: "陈旧",
  skipped: "已跳过",
  failed: "失败",
};

const STATUS_TONE: Record<OperationalSignalStatus, string> = {
  loading: "border-hairline text-muted",
  current: "border-success text-success",
  degraded: "border-warning text-warning",
  stale: "border-warning text-warning",
  skipped: "border-hairline text-muted",
  failed: "border-error text-error",
};

function SignalCard({ label, signal }: { label: string; signal: OperationalSignal }) {
  return (
    <article className="flex min-h-44 flex-col gap-4 rounded-lg border border-hairline bg-surface-card p-5 shadow-card">
      <div className="flex items-start justify-between gap-3">
        <h2 className="font-display text-display-sm font-semibold text-ink">{label}</h2>
        <span
          className={cn(
            "rounded-pill border px-2.5 py-1 text-caption font-medium",
            STATUS_TONE[signal.status],
          )}
        >
          {STATUS_COPY[signal.status]}
        </span>
      </div>
      <p className="text-body text-ink">{signal.summary}</p>
      <time className="mt-auto text-caption text-muted" dateTime={signal.checked_at}>
        检查于 {new Date(signal.checked_at).toLocaleString("zh-CN")}
      </time>
    </article>
  );
}

export function OperationsPage() {
  const query = useQuery({
    queryKey: ["admin", "operations", "snapshot"],
    queryFn: getOperationsSnapshot,
    refetchInterval: 30_000,
    retry: false,
  });

  return (
    <PageShell density="workbench" width="full" stagger>
      <PageHeader
        eyebrow="OPERATIONS · 运维"
        title="正式主机状态"
        description="每 30 秒刷新；每个信号独立显示当前、降级、陈旧、跳过或失败。"
      />
      {query.isError && query.data ? (
        <PageStaleNotice
          lastSuccessfulAt={query.dataUpdatedAt}
          onRetry={() => query.refetch()}
          retrying={query.isFetching}
        />
      ) : null}
      {query.isLoading ? <PageState state="loading" rows={4} /> : null}
      {query.isError && !query.data ? (
        <PageState
          state="error"
          title="运维状态加载失败。"
          description="请检查本机操作员入口和后端服务。"
          onRetry={() => void query.refetch()}
        />
      ) : null}
      {query.data ? (
        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" aria-label="运维信号">
          {SIGNALS.map(([key, label]) => (
            <SignalCard key={key} label={label} signal={query.data[key]} />
          ))}
        </section>
      ) : null}
    </PageShell>
  );
}
