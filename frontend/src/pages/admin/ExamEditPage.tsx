import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, Save, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { Link, useParams } from "react-router-dom";
import { z } from "zod";

import { getErrorMessage } from "@/api/client";
import { getAdminExams, updateAdminExam } from "@/api/exams";
import { StatusPill, type StatusPillVariant } from "@/components/editorial/StatusPill";
import { PageHeader, PageSection, PageShell } from "@/components/page";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { adminPageCopy } from "@/lib/pageCopy";
import { cn } from "@/lib/utils";

const STATUS_OPTIONS = [
  { value: "draft", label: "DRAFT · 草稿", variant: "default" },
  { value: "active", label: "LIVE · 进行中", variant: "success" },
  { value: "archived", label: "ENDED · 已结束", variant: "warning" },
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

function StatusDropdown({
  value,
  onChange,
}: {
  value: ExamEditForm["status"];
  onChange: (next: ExamEditForm["status"]) => void;
}) {
  const [open, setOpen] = useState(false);
  const current = STATUS_OPTIONS.find((status) => status.value === value) ?? STATUS_OPTIONS[0];

  return (
    <div className="relative">
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((previous) => !previous)}
        className="flex h-11 w-full items-center justify-between gap-2 rounded-md border border-hairline bg-canvas px-4 text-body text-ink hover:border-ink"
      >
        <span className="flex items-center gap-2">
          <StatusPill variant={current.variant as StatusPillVariant}>{current.value}</StatusPill>
          {current.label}
        </span>
        <ChevronDown className="size-4 text-muted" aria-hidden="true" />
      </button>
      {open ? (
        <ul
          role="listbox"
          className="absolute z-20 mt-1 w-full overflow-hidden rounded-md border border-hairline bg-surface-elev shadow-pop"
        >
          {STATUS_OPTIONS.map((option) => (
            <li key={option.value}>
              <button
                type="button"
                role="option"
                aria-selected={option.value === value}
                onClick={() => {
                  onChange(option.value);
                  setOpen(false);
                }}
                className={cn(
                  "flex w-full items-center gap-2 px-4 py-2 text-left text-body hover:bg-surface-card",
                  option.value === value && "bg-surface-card",
                )}
              >
                <StatusPill variant={option.variant as StatusPillVariant}>
                  {option.value}
                </StatusPill>
                {option.label}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
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
  const exams = useQuery({ queryKey: ["admin-exams"], queryFn: getAdminExams });
  const currentExam = exams.data?.find((exam) => String(exam.id) === examId);
  const isPublished = currentExam?.status === "active";
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
      void queryClient.invalidateQueries({ queryKey: ["admin-exams"] });
    },
    onError: (error) => {
      setNotice({ tone: "error", message: getErrorMessage(error, "保存考试失败") });
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

  return (
    <PageShell data-testid="exam-edit-shell" density="workbench" width="full" stagger>
      <PageHeader
        eyebrow={adminPageCopy.exams}
        title={`编辑考试 #${examId ?? "-"}`}
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

      <PageSection variant="card" className="grid gap-6 lg:grid-cols-2 lg:p-8">
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
            <Controller
              control={form.control}
              name="status"
              render={({ field }) => (
                <StatusDropdown value={field.value} onChange={field.onChange} />
              )}
            />
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
                切换为 active 会冻结题池、时长、抽题规则和应考名单。
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
              {adminPageCopy.candidates}
            </span>
            <span className="text-body text-ink">应考人员 · 在此页维护本场名单</span>
          </div>
          <Button asChild variant="outline" size="sm">
            <Link to={`/admin/exams/${examId ?? "1"}/candidates`}>管理应考</Link>
          </Button>
        </div>
      </PageSection>
    </PageShell>
  );
}
