import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";

import { getAbsentCandidates } from "@/api/reports";
import { SimpleDataTable } from "@/components/admin/SimpleDataTable";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AbsentCandidateRow } from "@/types/report";

const columns: ColumnDef<AbsentCandidateRow>[] = [
  { accessorKey: "candidate_id", header: "人员 ID" },
  { accessorKey: "name", header: "姓名" },
  { accessorKey: "employee_no", header: "员工号" },
  { accessorKey: "department", header: "部门" },
  { accessorKey: "exam_group", header: "考试分组" },
];

export function AbsentCandidatePage() {
  const { data = [] } = useQuery({ queryKey: ["absent-candidates"], queryFn: getAbsentCandidates });

  return (
    <Card>
      <CardHeader>
        <CardTitle>未参加人员</CardTitle>
      </CardHeader>
      <CardContent>
        <SimpleDataTable columns={columns} data={data} />
      </CardContent>
    </Card>
  );
}
