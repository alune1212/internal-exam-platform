import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";

import { getQuestionAccuracy } from "@/api/reports";
import { SimpleDataTable } from "@/components/admin/SimpleDataTable";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { QuestionAccuracyRow } from "@/types/report";

const columns: ColumnDef<QuestionAccuracyRow>[] = [
  { accessorKey: "question_id", header: "题目 ID" },
  { accessorKey: "stem", header: "题干" },
  { accessorKey: "correct_count", header: "正确次数" },
  { accessorKey: "total_count", header: "答题次数" },
  { accessorKey: "accuracy_rate", header: "正确率" },
];

export function QuestionAccuracyPage() {
  const { data = [] } = useQuery({ queryKey: ["question-accuracy"], queryFn: getQuestionAccuracy });

  return (
    <Card>
      <CardHeader>
        <CardTitle>题目正确率</CardTitle>
      </CardHeader>
      <CardContent>
        <SimpleDataTable columns={columns} data={data} />
      </CardContent>
    </Card>
  );
}
