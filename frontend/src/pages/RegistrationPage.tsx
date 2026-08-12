import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { ArrowRight, Check } from "lucide-react";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { Navigate, useNavigate, useOutletContext, useSearchParams } from "react-router-dom";
import { z } from "zod";

import { completeCandidateRegistration } from "@/api/auth";
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
  getRegistrationFlow,
  getSafeReturnTo,
  setCurrentCandidate,
} from "@/lib/candidateSession";

const schema = z.object({
  display_name: z.string().trim().min(1, "请输入姓名"),
  confirm_suggested_name: z.boolean().optional(),
});

type RegistrationForm = z.infer<typeof schema>;

export function RegistrationPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const context = useOutletContext<CandidateSessionContext | null>();
  const candidate = context?.candidate ?? null;
  const loginCandidate = context?.loginCandidate;
  const activeFlow = getRegistrationFlow();
  const returnTo = getSafeReturnTo(searchParams.get("returnTo") ?? activeFlow?.returnTo);
  const suggestion = activeFlow?.suggested_display_name?.trim() ?? "";
  const form = useForm<RegistrationForm>({
    resolver: zodResolver(schema),
    defaultValues: { display_name: suggestion, confirm_suggested_name: false },
  });

  useEffect(() => {
    if (suggestion && form.getValues("display_name") !== suggestion) {
      form.reset({ display_name: suggestion, confirm_suggested_name: false });
    }
  }, [form, suggestion]);

  const mutation = useMutation({
    mutationFn: completeCandidateRegistration,
    onSuccess: (nextCandidate) => {
      clearRegistrationFlow();
      if (loginCandidate) loginCandidate(nextCandidate);
      else setCurrentCandidate(nextCandidate);
      navigate(returnTo, { replace: true });
    },
  });

  if (candidate) {
    return <Navigate to={returnTo} replace />;
  }

  if (!activeFlow) {
    return <Navigate to={`/login?returnTo=${encodeURIComponent(returnTo)}`} replace />;
  }

  function handleSubmit(values: RegistrationForm) {
    const displayName = values.display_name.trim();
    if (!displayName) {
      form.setError("display_name", { message: "请输入姓名" });
      return;
    }
    if (suggestion && displayName === suggestion && !values.confirm_suggested_name) {
      form.setError("confirm_suggested_name", { message: "请确认或修改该姓名" });
      return;
    }
    const registrationCredential = activeFlow?.registration_credential;
    if (!registrationCredential) return;
    mutation.mutate({
      registration_credential: registrationCredential,
      display_name: displayName,
    });
  }

  return (
    <PageSection variant="plain" data-stagger className="w-full max-w-md gap-6">
      <PageHeader
        eyebrow={candidatePageCopy.login}
        title={candidatePageText.login.registrationTitle}
        description={candidatePageText.login.registrationDescription}
      />
      <Card className="bg-canvas shadow-pop">
        <CardContent className="p-6 md:p-8">
          <form
            className="flex flex-col gap-5"
            onSubmit={form.handleSubmit(handleSubmit)}
            noValidate
          >
            <FieldGroup>
              <Field data-invalid={form.formState.errors.display_name ? "" : undefined}>
                <FieldLabel htmlFor="display_name">姓名</FieldLabel>
                <Input
                  id="display_name"
                  autoComplete="name"
                  autoFocus
                  aria-invalid={Boolean(form.formState.errors.display_name)}
                  {...form.register("display_name")}
                />
                {suggestion ? (
                  <FieldDescription>
                    应考名单中的姓名仅作建议；确认或修改后才会创建用户账号，不会改写正式考试名单。
                  </FieldDescription>
                ) : null}
                {form.formState.errors.display_name ? (
                  <FieldError>{form.formState.errors.display_name.message}</FieldError>
                ) : null}
              </Field>
              {suggestion ? (
                <Field
                  orientation="horizontal"
                  data-invalid={form.formState.errors.confirm_suggested_name ? "" : undefined}
                >
                  <FieldLabel
                    htmlFor="confirm_suggested_name"
                    className="normal-case tracking-normal"
                  >
                    <span className="inline-flex items-center gap-2">
                      <Input
                        id="confirm_suggested_name"
                        type="checkbox"
                        className="size-4"
                        aria-invalid={Boolean(form.formState.errors.confirm_suggested_name)}
                        {...form.register("confirm_suggested_name")}
                      />
                      确认此姓名用于用户账号
                    </span>
                  </FieldLabel>
                  {form.formState.errors.confirm_suggested_name ? (
                    <FieldError>{form.formState.errors.confirm_suggested_name.message}</FieldError>
                  ) : null}
                </Field>
              ) : null}
            </FieldGroup>

            <Button type="submit" size="lg" className="h-12 w-full" disabled={mutation.isPending}>
              {mutation.isPending ? (
                <Spinner data-icon="inline-start" aria-label="正在创建账号" />
              ) : (
                <Check data-icon="inline-start" aria-hidden="true" />
              )}
              创建账号并继续
              <ArrowRight data-icon="inline-end" aria-hidden="true" />
            </Button>
            {mutation.isError ? (
              <Alert variant="error">
                <AlertDescription>注册信息暂不可用，请重新验证邮箱后再试。</AlertDescription>
              </Alert>
            ) : null}
          </form>
        </CardContent>
      </Card>
    </PageSection>
  );
}
