import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { useParams } from "react-router-dom";

import { getExamRanking } from "@/api/exams";
import { SimpleDataTable } from "@/components/admin/SimpleDataTable";
import { ChapterNumber } from "@/components/editorial/ChapterNumber";
import { EmptyState } from "@/components/editorial/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
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
  if (row.rank === 1) return "bg-ink text-white hover:bg-ink";
  if (row.rank === 2 || row.rank === 3) return "bg-canvas";
  return undefined;
};

const mobileRowClassName = (row: RankingRow) => {
  if (row.rank === 1) return "border-l-4 border-ink bg-ink text-white";
  if (row.rank === 2) return "border-l-4 border-surface-card bg-surface-card";
  if (row.rank === 3) return "border-l-4 border-ink bg-canvas";
  return "border-l-4 border-hairline bg-canvas";
};

export function RankingPage() {
  const { examId = "1" } = useParams();
  const { data = [], isLoading } = useQuery({
    queryKey: ["ranking", examId],
    queryFn: () => getExamRanking(examId),
  });

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-3">
        <ChapterNumber>CHAPTER 03 · RESULTS</ChapterNumber>
        <h1 className="font-display text-[28px] font-semibold italic tracking-[-0.04em] text-ink lg:text-[40px]">
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
        <SimpleDataTable
          columns={columns}
          data={data}
          rowKey={(row) => row.rank}
          rowClassName={rowClassName}
          mobileRowClassName={mobileRowClassName}
        />
      ) : (
        <EmptyState
          chapter="CHAPTER 03 · RESULTS"
          title="还没有人交卷。"
          description="第一位交卷者将出现在这里。"
        />
      )}
      <p className="text-caption italic text-muted">
        第 1 名整行加黑；2-3 名白底；4+ 名白底 hairline 分割。手机端用左侧色条表达同样差异。
      </p>
    </div>
  );
}
