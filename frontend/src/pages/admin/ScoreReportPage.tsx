import type { ColumnDef } from "@tanstack/react-table";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { getAdminExams } from "@/api/exams";
import { getScoreReport } from "@/api/reports";
import { ExamReportFilter } from "@/components/admin/ExamReportFilter";
import { ReportPage } from "@/components/admin/ReportPage";
import { ReportExportButton } from "@/components/admin/ReportExportButton";
import type { ScoreReportRow } from "@/types/report";

const columns: ColumnDef<ScoreReportRow>[] = [
  {
    accessorKey: "candidate_name",
    header: "NAME",
    cell: ({ row }) => <span className="font-medium">{row.original.candidate_name}</span>,
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
    accessorKey: "exam_title",
    header: "EXAM",
    meta: { mobileLabel: "EXAM" },
  },
  {
    accessorKey: "score",
    header: "SCORE",
    cell: ({ row }) => (
      <span className="font-mono text-sm tabular-nums">
        {row.original.score} / {row.original.total_score}
      </span>
    ),
    meta: { mobilePriority: "primary", mobileLabel: "SCORE" },
  },
  {
    accessorKey: "total_score",
    header: "TOTAL",
    cell: ({ row }) => (
      <span className="font-mono text-sm tabular-nums">{row.original.total_score}</span>
    ),
    meta: { mobilePriority: false },
  },
];

export function ScoreReportPage() {
  const exams = useQuery({ queryKey: ["admin-exams"], queryFn: getAdminExams });
  const [selectedExamId, setSelectedExamId] = useState<string | null | undefined>(undefined);

  useEffect(() => {
    if (selectedExamId !== undefined || !exams.data) {
      return;
    }
    setSelectedExamId(exams.data[0] ? String(exams.data[0].id) : null);
  }, [exams.data, selectedExamId]);

  return (
    <ReportPage
      title="个人成绩"
      chapterLabel="CHAPTER 04 · REPORTS"
      description="默认按单场考试查看个人提交结果，避免正式成绩混场。"
      queryKey={["score-report", selectedExamId]}
      queryFn={() =>
        selectedExamId === undefined ? Promise.resolve([]) : getScoreReport(selectedExamId)
      }
      columns={columns}
      actions={
        <>
          <ExamReportFilter
            exams={exams.data ?? []}
            value={selectedExamId ?? null}
            onChange={setSelectedExamId}
          />
          <ReportExportButton examId={selectedExamId ?? null} />
        </>
      }
    />
  );
}
