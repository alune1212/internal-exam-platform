import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { Medal, Sigma, Trophy, Users } from "lucide-react";
import { useParams } from "react-router-dom";

import { getExamRanking } from "@/api/exams";
import { SimpleDataTable } from "@/components/admin/SimpleDataTable";
import { ChapterNumber } from "@/components/editorial/ChapterNumber";
import { EmptyState } from "@/components/editorial/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { RankingRow } from "@/types/exam";

const columns: ColumnDef<RankingRow>[] = [
  {
    accessorKey: "rank",
    header: "RANK",
    cell: ({ row }) => (
      <span className="font-mono text-sm tabular-nums">
        {String(row.original.rank).padStart(2, "0")}
      </span>
    ),
    meta: { mobilePriority: "primary", mobileLabel: "RANK" },
  },
  {
    accessorKey: "candidate_name",
    header: "NAME",
    cell: ({ row }) => <span className="font-medium">{row.original.candidate_name}</span>,
    meta: { mobilePriority: "primary", mobileLabel: "NAME" },
  },
  {
    accessorKey: "department",
    header: "DEPT",
    cell: ({ row }) => row.original.department ?? "-",
    meta: { mobileLabel: "DEPT" },
  },
  {
    accessorKey: "score",
    header: "SCORE",
    cell: ({ row }) => (
      <span className="font-mono text-sm tabular-nums">
        {row.original.score} / {row.original.total_score}
      </span>
    ),
    meta: { mobilePriority: "primary", mobileLabel: "SCORE" },
  },
  {
    accessorKey: "total_score",
    header: "TOTAL",
    cell: ({ row }) => (
      <span className="font-mono text-sm tabular-nums">{row.original.total_score}</span>
    ),
    meta: { mobilePriority: false },
  },
];

const rowClassName = (row: RankingRow) => {
  if (row.rank === 1) return "border-l-4 border-l-ink bg-surface-card";
  if (row.rank === 2 || row.rank === 3) return "border-l-4 border-l-ink-soft bg-canvas-warm";
  return "border-l-4 border-l-hairline";
};

const mobileRowClassName = (row: RankingRow) => {
  if (row.rank === 1) return "border-l-4 border-ink bg-surface-card";
  if (row.rank === 2 || row.rank === 3) return "border-l-4 border-ink-soft bg-canvas-warm";
  return "border-l-4 border-hairline bg-canvas";
};

function formatScore(row?: RankingRow) {
  if (!row) return "-";
  return `${row.score} / ${row.total_score}`;
}

function averageScore(rows: RankingRow[]) {
  if (!rows.length) return "-";
  const total = rows.reduce((sum, row) => sum + row.score, 0);
  return (total / rows.length).toFixed(1);
}

function RankingMetric({
  label,
  value,
  icon: Icon,
  emphasis = false,
}: {
  label: string;
  value: string | number;
  icon: typeof Trophy;
  emphasis?: boolean;
}) {
  return (
    <div
      className={cn(
        "flex items-start justify-between gap-4 rounded-lg border bg-canvas p-4 shadow-card",
        emphasis ? "border-ink" : "border-hairline",
      )}
    >
      <div className="flex flex-col gap-2">
        <span className="text-caption uppercase tracking-[0.16em] text-muted">{label}</span>
        <span className="font-display text-[28px] font-semibold tabular-nums text-ink">
          {value}
        </span>
      </div>
      <Icon className={cn("h-5 w-5", emphasis ? "text-ink" : "text-muted")} aria-hidden="true" />
    </div>
  );
}

function TopRankCard({ row }: { row: RankingRow }) {
  const isFirst = row.rank === 1;
  const isPodium = row.rank <= 3;

  return (
    <article
      className={cn(
        "flex flex-col gap-4 rounded-lg border bg-canvas p-5 shadow-card",
        isFirst ? "border-ink" : "border-hairline",
      )}
    >
      <div className="flex items-center justify-between gap-3">
        <span
          className={cn(
            "font-mono text-caption uppercase tracking-[0.16em]",
            isFirst ? "text-ink-red" : "text-muted",
          )}
        >
          RANK {String(row.rank).padStart(2, "0")}
        </span>
        <Medal
          className={cn(
            "h-5 w-5",
            isFirst ? "fill-ink-red text-ink-red" : isPodium ? "text-ink-soft" : "text-hairline",
          )}
          strokeWidth={isFirst ? 2 : 1.5}
          aria-hidden="true"
        />
      </div>
      <div className="flex flex-col gap-1">
        <h2 className="font-display text-[24px] font-semibold text-ink">{row.candidate_name}</h2>
        <p className="text-body-sm text-muted">{row.department ?? "未填写部门"}</p>
      </div>
      <p className="font-mono text-display-md tabular-nums text-ink">{formatScore(row)}</p>
    </article>
  );
}

export function RankingPage() {
  const { examId = "1" } = useParams();
  const { data = [], isLoading } = useQuery({
    queryKey: ["ranking", examId],
    queryFn: () => getExamRanking(examId),
  });
  const topRows = data.slice(0, 3);
  const leader = data[0];

  return (
    <div data-stagger className="flex flex-col gap-8">
      <header className="flex flex-col gap-3">
        <ChapterNumber>CHAPTER 03 · RESULTS</ChapterNumber>
        <h1 className="font-display text-display-lg font-semibold text-ink lg:text-display-xl">
          谁在这场考试里名列前茅。
        </h1>
      </header>

      {isLoading ? (
        <div className="flex flex-col gap-2" aria-busy="true">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      ) : data.length ? (
        <>
          <section className="flex flex-col gap-4" aria-label="榜单概览">
            <div className="flex items-baseline justify-between gap-4 border-b border-hairline pb-3">
              <h2 className="font-display text-display-md font-semibold text-ink">榜单概览</h2>
              <span className="text-caption uppercase tracking-[0.16em] text-muted">
                {data.length} 人已交卷
              </span>
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              <RankingMetric label="最高分" value={formatScore(leader)} icon={Trophy} emphasis />
              <RankingMetric label="平均分" value={averageScore(data)} icon={Sigma} />
              <RankingMetric label="交卷人数" value={data.length} icon={Users} />
            </div>
          </section>

          <section className="flex flex-col gap-4" aria-label="TOP 3">
            <h2 className="font-display text-display-md font-semibold text-ink">TOP 3</h2>
            <div className="grid gap-4 md:grid-cols-3">
              {topRows.map((row) => (
                <TopRankCard key={row.rank} row={row} />
              ))}
            </div>
          </section>

          <section className="flex flex-col gap-4" aria-label="明细排名">
            <h2 className="font-display text-display-md font-semibold text-ink">明细排名</h2>
            <SimpleDataTable
              columns={columns}
              data={data}
              rowKey={(row) => row.rank}
              rowClassName={rowClassName}
              mobileRowClassName={mobileRowClassName}
            />
          </section>
        </>
      ) : (
        <EmptyState
          chapter="CHAPTER 03 · RESULTS"
          title="还没有人交卷。"
          description="第一位交卷者将出现在这里。"
        />
      )}
    </div>
  );
}
