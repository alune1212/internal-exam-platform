import type { ColumnDef } from "@tanstack/react-table";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { getAdminExams } from "@/api/exams";
import { getScoreReport } from "@/api/reports";
import { ExamReportFilter } from "@/components/admin/ExamReportFilter";
import { ReportPage } from "@/components/admin/ReportPage";
import { ReportExportButton } from "@/components/admin/ReportExportButton";
import { adminPageCopy, adminTableCopy } from "@/lib/pageCopy";
import type { ScoreReportRow } from "@/types/report";

const columns: ColumnDef<ScoreReportRow>[] = [
  {
    accessorKey: "candidate_name",
    header: adminTableCopy.name,
    cell: ({ row }) => <span className="font-medium">{row.original.candidate_name}</span>,
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
    accessorKey: "exam_title",
    header: adminTableCopy.exam,
    meta: { mobileLabel: adminTableCopy.exam },
  },
  {
    accessorKey: "score",
    header: adminTableCopy.score,
    cell: ({ row }) => (
      <span className="font-mono text-sm tabular-nums">
        {row.original.score} / {row.original.total_score}
      </span>
    ),
    meta: { mobilePriority: "primary", mobileLabel: adminTableCopy.score },
  },
  {
    accessorKey: "total_score",
    header: adminTableCopy.totalScore,
    cell: ({ row }) => (
      <span className="font-mono text-sm tabular-nums">{row.original.total_score}</span>
    ),
    meta: { mobilePriority: false },
  },
];

export function ScoreReportPage() {
  const exams = useQuery({ queryKey: ["admin", "exams"], queryFn: getAdminExams });
  const [selectedExamId, setSelectedExamId] = useState<string | null | undefined>(undefined);
  const examsLoadError = exams.isError && !exams.data;
  const examsPending = selectedExamId === undefined && !examsLoadError;

  useEffect(() => {
    if (selectedExamId !== undefined || !exams.data) {
      return;
    }
    setSelectedExamId(exams.data[0] ? String(exams.data[0].id) : null);
  }, [exams.data, selectedExamId]);

  return (
    <ReportPage
      title="个人成绩"
      chapterLabel={adminPageCopy.reports}
      description="默认按单场考试查看个人交卷结果，避免正式成绩混场。"
      queryKey={[
        "admin",
        "score-report",
        selectedExamId,
        examsLoadError ? "exams-error" : examsPending ? "exams-loading" : "exams-ready",
      ]}
      queryEnabled={!examsPending}
      isLoading={examsPending}
      queryFn={() => {
        if (examsLoadError) {
          throw new Error("考试列表加载失败");
        }
        return getScoreReport(selectedExamId ?? null);
      }}
      columns={columns}
      actions={
        examsLoadError || examsPending ? null : (
          <>
            <ExamReportFilter
              exams={exams.data ?? []}
              value={selectedExamId ?? null}
              onChange={setSelectedExamId}
            />
            <ReportExportButton examId={selectedExamId ?? null} />
          </>
        )
      }
    />
  );
}
