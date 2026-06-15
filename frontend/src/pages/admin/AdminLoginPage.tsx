import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { ShieldCheck } from "lucide-react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";

import { loginAdmin } from "@/api/auth";
import { setAdminToken } from "@/lib/adminSession";
import { ChapterNumber } from "@/components/editorial/ChapterNumber";
import { Wordmark } from "@/components/editorial/Wordmark";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const schema = z.object({
  username: z.string().min(1, "请输入管理员账号"),
  password: z.string().min(1, "请输入密码"),
});

type AdminLoginForm = z.infer<typeof schema>;

export function AdminLoginPage() {
  const navigate = useNavigate();
  const form = useForm<AdminLoginForm>({
    resolver: zodResolver(schema),
    defaultValues: { username: "", password: "" },
  });
  const mutation = useMutation({
    mutationFn: loginAdmin,
    onSuccess: (_data, variables) => {
      setAdminToken(variables.password);
      navigate("/admin/dashboard");
    },
  });

  return (
    <main className="grid min-h-screen grid-cols-1 lg:grid-cols-2">
      <section className="flex flex-col gap-10 px-6 py-10 lg:px-16 lg:py-16">
        <Wordmark tone="dark" subtitle="— admin console" />
        <div className="flex flex-1 flex-col justify-center gap-8">
          <header className="flex flex-col gap-3">
            <ChapterNumber>CHAPTER 00 · ADMIN</ChapterNumber>
            <h1 className="font-display text-[40px] font-semibold italic tracking-[-0.04em] text-ink lg:text-[64px]">
              安静地工作。
            </h1>
            <p className="text-body text-body-lg">管理员登录后可访问题库、考试配置与所有报表。</p>
          </header>

          <form
            className="flex max-w-md flex-col gap-4 rounded-lg border border-hairline bg-surface-card p-6 lg:p-8"
            onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
          >
            <div className="flex flex-col gap-2">
              <Label htmlFor="username">账号 · Username</Label>
              <Input id="username" autoComplete="username" {...form.register("username")} />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="password">密码 · Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                {...form.register("password")}
              />
            </div>
            <Button type="submit" size="lg" disabled={mutation.isPending}>
              <ShieldCheck data-icon="inline-start" />
              登录管理后台
            </Button>
            {mutation.isError ? (
              <p className="text-caption text-error" role="alert">
                账号或密码不正确。
              </p>
            ) : null}
          </form>
        </div>
      </section>

      <aside
        aria-hidden="true"
        className="relative hidden bg-footer lg:block"
        style={{
          backgroundImage: "radial-gradient(rgba(255,255,255,0.08) 1px, transparent 1px)",
          backgroundSize: "24px 24px",
        }}
      >
        <div className="absolute inset-0 flex flex-col items-start justify-end gap-3 p-16 text-footer-soft">
          <p className="text-caption uppercase tracking-[0.18em]">ADMIN CONSOLE</p>
          <p className="max-w-sm font-display text-[28px] font-semibold italic tracking-[-0.04em] text-white">
            所有考试、题库、报表 — 一处掌控。
          </p>
        </div>
      </aside>
    </main>
  );
}
