import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { LogIn } from "lucide-react";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { Navigate, useNavigate, useOutletContext } from "react-router-dom";
import { z } from "zod";

import {
  requestCandidateLoginOtp,
  verifyCandidateLoginOtp,
  type CandidateLoginChallenge,
} from "@/api/auth";
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
  email: z.string().min(1, "请输入邮箱").email("请输入有效邮箱"),
  otp: z.string().optional(),
});

type LoginForm = z.infer<typeof schema>;

export function LoginPage() {
  const navigate = useNavigate();
  const { candidate, loginCandidate } = useOutletContext<CandidateSessionContext>();
  const [challenge, setChallenge] = useState<CandidateLoginChallenge | null>(null);
  const [nowMs, setNowMs] = useState(0);
  const form = useForm<LoginForm>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", employee_no: "", email: "", otp: "" },
  });
  const requestMutation = useMutation({
    mutationFn: requestCandidateLoginOtp,
    onSuccess: (nextChallenge) => {
      setChallenge(nextChallenge);
      form.clearErrors("otp");
    },
  });
  const verifyMutation = useMutation({
    mutationFn: verifyCandidateLoginOtp,
    onSuccess: (nextCandidate) => {
      loginCandidate(nextCandidate);
      navigate("/exams", { replace: true });
    },
  });

  useEffect(() => {
    if (!challenge) {
      setNowMs(0);
      return;
    }

    const refreshNow = () => setNowMs(Date.now());
    refreshNow();

    const cooldownMs = Date.parse(challenge.resend_available_at) - Date.now();
    if (cooldownMs <= 0) {
      return;
    }

    const timeoutId = window.setTimeout(refreshNow, cooldownMs + 100);
    return () => window.clearTimeout(timeoutId);
  }, [challenge]);

  if (candidate) {
    return <Navigate to="/exams" replace />;
  }

  function handleSubmit(values: LoginForm) {
    if (!challenge) {
      requestMutation.mutate({
        name: values.name,
        employee_no: values.employee_no || undefined,
        email: values.email,
      });
      return;
    }
    if (!values.otp?.trim()) {
      form.setError("otp", { message: "请输入验证码" });
      return;
    }
    verifyMutation.mutate({ challenge_id: challenge.challenge_id, otp: values.otp });
  }

  const isPending = requestMutation.isPending || verifyMutation.isPending;
  const resendDisabled = challenge !== null && Date.parse(challenge.resend_available_at) > nowMs;

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
            onSubmit={form.handleSubmit(handleSubmit)}
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
                  disabled={Boolean(challenge)}
                />
                {form.formState.errors.name ? (
                  <FieldError>{form.formState.errors.name.message}</FieldError>
                ) : null}
              </Field>

              <Field>
                <FieldLabel htmlFor="employee_no">员工号（可选）</FieldLabel>
                <Input
                  id="employee_no"
                  autoComplete="off"
                  placeholder="例如 10042"
                  {...form.register("employee_no")}
                  disabled={Boolean(challenge)}
                />
              </Field>

              <Field data-invalid={form.formState.errors.email ? "" : undefined}>
                <FieldLabel htmlFor="email">邮箱</FieldLabel>
                <Input
                  id="email"
                  autoComplete="email"
                  type="email"
                  aria-invalid={Boolean(form.formState.errors.email)}
                  {...form.register("email")}
                  disabled={Boolean(challenge)}
                />
                {form.formState.errors.email ? (
                  <FieldError>{form.formState.errors.email.message}</FieldError>
                ) : null}
              </Field>

              {challenge ? (
                <Field data-invalid={form.formState.errors.otp ? "" : undefined}>
                  <FieldLabel htmlFor="otp">验证码</FieldLabel>
                  <Input
                    id="otp"
                    autoComplete="one-time-code"
                    inputMode="numeric"
                    aria-invalid={Boolean(form.formState.errors.otp)}
                    {...form.register("otp")}
                  />
                  {form.formState.errors.otp ? (
                    <FieldError>{form.formState.errors.otp.message}</FieldError>
                  ) : null}
                </Field>
              ) : null}
            </FieldGroup>

            <Button type="submit" size="lg" className="h-12 w-full" disabled={isPending}>
              {isPending ? (
                <Spinner
                  data-icon="inline-start"
                  aria-label={challenge ? "正在进入" : "正在发送"}
                />
              ) : (
                <LogIn data-icon="inline-start" />
              )}
              {isPending
                ? challenge
                  ? "正在进入"
                  : "正在发送"
                : challenge
                  ? "进入平台"
                  : "发送验证码"}
            </Button>

            {challenge ? (
              <Button
                type="button"
                variant="ghost"
                className="w-full"
                disabled={requestMutation.isPending || resendDisabled}
                onClick={() => {
                  const values = form.getValues();
                  requestMutation.mutate({
                    name: values.name,
                    employee_no: values.employee_no || undefined,
                    email: values.email,
                  });
                }}
              >
                重新发送验证码
              </Button>
            ) : null}

            {requestMutation.isError ? (
              <Alert variant="error">
                <AlertDescription>{candidatePageText.login.error}</AlertDescription>
              </Alert>
            ) : null}
            {verifyMutation.isError ? (
              <Alert variant="error">
                <AlertDescription>{candidatePageText.login.otpError}</AlertDescription>
              </Alert>
            ) : null}
            {challenge ? (
              <Alert>
                <AlertDescription>{candidatePageText.login.otpSent}</AlertDescription>
              </Alert>
            ) : null}
          </form>
        </CardContent>
      </Card>
    </PageSection>
  );
}
