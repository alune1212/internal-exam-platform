import type { ColumnDef } from "@tanstack/react-table";
import { ArrowUpRight } from "lucide-react";
import { Link } from "react-router-dom";

import { getAdminQuestions } from "@/api/questions";
import { ReportPage } from "@/components/admin/ReportPage";
import { Button } from "@/components/ui/button";
import type { Question } from "@/types/question";

const columns: ColumnDef<Question>[] = [
  {
    accessorKey: "id",
    header: "ID",
    cell: ({ row }) => <span className="font-mono text-sm">{row.original.id}</span>,
    meta: { mobilePriority: false },
  },
  {
    accessorKey: "question_type",
    header: "TYPE",
    meta: { mobileLabel: "TYPE" },
  },
  {
    accessorKey: "stem",
    header: "STEM",
    cell: ({ row }) => <span className="line-clamp-1 max-w-md">{row.original.stem}</span>,
    meta: { mobilePriority: "primary", mobileLabel: "STEM" },
  },
  {
    accessorKey: "score",
    header: "SCORE",
    cell: ({ row }) => <span className="font-mono text-sm tabular-nums">{row.original.score}</span>,
    meta: { mobileLabel: "SCORE" },
  },
  {
    accessorKey: "status",
    header: "STATUS",
    meta: { mobileLabel: "STATUS" },
  },
];

export function QuestionListPage() {
  return (
    <ReportPage
      title="题库管理"
      chapterLabel="CHAPTER 03 · LIBRARY"
      description="所有题目的列表与状态。点击右上「导入题库」批量上传 Excel。"
      queryKey="admin-questions"
      queryFn={getAdminQuestions}
      columns={columns}
      actions={
        <Button asChild size="sm">
          <Link to="/admin/questions/import">
            导入题库
            <ArrowUpRight data-icon="inline-end" />
          </Link>
        </Button>
      }
    />
  );
}
