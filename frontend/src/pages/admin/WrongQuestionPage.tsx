import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";

import { getWrongQuestions } from "@/api/reports";
import { SimpleDataTable } from "@/components/admin/SimpleDataTable";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { WrongQuestionRow } from "@/types/report";

const columns: ColumnDef<WrongQuestionRow>[] = [
  { accessorKey: "question_id", header: "题目 ID" },
  { accessorKey: "stem", header: "题干" },
  { accessorKey: "wrong_count", header: "错误次数" },
  { accessorKey: "category_1", header: "一级分类" },
  { accessorKey: "category_2", header: "二级分类" },
];

export function WrongQuestionPage() {
  const { data = [] } = useQuery({ queryKey: ["wrong-questions"], queryFn: getWrongQuestions });

  return (
    <Card>
      <CardHeader>
        <CardTitle>错题排行</CardTitle>
      </CardHeader>
      <CardContent>
        <SimpleDataTable columns={columns} data={data} />
      </CardContent>
    </Card>
  );
}
