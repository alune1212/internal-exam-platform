import type { ColumnDef } from "@tanstack/react-table";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { getAdminExams } from "@/api/exams";
import { getAbsentCandidates, type AttendanceStatus } from "@/api/reports";
import { ExamReportFilter } from "@/components/admin/ExamReportFilter";
import { ReportPage } from "@/components/admin/ReportPage";
import { ReportExportButton } from "@/components/admin/ReportExportButton";
import { ReportToolbar } from "@/components/admin/ReportToolbar";
import { StatusPill, type StatusPillVariant } from "@/components/editorial/StatusPill";
import { Button } from "@/components/ui/button";
import {
  adminPageCopy,
  adminPageText,
  adminTableCopy,
  formatAttemptStatus,
} from "@/lib/pageCopy";
import { adminKeys } from "@/lib/queryKeys";
import type { AbsentCandidateRow } from "@/types/report";

const statusLabels: Record<AttendanceStatus, string> = {
  not_started: formatAttemptStatus("not_started"),
  in_progress: formatAttemptStatus("in_progress"),
  submitted: formatAttemptStatus("submitted"),
};

const statusVariants: Record<AttendanceStatus, StatusPillVariant> = {
  not_started: "pending",
  in_progress: "warning",
  submitted: "success",
};

const columns: ColumnDef<AbsentCandidateRow>[] = [
  {
    accessorKey: "candidate_id",
    header: adminTableCopy.candidateId,
    cell: ({ row }) => <span className="font-mono text-sm">{row.original.candidate_id}</span>,
    meta: { mobilePriority: false },
  },
  {
    accessorKey: "roster_name",
    header: "名单姓名",
    cell: ({ row }) => (
      <span className="min-w-0 break-words font-medium">{row.original.roster_name}</span>
    ),
    meta: { mobilePriority: "primary", mobileLabel: "名单姓名" },
  },
  {
    accessorKey: "roster_email",
    header: "名单邮箱",
    cell: ({ row }) => (
      <span className="min-w-0 break-words font-mono text-body-sm">
        {row.original.roster_email}
      </span>
    ),
    meta: { mobileLabel: "名单邮箱" },
  },
  {
    accessorKey: "department",
    header: adminTableCopy.department,
    cell: ({ row }) => row.original.department ?? "-",
    meta: { mobileLabel: adminTableCopy.department },
  },
  {
    accessorKey: "exam_group",
    header: adminTableCopy.group,
    cell: ({ row }) => row.original.exam_group ?? "-",
    meta: { mobilePriority: "primary", mobileLabel: adminTableCopy.group },
  },
  {
    accessorKey: "attendance_status",
    header: adminTableCopy.status,
    cell: ({ row }) => (
      <StatusPill variant={statusVariants[row.original.attendance_status]}>
        {statusLabels[row.original.attendance_status]}
      </StatusPill>
    ),
    meta: { mobileLabel: adminTableCopy.status },
  },
];

export function AbsentCandidatePage() {
  const [status, setStatus] = useState<AttendanceStatus>("not_started");
  const [selectedExamId, setSelectedExamId] = useState<string | null>(null);
  const exams = useQuery({ queryKey: adminKeys.exams(), queryFn: getAdminExams });

  return (
    <ReportPage
      title={adminPageText.reports.attendance.title}
      chapterLabel={adminPageCopy.reports}
      description={adminPageText.reports.attendance.description}
      queryKey={["admin", "absent-candidates", status, selectedExamId]}
      onRetry={() => exams.refetch()}
      queryFn={() =>
        selectedExamId ? getAbsentCandidates(status, selectedExamId) : getAbsentCandidates(status)
      }
      columns={columns}
      toolbar={
        <ReportToolbar
          filters={
            exams.data ? (
              <ExamReportFilter
                exams={exams.data}
                value={selectedExamId}
                onChange={setSelectedExamId}
              />
            ) : null
          }
          segments={
            <>
              {(["not_started", "in_progress", "submitted"] as AttendanceStatus[]).map((item) => (
                <Button
                  key={item}
                  type="button"
                  variant={status === item ? "default" : "ghost"}
                  size="sm"
                  aria-pressed={status === item}
                  onClick={() => setStatus(item)}
                >
                  {statusLabels[item]}
                </Button>
              ))}
            </>
          }
          actions={<ReportExportButton examId={selectedExamId} />}
        />
      }
    />
  );
}
