import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Save } from "lucide-react";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { Navigate, useNavigate, useOutletContext } from "react-router-dom";
import { z } from "zod";

import { getCandidateProfile, updateCandidateProfile } from "@/api/auth";
import type { CandidateSessionContext } from "@/components/layout/CandidateLayout";
import { PageHeader, PageSection, PageStaleNotice, PageState } from "@/components/page";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Field, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { setCurrentCandidate } from "@/lib/candidateSession";
import { candidatePageCopy, candidatePageText } from "@/lib/pageCopy";
import { candidateDisplayName } from "@/types/candidate";

const schema = z.object({ display_name: z.string().trim().min(1, "请输入姓名") });
type ProfileForm = z.infer<typeof schema>;

export function ProfilePage() {
  const navigate = useNavigate();
  const context = useOutletContext<CandidateSessionContext | null>();
  const candidate = context?.candidate ?? null;
  const query = useQuery({
    queryKey: ["candidate", candidate?.id ?? "anonymous", "profile"],
    queryFn: getCandidateProfile,
    enabled: Boolean(candidate),
    retry: false,
  });
  const form = useForm<ProfileForm>({
    resolver: zodResolver(schema),
    defaultValues: { display_name: candidate ? candidateDisplayName(candidate) : "" },
  });

  useEffect(() => {
    if (query.data) {
      form.reset({ display_name: candidateDisplayName(query.data) });
    }
  }, [form, query.data]);

  const mutation = useMutation({
    mutationFn: updateCandidateProfile,
    onSuccess: (profile) => {
      if (candidate) {
        setCurrentCandidate({
          ...candidate,
          ...profile,
          status: "active",
          token: candidate.token,
          token_expires_at: candidate.token_expires_at,
        });
      }
      query.refetch();
    },
  });

  if (!candidate) {
    return <Navigate to="/login?returnTo=%2Fprofile" replace />;
  }

  const hasLoadError = query.isError && !query.data;
  const hasStaleError = query.isError && Boolean(query.data);

  if (query.isLoading) {
    return <PageState state="loading" rows={2} />;
  }
  if (hasLoadError || !query.data) {
    return (
      <PageState
        state="error"
        eyebrow={candidatePageCopy.error}
        title="账号资料加载失败。"
        description="请稍后重试，或重新登录后再试。"
        onRetry={() => void query.refetch()}
      />
    );
  }

  function handleSubmit(values: ProfileForm) {
    mutation.mutate({ display_name: values.display_name.trim() });
  }

  return (
    <PageSection variant="plain" data-stagger className="w-full max-w-2xl gap-6">
      {hasStaleError ? (
        <PageStaleNotice
          lastSuccessfulAt={query.dataUpdatedAt}
          onRetry={() => query.refetch()}
          retrying={query.isFetching}
        />
      ) : null}
      <PageHeader
        eyebrow={candidatePageCopy.login}
        title={candidatePageText.login.profileTitle}
        description={candidatePageText.login.profileDescription}
      />
      <Card className="bg-canvas shadow-card">
        <CardContent className="p-6 md:p-8">
          <form
            className="flex flex-col gap-6"
            onSubmit={form.handleSubmit(handleSubmit)}
            noValidate
          >
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="profile_email">邮箱（只读）</FieldLabel>
                <Input id="profile_email" value={query.data.email} readOnly aria-readonly="true" />
              </Field>
              <Field data-invalid={form.formState.errors.display_name ? "" : undefined}>
                <FieldLabel htmlFor="profile_display_name">显示姓名</FieldLabel>
                <Input
                  id="profile_display_name"
                  autoComplete="name"
                  aria-invalid={Boolean(form.formState.errors.display_name)}
                  {...form.register("display_name")}
                />
                {form.formState.errors.display_name ? (
                  <FieldError>{form.formState.errors.display_name.message}</FieldError>
                ) : null}
              </Field>
            </FieldGroup>
            <Button type="submit" size="lg" className="self-start" disabled={mutation.isPending}>
              {mutation.isPending ? (
                <Spinner data-icon="inline-start" aria-label="正在保存" />
              ) : (
                <Save data-icon="inline-start" aria-hidden="true" />
              )}
              保存显示姓名
            </Button>
            {mutation.isSuccess ? (
              <Alert variant="success">
                <AlertDescription>资料已更新，正式考试名单保持不变。</AlertDescription>
              </Alert>
            ) : null}
            {mutation.isError ? (
              <Alert variant="error">
                <AlertDescription>资料保存失败，请稍后重试。</AlertDescription>
              </Alert>
            ) : null}
          </form>
        </CardContent>
      </Card>
      <Button
        type="button"
        variant="ghost"
        className="self-start"
        onClick={() => navigate("/exams")}
      >
        返回受邀考试
      </Button>
    </PageSection>
  );
}
