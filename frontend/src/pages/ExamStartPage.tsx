import { useMutation } from "@tanstack/react-query";
import { ClipboardCheck } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { startExam } from "@/api/exams";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getCurrentCandidate } from "@/lib/candidateSession";

export function ExamStartPage() {
  const { examId = "1" } = useParams();
  const navigate = useNavigate();
  const candidate = getCurrentCandidate();
  const mutation = useMutation({
    mutationFn: () => startExam(examId, candidate?.id ?? 0),
    onSuccess: (result) => {
      navigate(`/exams/${examId}/taking?attemptId=${result.attempt_id}`);
    },
  });

  return (
    <Card className="max-w-2xl">
      <CardHeader>
        <CardTitle>考试开始确认</CardTitle>
        <CardDescription>系统会在开始时生成题目快照，后续题库修改不影响本次结果。</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <ul className="list-disc pl-5 text-sm text-muted-foreground">
          <li>考试中答案会自动暂存，但倒计时不会暂停。</li>
          <li>可以提前交卷，到时间系统自动提交。</li>
          <li>提交后自动判分，并按配置展示答案和排名。</li>
        </ul>
        {candidate ? <p className="text-sm text-muted-foreground">当前考试人：{candidate.name}</p> : null}
        {candidate ? (
          <Button type="button" disabled={mutation.isPending} onClick={() => mutation.mutate()}>
            <ClipboardCheck data-icon="inline-start" />
            {mutation.isPending ? "正在开始" : "开始考试"}
          </Button>
        ) : (
          <Button asChild>
            <Link to="/login">先登录考试人</Link>
          </Button>
        )}
        {mutation.isError ? <p className="text-sm text-destructive">开始考试失败，请确认考试仍处于发布状态。</p> : null}
      </CardContent>
    </Card>
  );
}
