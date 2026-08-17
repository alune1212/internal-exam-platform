import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { Edit3, FileUp, Plus, Power, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";
import { useMemo, useRef, useState } from "react";

import { getErrorMessage } from "@/api/client";
import {
  createAdminQuestion,
  deleteAdminQuestion,
  getAdminQuestions,
  updateAdminQuestion,
} from "@/api/questions";
import { ReportPage } from "@/components/admin/ReportPage";
import { StatusPill } from "@/components/editorial/StatusPill";
import { PageActions } from "@/components/page";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Field, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  adminPageCopy,
  adminPageText,
  adminTableCopy,
  formatQuestionStatus,
  formatQuestionTypeLabel,
} from "@/lib/pageCopy";
import type { Question, QuestionOptionPayload, QuestionPayload } from "@/types/question";

type Notice = { tone: "success" | "error"; message: string };
type QuestionFormState = QuestionPayload;
type QuestionStatusValue = "active" | "inactive";

const DEFAULT_OPTIONS: QuestionOptionPayload[] = [
  { label: "A", content: "正确", is_correct: true, sort_order: 1 },
  { label: "B", content: "错误", is_correct: false, sort_order: 2 },
  { label: "C", content: "", is_correct: false, sort_order: 3 },
  { label: "D", content: "", is_correct: false, sort_order: 4 },
  { label: "E", content: "", is_correct: false, sort_order: 5 },
  { label: "F", content: "", is_correct: false, sort_order: 6 },
];

const QUESTION_STATUS_OPTIONS: QuestionStatusValue[] = ["active", "inactive"];

const OPTIONAL_FIELD_LABELS = {
  category_1: "一级分类",
  category_2: "二级分类",
  difficulty: "难度",
} as const;

function emptyForm(): QuestionFormState {
  return {
    question_type: "single",
    stem: "",
    analysis: "",
    category_1: "",
    category_2: "",
    difficulty: "",
    score: 1,
    status: "active",
    source: "",
    source_no: "",
    remark: "",
    options: DEFAULT_OPTIONS,
  };
}

function formFromQuestion(question: Question): QuestionFormState {
  const options = DEFAULT_OPTIONS.map((fallback) => {
    const existing = question.options.find((option) => option.label === fallback.label);
    return existing
      ? {
          label: existing.label,
          content: existing.content,
          is_correct: existing.is_correct,
          sort_order: existing.sort_order,
        }
      : fallback;
  });
  return {
    question_type: question.question_type,
    stem: question.stem,
    analysis: question.analysis ?? "",
    category_1: question.category_1 ?? "",
    category_2: question.category_2 ?? "",
    difficulty: question.difficulty ?? "",
    score: question.score,
    status: question.status,
    source: question.source ?? "",
    source_no: question.source_no ?? "",
    remark: question.remark ?? "",
    options,
  };
}

function cleanForm(form: QuestionFormState): QuestionPayload {
  const options =
    form.question_type === "judge"
      ? form.options.slice(0, 2).map((option, index) => ({
          ...option,
          content: index === 0 ? option.content || "正确" : option.content || "错误",
        }))
      : form.options.filter((option) => option.content.trim());
  return {
    ...form,
    stem: form.stem.trim(),
    score: Number(form.score),
    options,
  };
}

function statusActionPending(
  mutation: { isPending: boolean; variables?: Question },
  questionId: number,
) {
  return mutation.isPending && mutation.variables?.id === questionId;
}

function NoticeText({ notice }: { notice: Notice | null }) {
  if (!notice) return null;
  return (
    <Alert variant={notice.tone === "success" ? "success" : "error"}>
      <AlertDescription>{notice.message}</AlertDescription>
    </Alert>
  );
}

