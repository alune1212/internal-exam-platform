import type { ColumnDef } from "@tanstack/react-table";

import { getQuestionAccuracy } from "@/api/reports";
import { ReportPage } from "@/components/admin/ReportPage";
import type { QuestionAccuracyRow } from "@/types/report";

const columns: ColumnDef<QuestionAccuracyRow>[] = [
  { accessorKey: "question_id", header: "题目 ID" },
  { accessorKey: "stem", header: "题干" },
  { accessorKey: "correct_count", header: "正确次数" },
  { accessorKey: "total_count", header: "答题次数" },
  { accessorKey: "accuracy_rate", header: "正确率" },
];

export function QuestionAccuracyPage() {
  return (
    <ReportPage
      title="题目正确率"
      queryKey="question-accuracy"
      queryFn={getQuestionAccuracy}
      columns={columns}
    />
  );
}
