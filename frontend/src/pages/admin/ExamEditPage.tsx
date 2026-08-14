import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, Save, ShieldCheck, Upload, X } from "lucide-react";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useParams } from "react-router-dom";
import { z } from "zod";

import { getErrorMessage } from "@/api/client";
import {
  getAdminExams,
  getPublicationReadiness,
  publishAdminExam,
  releaseResultDetails,
  updateAdminExam,
} from "@/api/exams";
import { PageHeader, PageSection, PageShell, PageState } from "@/components/page";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  adminPageCopy,
  adminPageText,
  formatAdminExamEditTitle,
  formatExamStatus,
} from "@/lib/pageCopy";
import { adminKeys } from "@/lib/queryKeys";

const STATUS_OPTIONS = [
  { value: "draft", label: formatExamStatus("draft") },
  { value: "active", label: formatExamStatus("active") },
  { value: "archived", label: formatExamStatus("archived") },
] as const;

const schema = z
  .object({
    title: z.string().min(1, "请输入考试名称"),
    duration_minutes: z.coerce.number().int().min(1, "时长必须 >= 1 分钟"),
    status: z.enum(["draft", "active", "archived"]),
    question_rule_json: z.string().min(2, "抽题规则不能为空"),
    available_from: z.string(),
    available_until: z.string(),
  })
  .superRefine((values, context) => {
    if (!values.available_from || !values.available_until) {
      return;
    }
    if (new Date(values.available_from) >= new Date(values.available_until)) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["available_until"],
        message: "结束时间必须晚于开始时间",
      });
    }
  });

type ExamEditForm = z.infer<typeof schema>;

const DEFAULT_FIXED_RULE = {
  question_count: 50,
  total_score: 100,
  pass_score: 60,
  mode: "fixed_paper",
  type_counts: { single: 30, multiple: 10, judge: 10 },
};

function formatQuestionRule(rule: Record<string, unknown>) {
  return JSON.stringify(Object.keys(rule).length ? rule : DEFAULT_FIXED_RULE, null, 2);
}

function normalizeStatus(status: string): ExamEditForm["status"] {
  return STATUS_OPTIONS.some((option) => option.value === status)
    ? (status as ExamEditForm["status"])
    : "draft";
}

function toDateTimeLocalValue(value?: string | null) {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  const localDate = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return localDate.toISOString().slice(0, 16);
}

function fromDateTimeLocalValue(value: string) {
  return value ? new Date(value).toISOString() : null;
}

