import type { ColumnDef } from "@tanstack/react-table";

import { getQuestionAccuracy } from "@/api/reports";
import { ReportPage } from "@/components/admin/ReportPage";
import type { QuestionAccuracyRow } from "@/types/report";

const columns: ColumnDef<QuestionAccuracyRow>[] = [
  {
    accessorKey: "question_id",
    header: "QID",
    cell: ({ row }) => <span className="font-mono text-sm">{row.original.question_id}</span>,
    meta: { mobileLabel: "QID" },
  },
  {
    accessorKey: "stem",
    header: "STEM",
    cell: ({ row }) => <span className="line-clamp-1 max-w-md">{row.original.stem}</span>,
    meta: { mobilePriority: "primary", mobileLabel: "STEM" },
  },
  {
    accessorKey: "correct_count",
    header: "CORRECT",
    cell: ({ row }) => (
      <span className="font-mono text-sm tabular-nums">{row.original.correct_count}</span>
    ),
    meta: { mobileLabel: "CORRECT" },
  },
  {
    accessorKey: "total_count",
    header: "TOTAL",
    cell: ({ row }) => (
      <span className="font-mono text-sm tabular-nums">{row.original.total_count}</span>
    ),
    meta: { mobileLabel: "TOTAL" },
  },
  {
    accessorKey: "accuracy_rate",
    header: "RATE",
    cell: ({ row }) => {
      const rate = row.original.accuracy_rate;
      const pct = rate > 1 ? rate : rate * 100;

      return (
        <span className="font-mono text-sm tabular-nums">{pct.toFixed(pct >= 100 ? 0 : 1)}%</span>
      );
    },
    meta: { mobilePriority: "primary", mobileLabel: "RATE" },
  },
];

export function QuestionAccuracyPage() {
  return (
    <ReportPage
      title="题目正确率"
      chapterLabel="CHAPTER 04 · REPORTS"
      description="每道题被答对的比率。数字越高表示越简单。"
      queryKey="question-accuracy"
      queryFn={getQuestionAccuracy}
      columns={columns}
    />
  );
}
