import type { ColumnDef } from "@tanstack/react-table";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { getAdminExams } from "@/api/exams";
import { getQuestionAccuracy } from "@/api/reports";
import { ExamReportFilter } from "@/components/admin/ExamReportFilter";
import { ReportPage } from "@/components/admin/ReportPage";
import { ReportExportButton } from "@/components/admin/ReportExportButton";
import { adminPageCopy } from "@/lib/pageCopy";
import type { QuestionAccuracyRow } from "@/types/report";

const columns: ColumnDef<QuestionAccuracyRow>[] = [
  {
    accessorKey: "question_id",
    header: "QID",
    cell: ({ row }) => <span className="font-mono text-sm">{row.original.question_id}</span>,
    meta: { mobileLabel: "QID" },
  },
  {
    accessorKey: "stem",
    header: "STEM",
    cell: ({ row }) => <span className="line-clamp-1 max-w-md">{row.original.stem}</span>,
    meta: { mobilePriority: "primary", mobileLabel: "STEM" },
  },
  {
    accessorKey: "correct_count",
    header: "CORRECT",
    cell: ({ row }) => (
      <span className="font-mono text-sm tabular-nums">{row.original.correct_count}</span>
    ),
    meta: { mobileLabel: "CORRECT" },
  },
  {
    accessorKey: "total_count",
    header: "TOTAL",
    cell: ({ row }) => (
      <span className="font-mono text-sm tabular-nums">{row.original.total_count}</span>
    ),
    meta: { mobileLabel: "TOTAL" },
  },
  {
    accessorKey: "accuracy_rate",
    header: "RATE",
    cell: ({ row }) => {
      const rate = row.original.accuracy_rate;
      const pct = rate > 1 ? rate : rate * 100;

      return (
        <span className="font-mono text-sm tabular-nums">{pct.toFixed(pct >= 100 ? 0 : 1)}%</span>
      );
    },
    meta: { mobilePriority: "primary", mobileLabel: "RATE" },
  },
];

export function QuestionAccuracyPage() {
  const exams = useQuery({ queryKey: ["admin", "exams"], queryFn: getAdminExams });
  const [selectedExamId, setSelectedExamId] = useState<string | null | undefined>(undefined);

  useEffect(() => {
    if (selectedExamId !== undefined || !exams.data) {
      return;
    }
    setSelectedExamId(exams.data[0] ? String(exams.data[0].id) : null);
  }, [exams.data, selectedExamId]);

  return (
    <ReportPage
      title="题目正确率"
      chapterLabel={adminPageCopy.reports}
      description="默认按单场考试查看题目正确率。数字越高表示越简单。"
      queryKey={["admin", "question-accuracy", selectedExamId]}
      queryFn={() =>
        selectedExamId === undefined ? Promise.resolve([]) : getQuestionAccuracy(selectedExamId)
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
