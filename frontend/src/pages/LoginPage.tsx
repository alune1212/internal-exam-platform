import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { LogIn } from "lucide-react";
import { useForm } from "react-hook-form";
import { Navigate, useNavigate, useOutletContext } from "react-router-dom";
import { z } from "zod";

import { loginCandidate as requestCandidateLogin } from "@/api/auth";
import { Wordmark } from "@/components/editorial/Wordmark";
import type { CandidateSessionContext } from "@/components/layout/CandidateLayout";
import { PageHeader, PageSection } from "@/components/page";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Field, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { candidatePageCopy, candidatePageText } from "@/lib/pageCopy";

const schema = z.object({
  name: z.string().min(1, "请输入姓名"),
  employee_no: z.string().optional(),
  phone_suffix: z.string().min(1, "请输入手机号后四位"),
});

type LoginForm = z.infer<typeof schema>;

export function LoginPage() {
  const navigate = useNavigate();
  const { candidate, loginCandidate } = useOutletContext<CandidateSessionContext>();
  const form = useForm<LoginForm>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", employee_no: "", phone_suffix: "" },
  });
  const mutation = useMutation({
    mutationFn: requestCandidateLogin,
    onSuccess: (nextCandidate) => {
      loginCandidate(nextCandidate);
      navigate("/exams", { replace: true });
    },
  });

  if (candidate) {
    return <Navigate to="/exams" replace />;
  }

  return (
    <PageSection variant="plain" data-stagger className="w-full max-w-md gap-6">
      <div className="flex flex-col gap-4">
        <Wordmark size="md" subtitle="internal exam platform" />
        <PageHeader
          data-testid="candidate-login-header"
          eyebrow={candidatePageCopy.login}
          title={candidatePageText.login.title}
          description={candidatePageText.login.description}
          className="gap-3 md:flex-col md:items-start"
        />
      </div>

      <Card className="bg-canvas shadow-pop">
        <CardContent className="p-6 md:p-8">
          <form
            className="flex flex-col gap-5"
            onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
            noValidate
          >
            <FieldGroup>
              <Field data-invalid={form.formState.errors.name ? "" : undefined}>
                <FieldLabel htmlFor="name">姓名</FieldLabel>
                <Input
                  id="name"
                  autoComplete="name"
                  aria-invalid={Boolean(form.formState.errors.name)}
                  {...form.register("name")}
                />
                {form.formState.errors.name ? (
                  <FieldError>{form.formState.errors.name.message}</FieldError>
                ) : null}
              </Field>

              <Field>
                <FieldLabel htmlFor="employee_no">
                  员工号<span className="ml-1 text-muted">（可选）</span>
                </FieldLabel>
                <Input
                  id="employee_no"
                  autoComplete="off"
                  placeholder="例如 10042"
                  {...form.register("employee_no")}
                />
              </Field>

              <Field data-invalid={form.formState.errors.phone_suffix ? "" : undefined}>
                <FieldLabel htmlFor="phone_suffix">手机号后四位</FieldLabel>
                <Input
                  id="phone_suffix"
                  autoComplete="off"
                  inputMode="numeric"
                  aria-invalid={Boolean(form.formState.errors.phone_suffix)}
                  {...form.register("phone_suffix")}
                />
                {form.formState.errors.phone_suffix ? (
                  <FieldError>{form.formState.errors.phone_suffix.message}</FieldError>
                ) : null}
              </Field>
            </FieldGroup>

            <Button type="submit" size="lg" className="h-12 w-full" disabled={mutation.isPending}>
              {mutation.isPending ? (
                <Spinner data-icon="inline-start" aria-label="正在进入" />
              ) : (
                <LogIn data-icon="inline-start" />
              )}
              {mutation.isPending ? "正在进入" : "进入平台"}
            </Button>

            {mutation.isError ? (
              <Alert variant="error">
                <AlertDescription>{candidatePageText.login.error}</AlertDescription>
              </Alert>
            ) : null}
            {mutation.data ? (
              <Alert>
                <AlertDescription>已识别：{mutation.data.name}</AlertDescription>
              </Alert>
            ) : null}
          </form>
        </CardContent>
      </Card>
    </PageSection>
  );
}
