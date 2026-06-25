import type { ColumnDef } from "@tanstack/react-table";
import { useState } from "react";

import { getAbsentCandidates, type AttendanceStatus } from "@/api/reports";
import { ReportPage } from "@/components/admin/ReportPage";
import { ReportExportButton } from "@/components/admin/ReportExportButton";
import { Button } from "@/components/ui/button";
import { adminPageCopy } from "@/lib/pageCopy";
import { cn } from "@/lib/utils";
import type { AbsentCandidateRow } from "@/types/report";

const statusLabels: Record<AttendanceStatus, string> = {
  not_started: "未开始",
  in_progress: "进行中",
  submitted: "已提交",
};

const columns: ColumnDef<AbsentCandidateRow>[] = [
  {
    accessorKey: "candidate_id",
    header: "CID",
    cell: ({ row }) => <span className="font-mono text-sm">{row.original.candidate_id}</span>,
    meta: { mobilePriority: false },
  },
  {
    accessorKey: "name",
    header: "NAME",
    cell: ({ row }) => <span className="font-medium">{row.original.name}</span>,
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
    accessorKey: "exam_group",
    header: "GROUP",
    cell: ({ row }) => row.original.exam_group ?? "-",
    meta: { mobilePriority: "primary", mobileLabel: "GROUP" },
  },
  {
    accessorKey: "attendance_status",
    header: "STATUS",
    cell: ({ row }) => statusLabels[row.original.attendance_status],
    meta: { mobileLabel: "STATUS" },
  },
];

export function AbsentCandidatePage() {
  const [status, setStatus] = useState<AttendanceStatus>("not_started");

  return (
    <ReportPage
      title="参考状态"
      chapterLabel={adminPageCopy.reports}
      description="按未开始、进行中、已提交拆分应考人员状态，避免把进行中考试计为缺考。"
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