export function ExamEditPage() {
  const { examId } = useParams();
  const queryClient = useQueryClient();
  const form = useForm<ExamEditForm>({
    resolver: zodResolver(schema),
    defaultValues: {
      title: "临时考试",
      duration_minutes: 60,
      status: "draft",
      question_rule_json: formatQuestionRule(DEFAULT_FIXED_RULE),
      available_from: "",
      available_until: "",
    },
  });
  const exams = useQuery({ queryKey: ["admin", "exams"], queryFn: getAdminExams });
  const currentExam = exams.data?.find((exam) => String(exam.id) === examId);
  const pageTitle = formatAdminExamEditTitle(examId);
  const isPublished = currentExam?.status === "active";
  const isDraft = currentExam?.status === "draft";
  const [publishConfirmation, setPublishConfirmation] = useState("");
  const [releaseConfirmation, setReleaseConfirmation] = useState("");
  const [notice, setNotice] = useState<{ tone: "success" | "error"; message: string } | null>(null);
  const mutation = useMutation({
    mutationFn: (values: ExamEditForm) => {
      if (!examId) {
        throw new Error("missing exam id");
      }
      const payload = {
        title: values.title,
        status: values.status,
        available_from: fromDateTimeLocalValue(values.available_from),
        available_until: fromDateTimeLocalValue(values.available_until),
      };
      if (!isPublished) {
        let questionRule: Record<string, unknown>;
        try {
          questionRule = JSON.parse(values.question_rule_json) as Record<string, unknown>;
        } catch {
          form.setError("question_rule_json", { message: "抽题规则必须是合法 JSON" });
          throw new Error("invalid question rule json");
        }
        return updateAdminExam(examId, {
          ...payload,
          duration_minutes: values.duration_minutes,
          question_rule: questionRule,
        });
      }
      return updateAdminExam(examId, payload);
    },
    onSuccess: () => {
      setNotice({ tone: "success", message: "考试配置已保存。" });
      void queryClient.invalidateQueries({ queryKey: ["admin", "exams"] });
      if (examId) {
        void queryClient.invalidateQueries({ queryKey: adminKeys.examWorkspace(examId) });
      }
    },
    onError: (error) => {
      setNotice({ tone: "error", message: getErrorMessage(error, "保存考试失败") });
    },
  });
  const readiness = useQuery({
    queryKey: ["admin", "exams", examId, "publication-readiness"],
    queryFn: () => {
      if (!examId) {
        throw new Error("missing exam id");
      }
      return getPublicationReadiness(examId);
    },
    enabled: Boolean(examId && isDraft),
  });
  const publishMutation = useMutation({
    mutationFn: () => {
      if (!examId || !currentExam) {
        throw new Error("missing exam");
      }
      return publishAdminExam(examId, publishConfirmation);
    },
    onSuccess: () => {
      setPublishConfirmation("");
      setNotice({ tone: "success", message: "考试已发布，题池与应考名单已冻结。" });
      void queryClient.invalidateQueries({ queryKey: ["admin", "exams"] });
      void queryClient.invalidateQueries({
        queryKey: ["admin", "exams", examId, "publication-readiness"],
      });
      if (examId) {
        void queryClient.invalidateQueries({ queryKey: adminKeys.examWorkspace(examId) });
      }
    },
    onError: (error) => {
      setNotice({ tone: "error", message: getErrorMessage(error, "发布考试失败") });
      void readiness.refetch();
    },
  });
  const releaseMutation = useMutation({
    mutationFn: () => {
      if (!examId || !currentExam) {
        throw new Error("missing exam");
      }
      return releaseResultDetails(examId, releaseConfirmation);
    },
    onSuccess: () => {
      setReleaseConfirmation("");
      setNotice({ tone: "success", message: "答案与解析已一次性发布。" });
      void queryClient.invalidateQueries({ queryKey: ["admin", "exams"] });
      if (examId) {
        void queryClient.invalidateQueries({ queryKey: adminKeys.examWorkspace(examId) });
      }
    },
    onError: (error) => {
      setNotice({ tone: "error", message: getErrorMessage(error, "发布答案解析失败") });
    },
  });

  useEffect(() => {
    if (!currentExam) {
      return;
    }
    form.reset({
      title: currentExam.title,
      duration_minutes: currentExam.duration_minutes,
      status: normalizeStatus(currentExam.status),
      question_rule_json: formatQuestionRule(currentExam.question_rule),
      available_from: toDateTimeLocalValue(currentExam.available_from),
      available_until: toDateTimeLocalValue(currentExam.available_until),
    });
  }, [currentExam, form]);

  if (exams.isLoading) {
    return (
      <PageShell data-testid="exam-edit-shell" density="workbench" width="full" stagger>
        <PageHeader eyebrow={adminPageCopy.exams} title={pageTitle} />
        <PageSection variant="card">
          <PageState
            state="loading"
            rows={4}
            className="border-0 bg-transparent py-8 shadow-none"
          />
        </PageSection>
      </PageShell>
    );
  }

  if (exams.isError) {
    return (
      <PageShell data-testid="exam-edit-shell" density="workbench" width="full" stagger>
        <PageHeader eyebrow={adminPageCopy.exams} title={pageTitle} />
        <PageSection variant="card">
          <PageState
            state="error"
            eyebrow={adminPageCopy.error}
            title={adminPageText.exams.errorTitle}
            description="请稍后重试，或确认后台服务是否可用。"
            className="border-0 bg-transparent py-8 shadow-none"
          />
        </PageSection>
      </PageShell>
    );
  }

  if (!currentExam) {
    return (
      <PageShell data-testid="exam-edit-shell" density="workbench" width="full" stagger>
        <PageHeader eyebrow={adminPageCopy.exams} title={pageTitle} />
        <PageSection variant="card">
          <PageState
            state="error"
            eyebrow={adminPageCopy.error}
            title="未找到考试。"
            description="请返回考试列表确认考试是否仍然存在。"
            className="border-0 bg-transparent py-8 shadow-none"
          />
        </PageSection>
      </PageShell>
    );
  }

  return (
    <PageShell data-testid="exam-edit-shell" density="workbench" width="full" stagger>
      <PageHeader
        eyebrow={adminPageCopy.exams}
        title={pageTitle}
        actions={
          <>
            <Button asChild variant="outline" size="sm">
              <Link to="/admin/exams">
                <X data-icon="inline-start" />
                取消
              </Link>
            </Button>
            <Button
              type="button"
              size="sm"
              disabled={mutation.isPending}
              onClick={form.handleSubmit((values) => mutation.mutate(values))}
            >
              <Save data-icon="inline-start" />
              {mutation.isPending ? "保存中" : "保存配置"}
            </Button>
          </>
        }
      />

      <PageSection id="archive" variant="card" className="grid gap-6 lg:grid-cols-2 lg:p-8">
        {notice ? (
          <Alert
            variant={notice.tone === "success" ? "success" : "error"}
            className="lg:col-span-2"
          >
            <AlertDescription>{notice.message}</AlertDescription>
          </Alert>
        ) : null}
        <FieldGroup className="contents">
          <Field>
            <FieldLabel htmlFor="title">考试名称 · Title</FieldLabel>
            <Input id="title" {...form.register("title")} />
          </Field>
          <Field data-disabled={isPublished ? "" : undefined}>
            <FieldLabel htmlFor="duration_minutes">时长（分钟）· Duration</FieldLabel>
            <Input
              id="duration_minutes"
              type="number"
              min={1}
              disabled={isPublished}
              {...form.register("duration_minutes", { valueAsNumber: true })}
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="status">状态 · Status</FieldLabel>
            <select
              id="status"
              className="h-11 w-full rounded-md border border-hairline bg-canvas px-3.5 text-body text-ink outline-none transition-colors duration-150 ease-out focus-visible:border-ink focus-visible:ring-1 focus-visible:ring-ink"
              {...form.register("status")}
            >
              {STATUS_OPTIONS.filter((option) => {
                if (currentExam.status === "draft") return option.value === "draft";
                if (currentExam.status === "active") return option.value !== "draft";
                return option.value === "archived";
              }).map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </Field>
          <Field>
            <FieldLabel htmlFor="available_from">开放开始时间 · Available From</FieldLabel>
            <Input id="available_from" type="datetime-local" {...form.register("available_from")} />
          </Field>
          <Field data-invalid={form.formState.errors.available_until ? "" : undefined}>
            <FieldLabel htmlFor="available_until">开放结束时间 · Available Until</FieldLabel>
            <Input
              id="available_until"
              type="datetime-local"
              {...form.register("available_until")}
            />
            {form.formState.errors.available_until ? (
              <FieldError>{form.formState.errors.available_until.message}</FieldError>
            ) : null}
          </Field>
          <Field
            className="lg:col-span-2"
            data-disabled={isPublished ? "" : undefined}
            data-invalid={form.formState.errors.question_rule_json ? "" : undefined}
          >
            <FieldLabel htmlFor="question_rule_json">抽题规则 · JSON</FieldLabel>
            <Textarea
              id="question_rule_json"
              rows={8}
              spellCheck={false}
              disabled={isPublished}
              className="font-mono"
              aria-invalid={Boolean(form.formState.errors.question_rule_json)}
              {...form.register("question_rule_json")}
            />
            {isPublished ? (
              <FieldDescription>
                考试已发布，题池、时长、抽题规则和应考名单已冻结。
              </FieldDescription>
            ) : (
              <FieldDescription>
                切换为已发布会冻结题池、时长、抽题规则和应考名单。
              </FieldDescription>
            )}
            {form.formState.errors.question_rule_json ? (
              <FieldError>{form.formState.errors.question_rule_json.message}</FieldError>
            ) : null}
          </Field>
        </FieldGroup>
        <div className="flex flex-col gap-3 rounded-md bg-surface-card p-4 md:flex-row md:items-center md:justify-between lg:col-span-2">
          <div className="flex flex-col gap-1">
            <span className="text-caption uppercase tracking-[0.16em] text-muted">
              {adminPageCopy.roster}
            </span>
            <span className="text-body text-ink">应考名单 · 在此页维护本场考试名单</span>
          </div>
          <Button asChild variant="outline" size="sm">
            <Link to={`/admin/exams/${examId ?? "1"}/candidates`}>管理名单</Link>
          </Button>
        </div>
      </PageSection>

      {isDraft ? (
        <PageSection
          id="publish"
          variant="card"
          aria-labelledby="publication-readiness-title"
          className="grid gap-5 lg:p-8"
        >
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex flex-col gap-1">
              <span className="text-caption uppercase tracking-[0.16em] text-muted">
                RELEASE GATE · 发布门禁
              </span>
              <h2
                id="publication-readiness-title"
                className="font-display text-display-sm text-ink"
              >
                发布预检
              </h2>
              <p className="text-body-sm text-muted">
                保存配置后刷新预检；只有全部阻断项通过，才可按考试名称确认发布。
              </p>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={readiness.isFetching}
              onClick={() => void readiness.refetch()}
            >
              <RefreshCw data-icon="inline-start" />
              {readiness.isFetching ? "检查中" : "刷新预检"}
            </Button>
          </div>

          {readiness.isLoading ? (
            <PageState
              state="loading"
              rows={2}
              className="border-0 bg-transparent py-4 shadow-none"
            />
          ) : readiness.isError ? (
            <Alert variant="error">
              <AlertDescription>发布预检读取失败；当前禁止发布，请刷新后重试。</AlertDescription>
            </Alert>
          ) : readiness.data ? (
            <div className="grid gap-4">
              <Alert variant={readiness.data.ready ? "success" : "error"}>
                <AlertDescription>
                  {readiness.data.ready
                    ? `预检通过：${readiness.data.roster_count} 名应考人员，预计冻结 ${readiness.data.prospective_pool_count} 道题。`
                    : `存在 ${readiness.data.blockers.length} 个阻断项，尚不能发布。`}
                </AlertDescription>
              </Alert>
              {readiness.data.blockers.length ? (
                <div aria-label="发布阻断项" className="rounded-md border border-error p-4">
                  <h3 className="text-caption font-semibold uppercase tracking-[0.14em] text-error">
                    BLOCKERS · 阻断项
                  </h3>
                  <ul className="mt-3 list-disc space-y-2 pl-5 text-body-sm text-ink">
                    {readiness.data.blockers.map((issue) => (
                      <li key={issue.code}>{issue.message}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {readiness.data.warnings.length ? (
                <div aria-label="发布警告" className="rounded-md border border-warning p-4">
                  <h3 className="text-caption font-semibold uppercase tracking-[0.14em] text-warning">
                    WARNINGS · 警告
                  </h3>
                  <ul className="mt-3 list-disc space-y-2 pl-5 text-body-sm text-ink">
                    {readiness.data.warnings.map((issue) => (
                      <li key={issue.code}>{issue.message}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              <Field
                data-invalid={
                  publishConfirmation && publishConfirmation !== currentExam.title ? "" : undefined
                }
              >
                <FieldLabel htmlFor="publish_confirmation">
                  输入完整考试名称确认发布 · {currentExam.title}
                </FieldLabel>
                <Input
                  id="publish_confirmation"
                  value={publishConfirmation}
                  autoComplete="off"
                  onChange={(event) => setPublishConfirmation(event.target.value)}
                />
                <FieldDescription>
                  发布不可通过状态下拉框完成；服务端会在同一事务中重新预检后再冻结题池。
                </FieldDescription>
              </Field>
              <div className="flex justify-end">
                <Button
                  type="button"
                  disabled={
                    !readiness.data.ready ||
                    publishConfirmation !== currentExam.title ||
                    publishMutation.isPending
                  }
                  onClick={() => publishMutation.mutate()}
                >
                  {readiness.data.ready ? (
                    <Upload data-icon="inline-start" />
                  ) : (
                    <ShieldCheck data-icon="inline-start" />
                  )}
                  {publishMutation.isPending ? "发布中" : "确认发布"}
                </Button>
              </div>
            </div>
          ) : null}
        </PageSection>
      ) : null}

      {!isDraft ? (
        <PageSection
          id="result-release"
          variant="card"
          aria-labelledby="result-release-title"
          className="grid gap-5 lg:p-8"
        >
          <div className="flex flex-col gap-1">
            <span className="text-caption uppercase tracking-[0.16em] text-muted">
              RESULT RELEASE · 结果发布
            </span>
            <h2 id="result-release-title" className="font-display text-display-sm text-ink">
              答案与解析
            </h2>
            <p className="text-body-sm text-muted">
              成绩与通过状态交卷后即可查看；答案解析仅可在全部记录结束后手动发布一次。
            </p>
          </div>
          {currentExam.result_details_released_at ? (
            <Alert variant="success">
              <AlertDescription>
                已于 {new Date(currentExam.result_details_released_at).toLocaleString()} 由
                {` ${currentExam.result_details_released_by ?? "具名操作员"} `}
                发布；该操作不可撤销或重复。
              </AlertDescription>
            </Alert>
          ) : (
            <div className="grid gap-4">
              <Alert variant="warning">
                <AlertDescription>
                  若仍有进行中的记录，服务端会拒绝发布。发布后考生可查看题目、正确答案和解析。
                </AlertDescription>
              </Alert>
              <Field
                data-invalid={
                  releaseConfirmation && releaseConfirmation !== currentExam.title ? "" : undefined
                }
              >
                <FieldLabel htmlFor="release_confirmation">
                  输入完整考试名称确认发布 · {currentExam.title}
                </FieldLabel>
                <Input
                  id="release_confirmation"
                  value={releaseConfirmation}
                  autoComplete="off"
                  onChange={(event) => setReleaseConfirmation(event.target.value)}
                />
                <FieldDescription>发布后不可撤销，也不能再次发布。</FieldDescription>
              </Field>
              <div className="flex justify-end">
                <Button
                  type="button"
                  disabled={releaseConfirmation !== currentExam.title || releaseMutation.isPending}
                  onClick={() => releaseMutation.mutate()}
                >
                  <ShieldCheck data-icon="inline-start" />
                  {releaseMutation.isPending ? "发布中" : "发布答案与解析"}
                </Button>
              </div>
            </div>
          )}
        </PageSection>
      ) : null}
    </PageShell>
  );
}
