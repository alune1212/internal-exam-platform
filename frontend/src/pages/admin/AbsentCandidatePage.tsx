import type { ColumnDef } from "@tanstack/react-table";

import { getAbsentCandidates } from "@/api/reports";
import { ReportPage } from "@/components/admin/ReportPage";
import type { AbsentCandidateRow } from "@/types/report";

const columns: ColumnDef<AbsentCandidateRow>[] = [
  { accessorKey: "candidate_id", header: "人员 ID" },
  { accessorKey: "name", header: "姓名" },
  { accessorKey: "employee_no", header: "员工号" },
  { accessorKey: "department", header: "部门" },
  { accessorKey: "exam_group", header: "考试分组" },
];

export function AbsentCandidatePage() {
  return (
    <ReportPage
      title="未参加人员"
      queryKey="absent-candidates"
      queryFn={getAbsentCandidates}
      columns={columns}
    />
  );
}
