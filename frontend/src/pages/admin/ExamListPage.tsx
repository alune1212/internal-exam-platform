import type { ColumnDef } from "@tanstack/react-table";
import { ArrowUpRight } from "lucide-react";
import { Link } from "react-router-dom";

import { getAdminExams } from "@/api/exams";
import { ReportPage } from "@/components/admin/ReportPage";
import { StatusPill, type StatusPillVariant } from "@/components/editorial/StatusPill";
import { Button } from "@/components/ui/button";
import type { Exam } from "@/types/exam";

function statusVariant(status: string): StatusPillVariant {
  if (status === "active" || status === "live") return "success";
  if (status === "archived" || status === "ended") return "warning";
  return "default";
}

const columns: ColumnDef<Exam>[] = [
  {
    accessorKey: "id",
    header: "ID",
    cell: ({ row }) => <span className="font-mono text-sm">{row.original.id}</span>,
    meta: { mobilePriority: false },
  },
  {
    accessorKey: "title",
    header: "TITLE",
    cell: ({ row }) => (
      <Link
        to={`/admin/exams/${row.original.id}/edit`}
        className="font-medium text-ink underline-offset-4 hover:underline"
      >
        {row.original.title}
      </Link>
    ),
    meta: { mobilePriority: "primary", mobileLabel: "TITLE" },
  },
  {
    accessorKey: "duration_minutes",
    header: "DURATION",
    cell: ({ row }) => (
      <span className="font-mono text-sm tabular-nums">{row.original.duration_minutes} 分</span>
    ),
    meta: { mobileLabel: "DURATION" },
  },
  {
    accessorKey: "status",
    header: "STATUS",
    cell: ({ row }) => (
      <StatusPill variant={statusVariant(row.original.status)}>{row.original.status}</StatusPill>
    ),
    meta: { mobilePriority: "primary", mobileLabel: "STATUS" },
  },
];

export function AdminExamListPage() {
  return (
    <ReportPage
      title="考试配置"
      chapterLabel="CHAPTER 02 · EXAMS"
      description="所有考试的配置入口。点击考试名进入编辑页。"
      queryKey="admin-exams"
      queryFn={getAdminExams}
      columns={columns}
      actions={
        <Button asChild size="sm">
          <Link to="/admin/exams/1/edit">
            新建考试
            <ArrowUpRight data-icon="inline-end" />
          </Link>
        </Button>
      }
    />
  );
}
