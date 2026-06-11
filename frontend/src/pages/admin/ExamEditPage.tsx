import { zodResolver } from "@hookform/resolvers/zod";
import { Save } from "lucide-react";
import { useForm } from "react-hook-form";
import { useParams } from "react-router-dom";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const schema = z.object({
  title: z.string().min(1),
  duration_minutes: z.coerce.number().min(1),
  status: z.string().min(1),
});

type ExamEditForm = z.infer<typeof schema>;

export function ExamEditPage() {
  const { examId } = useParams();
  const form = useForm<ExamEditForm>({
    resolver: zodResolver(schema),
    defaultValues: { title: "临时考试", duration_minutes: 60, status: "draft" },
  });

  return (
    <Card className="max-w-2xl">
      <CardHeader>
        <CardTitle>编辑考试 #{examId}</CardTitle>
        <CardDescription>第一阶段保留抽题规则 JSON 字段，后续补规则编辑器。</CardDescription>
      </CardHeader>
      <CardContent>
        <form className="flex flex-col gap-4" onSubmit={form.handleSubmit(() => undefined)}>
          <div className="flex flex-col gap-2">
            <Label htmlFor="title">考试名称</Label>
            <Input id="title" {...form.register("title")} />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="duration_minutes">考试时长（分钟）</Label>
            <Input id="duration_minutes" type="number" {...form.register("duration_minutes")} />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="status">状态</Label>
            <Input id="status" {...form.register("status")} />
          </div>
          <Button type="submit">
            <Save data-icon="inline-start" />
            保存配置
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
