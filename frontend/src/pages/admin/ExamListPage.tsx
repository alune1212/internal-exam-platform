import type { ColumnDef } from "@tanstack/react-table";
import { Plus } from "lucide-react";
import { Link } from "react-router-dom";
import { useNavigate } from "react-router-dom";
import { useState } from "react";

import { getErrorMessage } from "@/api/client";
import { createAdminExam, getAdminExams } from "@/api/exams";
import { ReportPage } from "@/components/admin/ReportPage";
import { StatusPill, type StatusPillVariant } from "@/components/editorial/StatusPill";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  adminPageCopy,
  adminPageText,
  adminTableCopy,
  formatExamAvailability,
  formatExamStatus,
} from "@/lib/pageCopy";
import type { Exam } from "@/types/exam";

function statusVariant(status: string): StatusPillVariant {
  if (status === "active" || status === "live") return "success";
  if (status === "archived" || status === "ended") return "warning";
  return "default";
}

function formatDateTime(value?: string | null) {
  if (!value) {
    return "未设置";
  }
  return new Date(value).toLocaleString();
}

function availabilityLabel(status?: Exam["availability_status"]) {
  return formatExamAvailability(status);
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
    header: adminTableCopy.title,
    cell: ({ row }) => (
      <Link
        to={`/admin/exams/${row.original.id}`}
        className="font-medium text-ink underline-offset-4 hover:underline"
      >
        {row.original.title}
      </Link>
    ),
    meta: { mobilePriority: "primary", mobileLabel: adminTableCopy.title },
  },
  {
    accessorKey: "duration_minutes",
    header: adminTableCopy.duration,
    cell: ({ row }) => (
      <span className="font-mono text-sm tabular-nums">{row.original.duration_minutes} 分</span>
    ),
    meta: { mobileLabel: adminTableCopy.duration },
  },
  {
    accessorKey: "status",
    header: adminTableCopy.status,
    cell: ({ row }) => (
      <StatusPill variant={statusVariant(row.original.status)}>
        {formatExamStatus(row.original.status)}
      </StatusPill>
    ),
    meta: { mobilePriority: "primary", mobileLabel: adminTableCopy.status },
  },
  {
    id: "availability",
    header: adminTableCopy.openWindow,
    cell: ({ row }) => (
      <div className="flex flex-col gap-1 text-body-sm">
        <span>{availabilityLabel(row.original.availability_status)}</span>
        <span className="text-caption text-muted">
          {formatDateTime(row.original.available_from)} -{" "}
          {formatDateTime(row.original.available_until)}
        </span>
      </div>
    ),
    meta: { mobileLabel: adminTableCopy.openWindow },
  },
  {
    id: "question_pool",
    header: adminTableCopy.questionPool,
    cell: ({ row }) => {
      const count = row.original.question_pool_count ?? 0;
      const frozen = row.original.status === "active" || count > 0;
      return (
        <div className="flex flex-col gap-1">
          <StatusPill variant={frozen ? "success" : "default"}>
            {frozen ? "已冻结" : "未冻结"}
          </StatusPill>
          <span className="text-caption text-muted">题池 {count}</span>
        </div>
      );
    },
    meta: { mobileLabel: adminTableCopy.questionPool },
  },
];

export function AdminExamListPage() {
  const navigate = useNavigate();
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const handleCreate = async () => {
    setIsCreating(true);
    setCreateError(null);
    try {
      const exam = await createAdminExam();
      navigate(`/admin/exams/${exam.id}/edit`);
    } catch (error) {
      setCreateError(getErrorMessage(error, "创建考试失败"));
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <ReportPage
        title={adminPageText.exams.title}
        chapterLabel={adminPageCopy.exams}
        description={adminPageText.exams.description}
        queryKey={["admin", "exams"]}
        queryFn={getAdminExams}
        columns={columns}
        actions={
          <Button type="button" size="sm" disabled={isCreating} onClick={() => void handleCreate()}>
            <Plus data-icon="inline-start" />
            {isCreating ? "创建中" : "新建考试"}
          </Button>
        }
      />
      {createError ? (
        <Alert variant="error">
          <AlertDescription>{createError}</AlertDescription>
        </Alert>
      ) : null}
    </div>
  );
}
