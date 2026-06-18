import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { LogIn } from "lucide-react";
import { useForm } from "react-hook-form";
import { Navigate, useNavigate, useOutletContext } from "react-router-dom";
import { z } from "zod";

import { loginCandidate as requestCandidateLogin } from "@/api/auth";
import { ChapterNumber } from "@/components/editorial/ChapterNumber";
import type { CandidateSessionContext } from "@/components/layout/CandidateLayout";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Field, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";

const schema = z.object({
  name: z.string().min(1, "请输入姓名"),
  employee_no: z.string().optional(),
});

type LoginForm = z.infer<typeof schema>;

export function LoginPage() {
  const navigate = useNavigate();
  const { candidate, loginCandidate } = useOutletContext<CandidateSessionContext>();
  const form = useForm<LoginForm>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", employee_no: "" },
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
    <div data-stagger className="flex min-h-[calc(100vh-10rem)] flex-col justify-center gap-8">
      <div className="flex flex-col gap-6">
        <ChapterNumber>CHAPTER 01 · WELCOME</ChapterNumber>
        <h1 className="font-display text-display-lg font-semibold leading-[1.08] text-ink lg:text-display-xl">
          报上姓名，<em className="italic">开始答题</em>。
        </h1>
        <p className="max-w-xl text-body-lg text-muted">
          填写姓名即可进入练习或考试。系统会先在应考名单中匹配；如有员工号会优先用于识别。整个过程不会发送邮件或短信。
        </p>
      </div>

      <Card className="max-w-3xl bg-canvas-warm">
        <CardContent className="p-6 md:p-8">
          <form
            className="flex flex-col gap-5"
            onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
            noValidate
          >
            <FieldGroup>
              <Field data-invalid={form.formState.errors.name ? "" : undefined}>
                <FieldLabel htmlFor="name">
                  姓名 · <span className="text-muted">Name</span>
                </FieldLabel>
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
                  员工号 · <span className="text-muted">Employee No.</span>
                  <span className="ml-1 text-muted">（可选）</span>
                </FieldLabel>
                <Input
                  id="employee_no"
                  autoComplete="off"
                  placeholder="例如 10042"
                  {...form.register("employee_no")}
                />
              </Field>
            </FieldGroup>

            <Button type="submit" size="lg" className="h-12 w-full" disabled={mutation.isPending}>
              {mutation.isPending ? (
                <Spinner data-icon="inline-start" aria-label="正在进入" />
              ) : (
                <LogIn data-icon="inline-start" />
              )}
              {mutation.isPending ? "正在进入" : "进入系统"}
            </Button>

            {mutation.isError ? (
              <Alert variant="error">
                <AlertDescription>未找到匹配的考试人员，请核对姓名或员工号。</AlertDescription>
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
    </div>
  );
}