export function QuestionListPage() {
  const queryClient = useQueryClient();
  const [notice, setNotice] = useState<Notice | null>(null);
  const [editing, setEditing] = useState<Question | null>(null);
  const [form, setForm] = useState<QuestionFormState>(emptyForm());
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Question | null>(null);
  const formDialogReturnFocusRef = useRef<HTMLElement | null>(null);

  const invalidateQuestions = () => {
    void queryClient.invalidateQueries({ queryKey: ["admin", "questions"] });
  };

  const saveMutation = useMutation({
    mutationFn: (values: QuestionPayload) =>
      editing ? updateAdminQuestion(editing.id, values) : createAdminQuestion(values),
    onSuccess: () => {
      setNotice({ tone: "success", message: "题目已保存。" });
      setDialogOpen(false);
      setEditing(null);
      invalidateQuestions();
    },
    onError: (error) =>
      setNotice({ tone: "error", message: getErrorMessage(error, "保存题目失败") }),
  });
  const statusMutation = useMutation({
    mutationFn: (question: Question) =>
      updateAdminQuestion(question.id, {
        status: question.status === "active" ? "inactive" : "active",
      }),
    onSuccess: () => {
      setNotice({ tone: "success", message: "题目状态已更新。" });
      invalidateQuestions();
    },
    onError: (error) =>
      setNotice({ tone: "error", message: getErrorMessage(error, "更新状态失败") }),
  });
  const deleteMutation = useMutation({
    mutationFn: (questionId: number) => deleteAdminQuestion(questionId),
    onSuccess: () => {
      setNotice({ tone: "success", message: "题目已删除。" });
      setDeleteTarget(null);
      invalidateQuestions();
    },
    onError: (error) =>
      setNotice({ tone: "error", message: getErrorMessage(error, "删除题目失败") }),
  });

  const openCreate = () => {
    formDialogReturnFocusRef.current =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setNotice(null);
    setEditing(null);
    setForm(emptyForm());
    setDialogOpen(true);
  };

  const openEdit = (question: Question) => {
    formDialogReturnFocusRef.current =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setNotice(null);
    setEditing(question);
    setForm(formFromQuestion(question));
    setDialogOpen(true);
  };

  const columns = useMemo<ColumnDef<Question>[]>(
    () => [
      {
        accessorKey: "id",
        header: adminTableCopy.id,
        cell: ({ row }) => <span className="font-mono text-body-sm">{row.original.id}</span>,
        meta: { mobilePriority: false },
      },
      {
        accessorKey: "question_type",
        header: adminTableCopy.questionType,
        cell: ({ row }) => formatQuestionTypeLabel(row.original.question_type),
        meta: { mobileLabel: adminTableCopy.questionType },
      },
      {
        accessorKey: "stem",
        header: adminTableCopy.stem,
        cell: ({ row }) => (
          <span className="line-clamp-2 block min-w-0 break-words">{row.original.stem}</span>
        ),
        meta: { mobilePriority: "primary", mobileLabel: adminTableCopy.stem },
      },
      {
        accessorKey: "score",
        header: adminTableCopy.score,
        cell: ({ row }) => (
          <span className="font-mono text-body-sm tabular-nums">{row.original.score}</span>
        ),
        meta: { mobileLabel: adminTableCopy.score },
      },
      {
        accessorKey: "status",
        header: adminTableCopy.status,
        cell: ({ row }) => (
          <StatusPill variant={row.original.status === "active" ? "success" : "warning"}>
            {formatQuestionStatus(row.original.status)}
          </StatusPill>
        ),
        meta: { mobileLabel: adminTableCopy.status },
      },
      {
        id: "actions",
        header: adminTableCopy.action,
        cell: ({ row }) => (
          <PageActions placement="card" aria-label="题目操作" className="justify-end">
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => openEdit(row.original)}
            >
              <Edit3 data-icon="inline-start" />
              编辑
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              pending={statusActionPending(statusMutation, row.original.id)}
              onClick={() => statusMutation.mutate(row.original)}
            >
              <Power data-icon="inline-start" />
              {row.original.status === "active" ? "停用" : "启用"}
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => setDeleteTarget(row.original)}
            >
              <Trash2 data-icon="inline-start" />
              删除
            </Button>
          </PageActions>
        ),
        meta: { mobileLabel: "操作" },
      },
    ],
    [statusMutation],
  );

  return (
    <div className="flex flex-col gap-4">
      <ReportPage
        title={adminPageText.questionBank.title}
        chapterLabel={adminPageCopy.library}
        description={adminPageText.questionBank.description}
        queryKey={["admin", "questions"]}
        queryFn={getAdminQuestions}
        columns={columns}
        actions={
          <>
            <Button type="button" size="sm" onClick={openCreate}>
              <Plus data-icon="inline-start" />
              新增题目
            </Button>
            <Button asChild size="sm" variant="outline">
              <Link to="/admin/questions/import">
                <FileUp data-icon="inline-start" />
                导入题库
              </Link>
            </Button>
          </>
        }
      />
      <NoticeText notice={!dialogOpen && !deleteTarget ? notice : null} />

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent
          className="sm:max-w-3xl"
          onCloseAutoFocus={(event) => {
            const returnFocus = formDialogReturnFocusRef.current;
            if (returnFocus?.isConnected) {
              event.preventDefault();
              returnFocus.focus();
            }
          }}
        >
          <DialogHeader>
            <DialogTitle>{editing ? "编辑题目" : "新增题目"}</DialogTitle>
            <DialogDescription>填写题干、选项和正确答案后保存。</DialogDescription>
          </DialogHeader>
          <NoticeText notice={saveMutation.isError ? notice : null} />
          <form
            data-question-form=""
            aria-busy={saveMutation.isPending || undefined}
            className="grid gap-4 md:grid-cols-2"
            onSubmit={(event) => {
              event.preventDefault();
              saveMutation.mutate(cleanForm(form));
            }}
          >
            <Field className="md:col-span-2">
              <FieldLabel htmlFor="stem">题干</FieldLabel>
              <Input
                id="stem"
                value={form.stem}
                onChange={(event) => setForm({ ...form, stem: event.target.value })}
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="question_type">题型</FieldLabel>
              <Select
                id="question_type"
                value={form.question_type}
                onChange={(event) => setForm({ ...form, question_type: event.target.value })}
              >
                <option value="single">{formatQuestionTypeLabel("single")}</option>
                <option value="multiple">{formatQuestionTypeLabel("multiple")}</option>
                <option value="judge">{formatQuestionTypeLabel("judge")}</option>
              </Select>
            </Field>
            <Field>
              <FieldLabel htmlFor="score">分值</FieldLabel>
              <Input
                id="score"
                type="number"
                min={0.5}
                step={0.5}
                value={form.score}
                onChange={(event) => setForm({ ...form, score: Number(event.target.value) })}
              />
            </Field>
            {(["category_1", "category_2", "difficulty"] as const).map((field) => (
              <Field key={field}>
                <FieldLabel htmlFor={field}>{OPTIONAL_FIELD_LABELS[field]}</FieldLabel>
                <Input
                  id={field}
                  value={String(form[field] ?? "")}
                  onChange={(event) => setForm({ ...form, [field]: event.target.value })}
                />
              </Field>
            ))}
            <Field>
              <FieldLabel htmlFor="status">题目状态</FieldLabel>
              <Select
                id="status"
                value={form.status}
                onChange={(event) => setForm({ ...form, status: event.target.value })}
              >
                {QUESTION_STATUS_OPTIONS.map((status) => (
                  <option key={status} value={status}>
                    {formatQuestionStatus(status)}
                  </option>
                ))}
              </Select>
            </Field>
            <Field className="md:col-span-2">
              <FieldLabel htmlFor="analysis">解析</FieldLabel>
              <Textarea
                id="analysis"
                rows={3}
                className="min-h-24"
                value={form.analysis ?? ""}
                onChange={(event) => setForm({ ...form, analysis: event.target.value })}
              />
            </Field>
            <section
              aria-labelledby="question-options-heading"
              data-form-section="options"
              className="flex min-w-0 flex-col gap-3 md:col-span-2"
            >
              <h3
                id="question-options-heading"
                className="font-display text-display-sm font-semibold text-ink"
              >
                选项与答案
              </h3>
              {form.options
                .slice(0, form.question_type === "judge" ? 2 : form.options.length)
                .map((option, index) => (
                  <div
                    key={option.label}
                    className="grid min-w-0 gap-2 md:grid-cols-[80px_1fr_120px]"
                  >
                    <Input value={option.label} readOnly aria-label={`选项 ${option.label} 标签`} />
                    <Input
                      value={option.content}
                      aria-label={`选项 ${option.label} 内容`}
                      onChange={(event) => {
                        const next = [...form.options];
                        next[index] = { ...option, content: event.target.value };
                        setForm({ ...form, options: next });
                      }}
                    />
                    <FieldLabel
                      htmlFor={`option-${option.label}-correct`}
                      className="flex min-h-action items-center gap-2 text-body-sm"
                    >
                      <input
                        id={`option-${option.label}-correct`}
                        type="checkbox"
                        checked={option.is_correct}
                        onChange={(event) => {
                          const next = [...form.options];
                          next[index] = { ...option, is_correct: event.target.checked };
                          setForm({ ...form, options: next });
                        }}
                      />
                      <span>正确答案</span>
                    </FieldLabel>
                  </div>
                ))}
            </section>
            <PageActions placement="form" aria-label="题目表单操作" className="md:col-span-2">
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                取消
              </Button>
              <Button type="submit" pending={saveMutation.isPending}>
                {saveMutation.isPending ? "保存中" : "保存题目"}
              </Button>
            </PageActions>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={deleteTarget !== null} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>删除题目</DialogTitle>
            <DialogDescription>
              删除只影响当前题库记录，已生成的考试快照不会改变。
            </DialogDescription>
          </DialogHeader>
          <p className="min-w-0 break-words text-body text-ink">{deleteTarget?.stem}</p>
          <PageActions placement="destructive" aria-label="删除题目操作">
            <Button type="button" variant="outline" onClick={() => setDeleteTarget(null)}>
              取消
            </Button>
            <Button
              type="button"
              pending={deleteMutation.isPending}
              onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
            >
              确认删除
            </Button>
          </PageActions>
        </DialogContent>
      </Dialog>
    </div>
  );
}
