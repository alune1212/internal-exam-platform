import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { useParams } from "react-router-dom";

import { getExamRanking } from "@/api/exams";
import { SimpleDataTable } from "@/components/admin/SimpleDataTable";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { RankingRow } from "@/types/exam";

const columns: ColumnDef<RankingRow>[] = [
  { accessorKey: "rank", header: "排名" },
  { accessorKey: "candidate_name", header: "姓名" },
  { accessorKey: "department", header: "部门" },
  { accessorKey: "score", header: "得分" },
  { accessorKey: "total_score", header: "总分" },
];

export function RankingPage() {
  const { examId = "1" } = useParams();
  const { data = [] } = useQuery({
    queryKey: ["ranking", examId],
    queryFn: () => getExamRanking(examId),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>成绩排名</CardTitle>
      </CardHeader>
      <CardContent>
        <SimpleDataTable columns={columns} data={data} />
      </CardContent>
    </Card>
  );
}
