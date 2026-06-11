import { Link, useParams } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function ExamResultPage() {
  const { examId = "1" } = useParams();

  return (
    <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
      <Card>
        <CardHeader>
          <CardTitle>考试结果</CardTitle>
          <CardDescription>提交后自动判分</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <p className="text-4xl font-semibold">0 / 0</p>
          <p className="text-sm text-muted-foreground">正确 0 题，错误 0 题</p>
          <Button asChild variant="outline">
            <Link to={`/exams/${examId}/ranking`}>查看排名</Link>
          </Button>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>答案与解析</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">完成业务实现后，这里展示题目快照、用户答案、正确答案和解析。</p>
        </CardContent>
      </Card>
    </div>
  );
}
