import { ClipboardCheck } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function ExamStartPage() {
  const { examId = "1" } = useParams();

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
        <Button asChild>
          <Link to={`/exams/${examId}/taking`}>
            <ClipboardCheck data-icon="inline-start" />
            开始考试
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}
