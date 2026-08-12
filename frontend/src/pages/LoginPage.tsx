import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { ArrowRight, LogIn } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { Navigate, useNavigate, useOutletContext, useSearchParams } from "react-router-dom";
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
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { candidatePageCopy, candidatePageText } from "@/lib/pageCopy";
import {
  clearRegistrationFlow,
  getSafeReturnTo,
  maskEmail,
  setRegistrationFlow,
} from "@/lib/candidateSession";

const schema = z.object({
  email: z.string().trim().min(1, "请输入邮箱").email("请输入有效邮箱"),
  otp: z.string().optional(),
});

type LoginForm = z.infer<typeof schema>;

export function LoginPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const returnTo = getSafeReturnTo(searchParams.get("returnTo"));
  const context = useOutletContext<CandidateSessionContext | null>();
  const candidate = context?.candidate ?? null;
  const loginCandidate = context?.loginCandidate ?? (() => undefined);
  const [challenge, setChallenge] = useState<CandidateLoginChallenge | null>(null);
  const [challengeEmail, setChallengeEmail] = useState("");
  const [nowMs, setNowMs] = useState(() => Date.now());
  const [accountUnavailableMessage, setAccountUnavailableMessage] = useState<string | null>(null);
  const form = useForm<LoginForm>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", otp: "" },
  });

  const requestMutation = useMutation({
    mutationFn: requestCandidateLoginOtp,
    onSuccess: (nextChallenge, variables) => {
      setChallenge(nextChallenge);
      setChallengeEmail(variables.email);
      setAccountUnavailableMessage(null);
      form.clearErrors("otp");
    },
  });

  const verifyMutation = useMutation({
    mutationFn: verifyCandidateLoginOtp,
    onSuccess: (verification) => {
      if (verification.outcome === "authenticated") {
        if (verification.account.status !== "active") {
          clearRegistrationFlow();
          setAccountUnavailableMessage("账号暂不可用，请联系管理员重新激活后再登录。");
          return;
        }
        clearRegistrationFlow();
        loginCandidate({
          ...verification.account,
          status: "active",
          token: verification.token,
          token_expires_at: verification.token_expires_at,
        });
        navigate(returnTo, { replace: true });
        return;
      }
      if (verification.outcome === "registration_required") {
        setRegistrationFlow({
          registration_credential: verification.registration_credential,
          email: verification.email,
          suggested_display_name: verification.suggested_display_name,
          returnTo,
          expires_at: verification.registration_expires_at,
        });
        navigate(`/register?returnTo=${encodeURIComponent(returnTo)}`, { replace: true });
        return;
      }
      // A verified inactive mailbox is intentionally not treated as a generic
      // OTP error: the user can take the actionable reactivation path.
      clearRegistrationFlow();
      setAccountUnavailableMessage(verification.message);
    },
    onError: () => {
      setAccountUnavailableMessage(null);
      form.setError("otp", { message: candidatePageText.login.otpError });
    },
  });

  useEffect(() => {
    if (!challenge) return undefined;
    const tick = () => setNowMs(Date.now());
    tick();
    const intervalId = window.setInterval(tick, 1_000);
    return () => window.clearInterval(intervalId);
  }, [challenge]);

  const resendSeconds = useMemo(() => {
    if (!challenge) return 0;
    const availableAt = Date.parse(challenge.resend_available_at);
    if (!Number.isFinite(availableAt)) return 0;
    return Math.max(0, Math.ceil((availableAt - nowMs) / 1_000));
  }, [challenge, nowMs]);

  if (candidate) {
    return <Navigate to={returnTo} replace />;
  }

  function handleSubmit(values: LoginForm) {
    const email = values.email.trim().toLowerCase();
    if (!challenge) {
      clearRegistrationFlow();
      requestMutation.mutate({ email });
      return;
    }
    const otp = values.otp?.trim() ?? "";
    if (!otp) {
      form.setError("otp", { message: "请输入验证码" });
      return;
    }
    verifyMutation.mutate({ challenge_id: challenge.challenge_id, otp });
  }

  const isPending = requestMutation.isPending || verifyMutation.isPending;
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
              <Field data-invalid={form.formState.errors.email ? "" : undefined}>
                <FieldLabel htmlFor="email">邮箱</FieldLabel>
                <Input
                  id="email"
                  autoComplete="email"
                  type="email"
                  inputMode="email"
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
                    maxLength={6}
                    aria-invalid={Boolean(form.formState.errors.otp)}
                    {...form.register("otp")}
                  />
                  <FieldDescription>
                    {candidatePageText.login.otpSent(maskEmail(challengeEmail), 10)}
                  </FieldDescription>
                  {form.formState.errors.otp ? (
                    <FieldError>{form.formState.errors.otp.message}</FieldError>
                  ) : null}
                </Field>
              ) : null}
            </FieldGroup>

            <p className="text-body-sm leading-relaxed text-muted">
              {candidatePageText.login.permissionNote}
            </p>

            <Button type="submit" size="lg" className="h-12 w-full" disabled={isPending}>
              {isPending ? (
                <Spinner
                  data-icon="inline-start"
                  aria-label={challenge ? "正在验证" : "正在发送"}
                />
              ) : challenge ? (
                <ArrowRight data-icon="inline-start" aria-hidden="true" />
              ) : (
                <LogIn data-icon="inline-start" aria-hidden="true" />
              )}
              {challenge ? "验证并继续" : "发送验证码"}
            </Button>

            {challenge ? (
              <Button
                type="button"
                variant="ghost"
                className="w-full"
                disabled={requestMutation.isPending || resendSeconds > 0}
                onClick={() => requestMutation.mutate({ email: challengeEmail })}
              >
                {resendSeconds > 0 ? `重新发送验证码（${resendSeconds}秒）` : "重新发送验证码"}
              </Button>
            ) : null}

            {requestMutation.isError ? (
              <Alert variant="error">
                <AlertDescription>{candidatePageText.login.error}</AlertDescription>
              </Alert>
            ) : null}
            {accountUnavailableMessage ? (
              <Alert variant="warning">
                <AlertDescription>{accountUnavailableMessage}</AlertDescription>
              </Alert>
            ) : null}
          </form>
        </CardContent>
      </Card>
    </PageSection>
  );
}
