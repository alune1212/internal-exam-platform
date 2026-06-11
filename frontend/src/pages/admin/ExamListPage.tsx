import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { Link } from "react-router-dom";

import { getAdminExams } from "@/api/exams";
import { SimpleDataTable } from "@/components/admin/SimpleDataTable";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Exam } from "@/types/exam";

const columns: ColumnDef<Exam>[] = [
  { accessorKey: "id", header: "ID" },
  { accessorKey: "title", header: "考试名称" },
  { accessorKey: "duration_minutes", header: "时长" },
  { accessorKey: "status", header: "状态" },
];

export function AdminExamListPage() {
  const { data = [] } = useQuery({ queryKey: ["admin-exams"], queryFn: getAdminExams });

  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <CardTitle>考试配置</CardTitle>
        <Button asChild variant="outline">
          <Link to="/admin/exams/1/edit">编辑示例考试</Link>
        </Button>
      </CardHeader>
      <CardContent>
        <SimpleDataTable columns={columns} data={data} />
      </CardContent>
    </Card>
  );
}
