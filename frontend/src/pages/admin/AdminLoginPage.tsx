import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { ShieldCheck } from "lucide-react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";

import { loginAdmin } from "@/api/auth";
import { Wordmark } from "@/components/editorial/Wordmark";
import { PageActions, PageHeader, PageSection } from "@/components/page";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { setAdminToken } from "@/lib/adminSession";
import { adminPageText } from "@/lib/pageCopy";

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
    <main
      data-auth-canvas="admin"
      className="flex min-h-screen w-full items-center justify-center bg-canvas-warm px-page-inline py-page-block md:px-page-inline-lg"
    >
      <section
        data-testid="admin-login-canvas-content"
        className="flex w-full max-w-reading flex-col gap-8 landscape:grid landscape:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)] landscape:items-start landscape:gap-6"
      >
        <div className="flex flex-col gap-5 landscape:gap-4">
          <Wordmark subtitle="管理入口" />
          <PageHeader
            data-testid="admin-login-header"
            context="管理员登录"
            title={adminPageText.login.title}
            description={adminPageText.login.description}
            className="gap-3 md:flex-col md:items-start md:justify-start"
          />
        </div>

        <PageSection data-testid="admin-login-form-section" variant="panel">
          <form
            className="flex flex-col gap-5"
            aria-busy={mutation.isPending}
            onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
            noValidate
          >
            <FieldGroup>
              <Field
                pending={mutation.isPending}
                data-invalid={form.formState.errors.username ? "" : undefined}
              >
                <FieldLabel htmlFor="username">管理员账号</FieldLabel>
                <Input
                  id="username"
                  autoComplete="username"
                  aria-invalid={Boolean(form.formState.errors.username)}
                  {...form.register("username")}
                />
                {form.formState.errors.username ? (
                  <FieldError>{form.formState.errors.username.message}</FieldError>
                ) : null}
              </Field>
              <Field
                pending={mutation.isPending}
                data-invalid={form.formState.errors.password ? "" : undefined}
              >
                <FieldLabel htmlFor="password">密码</FieldLabel>
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  aria-invalid={Boolean(form.formState.errors.password)}
                  {...form.register("password")}
                />
                {form.formState.errors.password ? (
                  <FieldError>{form.formState.errors.password.message}</FieldError>
                ) : null}
              </Field>
            </FieldGroup>

            <PageActions placement="auth" aria-label="管理后台登录操作">
              <Button type="submit" size="lg" pending={mutation.isPending} className="w-full">
                {mutation.isPending ? (
                  <Spinner data-icon="inline-start" aria-label="正在进入管理后台" />
                ) : (
                  <ShieldCheck data-icon="inline-start" aria-hidden="true" />
                )}
                进入管理后台
              </Button>
            </PageActions>

            {mutation.isError ? (
              <Alert variant="error">
                <AlertDescription>账号或密码不正确。</AlertDescription>
              </Alert>
            ) : null}
          </form>
        </PageSection>
      </section>
    </main>
  );
}
