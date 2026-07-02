import type { ColumnDef } from "@tanstack/react-table";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { getAdminExams } from "@/api/exams";
import { getQuestionAccuracy } from "@/api/reports";
import { ExamReportFilter } from "@/components/admin/ExamReportFilter";
import { ReportPage } from "@/components/admin/ReportPage";
import { ReportExportButton } from "@/components/admin/ReportExportButton";
import { adminPageCopy, adminTableCopy } from "@/lib/pageCopy";
import type { QuestionAccuracyRow } from "@/types/report";

const columns: ColumnDef<QuestionAccuracyRow>[] = [
  {
    accessorKey: "question_id",
    header: adminTableCopy.questionId,
    cell: ({ row }) => <span className="font-mono text-sm">{row.original.question_id}</span>,
    meta: { mobileLabel: adminTableCopy.questionId },
  },
  {
    accessorKey: "stem",
    header: adminTableCopy.stem,
    cell: ({ row }) => <span className="line-clamp-1 max-w-md">{row.original.stem}</span>,
    meta: { mobilePriority: "primary", mobileLabel: adminTableCopy.stem },
  },
  {
    accessorKey: "correct_count",
    header: adminTableCopy.correct,
    cell: ({ row }) => (
      <span className="font-mono text-sm tabular-nums">{row.original.correct_count}</span>
    ),
    meta: { mobileLabel: adminTableCopy.correct },
  },
  {
    accessorKey: "total_count",
    header: adminTableCopy.totalCount,
    cell: ({ row }) => (
      <span className="font-mono text-sm tabular-nums">{row.original.total_count}</span>
    ),
    meta: { mobileLabel: adminTableCopy.totalCount },
  },
  {
    accessorKey: "accuracy_rate",
    header: adminTableCopy.rate,
    cell: ({ row }) => {
      const rate = row.original.accuracy_rate;
      const pct = rate > 1 ? rate : rate * 100;

      return (
        <span className="font-mono text-sm tabular-nums">{pct.toFixed(pct >= 100 ? 0 : 1)}%</span>
      );
    },
    meta: { mobilePriority: "primary", mobileLabel: adminTableCopy.rate },
  },
];

export function QuestionAccuracyPage() {
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
      title="题目正确率"
      chapterLabel={adminPageCopy.reports}
      description="默认按单场考试查看题目正确率。正确率越高，答对比例越高。"
      queryKey={[
        "admin",
        "question-accuracy",
        selectedExamId,
        examsLoadError ? "exams-error" : examsPending ? "exams-loading" : "exams-ready",
      ]}
      queryEnabled={!examsPending}
      isLoading={examsPending}
      queryFn={() => {
        if (examsLoadError) {
          throw new Error("考试列表加载失败");
        }
        return getQuestionAccuracy(selectedExamId ?? null);
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
