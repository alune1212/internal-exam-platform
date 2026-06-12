import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { ShieldCheck } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { loginAdmin } from "@/api/auth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const schema = z.object({
  username: z.string().min(1, "请输入管理员账号"),
  password: z.string().min(1, "请输入密码"),
});

type AdminLoginForm = z.infer<typeof schema>;

export function AdminLoginPage() {
  const form = useForm<AdminLoginForm>({
    resolver: zodResolver(schema),
    defaultValues: { username: "", password: "" },
  });
  const mutation = useMutation({ mutationFn: loginAdmin });

  return (
    <div className="mx-auto flex min-h-screen max-w-xl items-center px-4">
      <Card className="w-full">
        <CardHeader>
          <CardTitle>管理员登录</CardTitle>
          <CardDescription>第一阶段使用简单管理员口令，后续可替换为正式认证。</CardDescription>
        </CardHeader>
        <CardContent>
          <form
            className="flex flex-col gap-4"
            onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
          >
            <div className="flex flex-col gap-2">
              <Label htmlFor="username">账号</Label>
              <Input id="username" {...form.register("username")} />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="password">密码</Label>
              <Input id="password" type="password" {...form.register("password")} />
            </div>
            <Button type="submit" disabled={mutation.isPending}>
              <ShieldCheck data-icon="inline-start" />
              登录管理后台
            </Button>
            {mutation.data ? (
              <p className="text-sm text-muted-foreground">已获取管理会话。</p>
            ) : null}
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
