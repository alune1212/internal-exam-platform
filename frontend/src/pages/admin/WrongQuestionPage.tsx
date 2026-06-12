import type { ColumnDef } from "@tanstack/react-table";

import { getWrongQuestions } from "@/api/reports";
import { ReportPage } from "@/components/admin/ReportPage";
import type { WrongQuestionRow } from "@/types/report";

const columns: ColumnDef<WrongQuestionRow>[] = [
  { accessorKey: "question_id", header: "题目 ID" },
  { accessorKey: "stem", header: "题干" },
  { accessorKey: "wrong_count", header: "错误次数" },
  { accessorKey: "category_1", header: "一级分类" },
  { accessorKey: "category_2", header: "二级分类" },
];

export function WrongQuestionPage() {
  return (
    <ReportPage
      title="错题排行"
      queryKey="wrong-questions"
      queryFn={getWrongQuestions}
      columns={columns}
    />
  );
}
