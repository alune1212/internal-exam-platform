import type { ColumnDef } from "@tanstack/react-table";

import { getAbsentCandidates } from "@/api/reports";
import { ReportPage } from "@/components/admin/ReportPage";
import type { AbsentCandidateRow } from "@/types/report";

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
];

export function AbsentCandidatePage() {
  return (
    <ReportPage
      title="未参加人员"
      chapterLabel="CHAPTER 04 · REPORTS"
      description="应考但未提交考试的人员列表。需补考时使用。"
      queryKey="absent-candidates"
      queryFn={getAbsentCandidates}
      columns={columns}
    />
  );
}
