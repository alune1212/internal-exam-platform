import type { ColumnDef } from "@tanstack/react-table";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { getAdminExams } from "@/api/exams";
import { getAbsentCandidates, type AttendanceStatus } from "@/api/reports";
import { ExamReportFilter } from "@/components/admin/ExamReportFilter";
import { ReportPage } from "@/components/admin/ReportPage";
import { ReportExportButton } from "@/components/admin/ReportExportButton";
import { Button } from "@/components/ui/button";
import {
  adminPageCopy,
  adminPageText,
  adminTableCopy,
  formatAttemptStatusShort,
} from "@/lib/pageCopy";
import { cn } from "@/lib/utils";
import type { AbsentCandidateRow } from "@/types/report";

const statusLabels: Record<AttendanceStatus, string> = {
  not_started: formatAttemptStatusShort("not_started"),
  in_progress: formatAttemptStatusShort("in_progress"),
  submitted: formatAttemptStatusShort("submitted"),
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
    header: "ROSTER NAME · 名单姓名",
    cell: ({ row }) => <span className="font-medium">{row.original.roster_name}</span>,
    meta: { mobilePriority: "primary", mobileLabel: "名单姓名" },
  },
  {
    accessorKey: "roster_email",
    header: "ROSTER EMAIL · 名单邮箱",
    cell: ({ row }) => <span className="font-mono text-sm">{row.original.roster_email}</span>,
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
    cell: ({ row }) => statusLabels[row.original.attendance_status],
    meta: { mobileLabel: adminTableCopy.status },
  },
];

export function AbsentCandidatePage() {
  const [status, setStatus] = useState<AttendanceStatus>("not_started");
  const [selectedExamId, setSelectedExamId] = useState<string | null>(null);
  const exams = useQuery({ queryKey: ["admin", "exams"], queryFn: getAdminExams });

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
      actions={
        <>
          {exams.data ? (
            <ExamReportFilter
              exams={exams.data}
              value={selectedExamId}
              onChange={setSelectedExamId}
            />
          ) : null}
          <div className="inline-flex items-center gap-1 rounded-pill border border-hairline bg-canvas p-1">
            {(["not_started", "in_progress", "submitted"] as AttendanceStatus[]).map((item) => (
              <Button
                key={item}
                type="button"
                variant="ghost"
                size="sm"
                className={cn(
                  "rounded-pill",
                  status === item ? "bg-ink text-canvas hover:bg-ink" : "text-muted",
                )}
                aria-pressed={status === item}
                onClick={() => setStatus(item)}
              >
                {statusLabels[item]}
              </Button>
            ))}
          </div>
          <ReportExportButton examId={selectedExamId} />
        </>
      }
    />
  );
}
