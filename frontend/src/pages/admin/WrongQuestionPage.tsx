import type { ColumnDef } from "@tanstack/react-table";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { getAdminExams } from "@/api/exams";
import { getWrongQuestions } from "@/api/reports";
import { ExamReportFilter } from "@/components/admin/ExamReportFilter";
import { ReportPage } from "@/components/admin/ReportPage";
import { ReportExportButton } from "@/components/admin/ReportExportButton";
import { adminPageCopy, adminTableCopy } from "@/lib/pageCopy";
import type { WrongQuestionRow } from "@/types/report";

const columns: ColumnDef<WrongQuestionRow>[] = [
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
    accessorKey: "wrong_count",
    header: adminTableCopy.wrong,
    cell: ({ row }) => (
      <span className="font-mono text-sm tabular-nums text-error">{row.original.wrong_count}</span>
    ),
    meta: { mobilePriority: "primary", mobileLabel: adminTableCopy.wrong },
  },
  {
    accessorKey: "category_1",
    header: adminTableCopy.category1,
    cell: ({ row }) => row.original.category_1 ?? "-",
    meta: { mobileLabel: adminTableCopy.category1 },
  },
  {
    accessorKey: "category_2",
    header: adminTableCopy.category2,
    cell: ({ row }) => row.original.category_2 ?? "-",
    meta: { mobileLabel: adminTableCopy.category2 },
  },
];

export function WrongQuestionPage() {
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
      title="错题排行"
      chapterLabel={adminPageCopy.reports}
      description="默认按单场考试查看错题排行。优先用于复盘与培训。"
      queryKey={[
        "admin",
        "wrong-questions",
        selectedExamId,
        examsLoadError ? "exams-error" : examsPending ? "exams-loading" : "exams-ready",
      ]}
      queryEnabled={!examsPending}
      isLoading={examsPending}
      queryFn={() => {
        if (examsLoadError) {
          throw new Error("考试列表加载失败");
        }
        return getWrongQuestions(selectedExamId ?? null);
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
