import type { ColumnDef } from "@tanstack/react-table";

import { getScoreReport } from "@/api/reports";
import { ReportPage } from "@/components/admin/ReportPage";
import type { ScoreReportRow } from "@/types/report";

const columns: ColumnDef<ScoreReportRow>[] = [
  {
    accessorKey: "candidate_name",
    header: "NAME",
    cell: ({ row }) => <span className="font-medium">{row.original.candidate_name}</span>,
    meta: { mobilePriority: "primary", mobileLabel: "NAME" },
  },
  {
    accessorKey: "employee_no",
    header: "EMP NO",
    cell: ({ row }) => <span className="font-mono text-sm">{row.original.employee_no ?? "-"}</span>,
    meta: { mobileLabel: "EMP NO" },
  },
  {
    accessorKey: "department",
    header: "DEPT",
    cell: ({ row }) => row.original.department ?? "-",
    meta: { mobileLabel: "DEPT" },
  },
  {
    accessorKey: "exam_title",
    header: "EXAM",
    meta: { mobileLabel: "EXAM" },
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

export function ScoreReportPage() {
  return (
    <ReportPage
      title="个人成绩"
      chapterLabel="CHAPTER 04 · REPORTS"
      description="每次考试的个人提交结果。"
      queryKey="score-report"
      queryFn={getScoreReport}
      columns={columns}
    />
  );
}
