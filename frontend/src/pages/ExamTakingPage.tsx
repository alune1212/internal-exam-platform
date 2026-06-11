import { Clock, Save, Send } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function ExamTakingPage() {
  const { examId = "1" } = useParams();

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_280px]">
      <Card>
        <CardHeader>
          <CardTitle>答题区</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="rounded-md border p-4">
            <p className="mb-3 font-medium">1. 第一阶段页面骨架题目展示区域</p>
            <div className="grid gap-2">
              {["A", "B", "C", "D"].map((label) => (
                <label key={label} className="flex items-center gap-2 rounded-md border p-3 text-sm">
                  <input type="radio" name="demo-question" />
                  {label}. 选项内容
                </label>
              ))}
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline">
              <Save data-icon="inline-start" />
              暂存答案
            </Button>
            <Button asChild>
              <Link to={`/exams/${examId}/result`}>
                <Send data-icon="inline-start" />
                提前交卷
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock data-icon="inline-start" />
            倒计时
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-3xl font-semibold">60:00</p>
          <p className="mt-2 text-sm text-muted-foreground">暂存不会暂停倒计时，到时间后自动提交。</p>
        </CardContent>
      </Card>
    </div>
  );
}
