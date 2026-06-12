import { useQuery } from "@tanstack/react-query";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { getAttemptResult } from "@/api/attempts";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function ExamResultPage() {
  const { examId = "1" } = useParams();
  const [searchParams] = useSearchParams();
  const attemptId = searchParams.get("attemptId");
  const { data: result, isLoading } = useQuery({
    queryKey: ["attempt-result", attemptId],
    queryFn: () => getAttemptResult(attemptId ?? ""),
    enabled: Boolean(attemptId),
  });

  return (
    <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
      <Card>
        <CardHeader>
          <CardTitle>考试结果</CardTitle>
          <CardDescription>提交后自动判分</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <p className="text-4xl font-semibold">
            {result ? `${result.score} / ${result.total_score}` : isLoading ? "加载中" : "--"}
          </p>
          <p className="text-sm text-muted-foreground">
            {result ? `正确 ${result.correct_count} 题，错误 ${result.wrong_count} 题` : "提交后显示成绩"}
          </p>
          <Button asChild variant="outline">
            <Link to={`/exams/${examId}/ranking`}>查看排名</Link>
          </Button>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>答案与解析</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {result?.questions.length ? (
            result.questions.map((question, index) => (
              <div key={question.attempt_question_id} className="rounded-md border p-4">
                <p className="font-medium">
                  {index + 1}. {question.stem_snapshot}
                </p>
                <p className="mt-2 text-sm text-muted-foreground">
                  你的答案：{question.selected_answer || "未作答"}；正确答案：{question.correct_answer_snapshot}
                </p>
                <p className={question.is_correct ? "mt-1 text-sm text-emerald-700" : "mt-1 text-sm text-destructive"}>
                  {question.is_correct ? "回答正确" : "回答错误"}，得分 {question.score_awarded} / {question.score}
                </p>
                {question.analysis_snapshot ? (
                  <p className="mt-2 text-sm text-muted-foreground">解析：{question.analysis_snapshot}</p>
                ) : null}
              </div>
            ))
          ) : (
            <p className="text-sm text-muted-foreground">{isLoading ? "正在加载结果" : "暂无结果，请先完成考试。"}</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
