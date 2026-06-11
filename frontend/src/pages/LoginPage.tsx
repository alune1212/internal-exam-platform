import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { LogIn } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { loginCandidate } from "@/api/auth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const schema = z.object({
  name: z.string().min(1, "请输入姓名"),
  employee_no: z.string().optional(),
});

type LoginForm = z.infer<typeof schema>;

export function LoginPage() {
  const form = useForm<LoginForm>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", employee_no: "" },
  });
  const mutation = useMutation({ mutationFn: loginCandidate });

  return (
    <Card className="max-w-xl">
      <CardHeader>
        <CardTitle>考试人登录</CardTitle>
        <CardDescription>输入姓名进入练习或考试；有员工号时优先用于识别。</CardDescription>
      </CardHeader>
      <CardContent>
        <form className="flex flex-col gap-4" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
          <div className="flex flex-col gap-2">
            <Label htmlFor="name">姓名</Label>
            <Input id="name" {...form.register("name")} aria-invalid={Boolean(form.formState.errors.name)} />
            {form.formState.errors.name ? (
              <p className="text-sm text-destructive">{form.formState.errors.name.message}</p>
            ) : null}
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="employee_no">员工号</Label>
            <Input id="employee_no" {...form.register("employee_no")} />
          </div>
          <Button type="submit" disabled={mutation.isPending}>
            <LogIn data-icon="inline-start" />
            进入系统
          </Button>
          {mutation.data ? <p className="text-sm text-muted-foreground">已识别：{mutation.data.name}</p> : null}
        </form>
      </CardContent>
    </Card>
  );
}
