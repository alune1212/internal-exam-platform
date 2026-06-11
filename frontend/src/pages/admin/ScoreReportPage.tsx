import type { ColumnDef } from "@tanstack/react-table";

import { getScoreReport } from "@/api/reports";
import { ReportPage } from "@/components/admin/ReportPage";
import type { ScoreReportRow } from "@/types/report";

const columns: ColumnDef<ScoreReportRow>[] = [
  { accessorKey: "candidate_name", header: "姓名" },
  { accessorKey: "employee_no", header: "员工号" },
  { accessorKey: "department", header: "部门" },
  { accessorKey: "exam_title", header: "考试" },
  { accessorKey: "score", header: "得分" },
  { accessorKey: "total_score", header: "总分" },
];

export function ScoreReportPage() {
  return <ReportPage title="个人成绩" queryKey="score-report" queryFn={getScoreReport} columns={columns} />;
}
