import type { ColumnDef } from "@tanstack/react-table";
import { useState } from "react";

import { getAbsentCandidates, type AttendanceStatus } from "@/api/reports";
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
    accessorKey: "name",
    header: adminTableCopy.name,
    cell: ({ row }) => <span className="font-medium">{row.original.name}</span>,
    meta: { mobilePriority: "primary", mobileLabel: adminTableCopy.name },
  },
  {
    accessorKey: "employee_no",
    header: adminTableCopy.employeeNo,
    cell: ({ row }) => <span className="font-mono text-sm">{row.original.employee_no ?? "-"}</span>,
    meta: { mobileLabel: adminTableCopy.employeeNo },
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

  return (
    <ReportPage
      title={adminPageText.reports.attendance.title}
      chapterLabel={adminPageCopy.reports}
      description={adminPageText.reports.attendance.description}
      queryKey={["admin", "absent-candidates", status]}
      queryFn={() => getAbsentCandidates(status)}
      columns={columns}
      actions={
        <>
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
          <ReportExportButton />
        </>
      }
    />
  );
}
