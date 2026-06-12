import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { getActiveExams } from "@/api/exams";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function ExamListPage() {
  const { data = [], isLoading } = useQuery({
    queryKey: ["active-exams"],
    queryFn: getActiveExams,
  });

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-2xl font-semibold">可参加考试</h2>
        <p className="text-muted-foreground">正式考试开始后倒计时持续运行，暂存不暂停考试。</p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {data.length ? (
          data.map((exam) => (
            <Card key={exam.id}>
              <CardHeader>
                <CardTitle>{exam.title}</CardTitle>
                <CardDescription>{exam.duration_minutes} 分钟</CardDescription>
              </CardHeader>
              <CardContent>
                <Button asChild>
                  <Link to={`/exams/${exam.id}/start`}>进入考试说明</Link>
                </Button>
              </CardContent>
            </Card>
          ))
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>{isLoading ? "正在加载" : "暂无可参加考试"}</CardTitle>
              <CardDescription>管理员发布 active 考试后会显示在这里。</CardDescription>
            </CardHeader>
          </Card>
        )}
      </div>
    </div>
  );
}
