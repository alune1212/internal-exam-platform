import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { ShieldCheck } from "lucide-react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";

import { loginAdmin } from "@/api/auth";
import { Wordmark } from "@/components/editorial/Wordmark";
import { PageHeader, PageSection } from "@/components/page";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { setAdminToken } from "@/lib/adminSession";
import { adminPageCopy } from "@/lib/pageCopy";

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
    onSuccess: (data) => {
      setAdminToken(data.token);
      navigate("/admin/dashboard");
    },
  });

  return (
    <main className="grid min-h-screen grid-cols-1 lg:grid-cols-2">
      <section className="flex flex-col gap-10 px-6 py-10 lg:px-16 lg:py-16">
        <Wordmark subtitle="— admin console" />
        <div className="flex flex-1 flex-col justify-center gap-8">
          <PageHeader
            data-testid="admin-login-header"
            eyebrow={adminPageCopy.login}
            title="安静地工作。"
            description="管理员登录后可访问题库、考试配置与所有报表。"
            className="md:flex-col md:items-start md:justify-start"
          />

          <PageSection data-testid="admin-login-form-section" variant="panel" className="max-w-md">
            <form
              className="flex flex-col gap-4"
              onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
            >
              <FieldGroup>
                <Field>
                  <FieldLabel htmlFor="username">账号 · Username</FieldLabel>
                  <Input id="username" autoComplete="username" {...form.register("username")} />
                </Field>
                <Field>
                  <FieldLabel htmlFor="password">密码 · Password</FieldLabel>
                  <Input
                    id="password"
                    type="password"
                    autoComplete="current-password"
                    {...form.register("password")}
                  />
                </Field>
              </FieldGroup>
              <Button type="submit" size="lg" disabled={mutation.isPending}>
                {mutation.isPending ? (
                  <Spinner data-icon="inline-start" aria-label="正在登录管理后台" />
                ) : (
                  <ShieldCheck data-icon="inline-start" />
                )}
                登录管理后台
              </Button>
              {mutation.isError ? (
                <Alert variant="error">
                  <AlertDescription>账号或密码不正确。</AlertDescription>
                </Alert>
              ) : null}
            </form>
          </PageSection>
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
          <p className="max-w-sm font-display text-display-md font-semibold text-canvas">
            所有考试、题库、报表 — 一处掌控。
          </p>
        </div>
      </aside>
    </main>
  );
}
