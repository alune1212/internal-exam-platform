import { useQuery } from "@tanstack/react-query";

import { getPracticeQuestions } from "@/api/questions";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function PracticePage() {
  const { data = [], isLoading } = useQuery({ queryKey: ["practice-questions"], queryFn: getPracticeQuestions });

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-2xl font-semibold">练习模式</h2>
        <p className="text-muted-foreground">刷全部 active 题目，练习结果不计入正式成绩。</p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>题目列表</CardTitle>
          <CardDescription>{isLoading ? "正在加载题目" : `当前 ${data.length} 道题`}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {data.length ? (
            data.map((question) => (
              <div key={question.id} className="rounded-md border p-4">
                <div className="mb-2 flex items-center gap-2">
                  <Badge variant="outline">{question.question_type}</Badge>
                  <span className="text-sm text-muted-foreground">{question.score} 分</span>
                </div>
                <p className="font-medium">{question.stem}</p>
                <p className="mt-3 text-sm text-muted-foreground">提交练习答案后显示正确答案和解析。</p>
              </div>
            ))
          ) : (
            <p className="text-sm text-muted-foreground">暂无题目，管理员导入题库后会显示在这里。</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
