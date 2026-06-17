import type { ColumnDef } from "@tanstack/react-table";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { getAdminExams } from "@/api/exams";
import { getWrongQuestions } from "@/api/reports";
import { ExamReportFilter } from "@/components/admin/ExamReportFilter";
import { ReportPage } from "@/components/admin/ReportPage";
import { ReportExportButton } from "@/components/admin/ReportExportButton";
import type { WrongQuestionRow } from "@/types/report";

const columns: ColumnDef<WrongQuestionRow>[] = [
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
    accessorKey: "wrong_count",
    header: "WRONG",
    cell: ({ row }) => (
      <span className="font-mono text-sm tabular-nums text-error">{row.original.wrong_count}</span>
    ),
    meta: { mobilePriority: "primary", mobileLabel: "WRONG" },
  },
  {
    accessorKey: "category_1",
    header: "CAT 1",
    cell: ({ row }) => row.original.category_1 ?? "-",
    meta: { mobileLabel: "CAT 1" },
  },
  {
    accessorKey: "category_2",
    header: "CAT 2",
    cell: ({ row }) => row.original.category_2 ?? "-",
    meta: { mobileLabel: "CAT 2" },
  },
];

export function WrongQuestionPage() {
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
      title="错题排行"
      chapterLabel="CHAPTER 04 · REPORTS"
      description="默认按单场考试查看错题排行。优先用于复盘与培训。"
      queryKey={["wrong-questions", selectedExamId]}
      queryFn={() =>
        selectedExamId === undefined ? Promise.resolve([]) : getWrongQuestions(selectedExamId)
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
