import type { ColumnDef } from "@tanstack/react-table";

import { getWrongQuestions } from "@/api/reports";
import { ReportPage } from "@/components/admin/ReportPage";
import { ReportExportButton } from "@/components/admin/ReportExportButton";
import type { WrongQuestionRow } from "@/types/report";

const columns: ColumnDef<WrongQuestionRow>[] = [
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
    accessorKey: "wrong_count",
    header: "WRONG",
    cell: ({ row }) => (
      <span className="font-mono text-sm tabular-nums text-error">{row.original.wrong_count}</span>
    ),
    meta: { mobilePriority: "primary", mobileLabel: "WRONG" },
  },
  {
    accessorKey: "category_1",
    header: "CAT 1",
    cell: ({ row }) => row.original.category_1 ?? "-",
    meta: { mobileLabel: "CAT 1" },
  },
  {
    accessorKey: "category_2",
    header: "CAT 2",
    cell: ({ row }) => row.original.category_2 ?? "-",
    meta: { mobileLabel: "CAT 2" },
  },
];

export function WrongQuestionPage() {
  return (
    <ReportPage
      title="错题排行"
      chapterLabel="CHAPTER 04 · REPORTS"
      description="答错次数最多的题目。优先用于复盘与培训。"
      queryKey="wrong-questions"
      queryFn={getWrongQuestions}
      columns={columns}
      actions={<ReportExportButton />}
    />
  );
}
