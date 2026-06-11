import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { Link } from "react-router-dom";

import { getAdminQuestions } from "@/api/questions";
import { SimpleDataTable } from "@/components/admin/SimpleDataTable";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Question } from "@/types/question";

const columns: ColumnDef<Question>[] = [
  { accessorKey: "id", header: "ID" },
  { accessorKey: "question_type", header: "题型" },
  { accessorKey: "stem", header: "题干" },
  { accessorKey: "score", header: "分值" },
  { accessorKey: "status", header: "状态" },
];

export function QuestionListPage() {
  const { data = [] } = useQuery({ queryKey: ["admin-questions"], queryFn: getAdminQuestions });

  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <CardTitle>题库管理</CardTitle>
        <Button asChild variant="outline">
          <Link to="/admin/questions/import">导入题库 Excel</Link>
        </Button>
      </CardHeader>
      <CardContent>
        <SimpleDataTable columns={columns} data={data} />
      </CardContent>
    </Card>
  );
}
