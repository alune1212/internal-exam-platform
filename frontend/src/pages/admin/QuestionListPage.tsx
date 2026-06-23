import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { Edit3, FileUp, Plus, Power, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";
import { useMemo, useState } from "react";

import { getErrorMessage } from "@/api/client";
import {
  createAdminQuestion,
  deleteAdminQuestion,
  getAdminQuestions,
  updateAdminQuestion,
} from "@/api/questions";
import { ReportPage } from "@/components/admin/ReportPage";
import { StatusPill } from "@/components/editorial/StatusPill";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { Question, QuestionOptionPayload, QuestionPayload } from "@/types/question";

type Notice = { tone: "success" | "error"; message: string };
type QuestionFormState = QuestionPayload;

const DEFAULT_OPTIONS: QuestionOptionPayload[] = [
  { label: "A", content: "正确", is_correct: true, sort_order: 1 },
  { label: "B", content: "错误", is_correct: false, sort_order: 2 },
  { label: "C", content: "", is_correct: false, sort_order: 3 },
  { label: "D", content: "", is_correct: false, sort_order: 4 },
  { label: "E", content: "", is_correct: false, sort_order: 5 },
  { label: "F", content: "", is_correct: false, sort_order: 6 },
];

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

  const invalidateQuestions = () => {
    void queryClient.invalidateQueries({ queryKey: ["admin-questions"] });
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
    setEditing(null);
    setForm(emptyForm());
    setDialogOpen(true);
  };

  const openEdit = (question: Question) => {
    setEditing(question);
    setForm(formFromQuestion(question));
    setDialogOpen(true);
  };

  const columns = useMemo<ColumnDef<Question>[]>(
    () => [
      {
        accessorKey: "id",
        header: "ID",
        cell: ({ row }) => <span className="font-mono text-sm">{row.original.id}</span>,
        meta: { mobilePriority: false },
      },
      {
        accessorKey: "question_type",
        header: "TYPE",
        meta: { mobileLabel: "TYPE" },
      },
      {
        accessorKey: "stem",
        header: "STEM",
        cell: ({ row }) => <span className="line-clamp-1 max-w-md">{row.original.stem}</span>,
        meta: { mobilePriority: "primary", mobileLabel: "STEM" },
      },
      {
        accessorKey: "score",
        header: "SCORE",
        cell: ({ row }) => (
          <span className="font-mono text-sm tabular-nums">{row.original.score}</span>
        ),
        meta: { mobileLabel: "SCORE" },
      },
      {
        accessorKey: "status",
        header: "STATUS",
        cell: ({ row }) => (
          <StatusPill variant={row.original.status === "active" ? "success" : "warning"}>
            {row.original.status}
          </StatusPill>
        ),
        meta: { mobileLabel: "STATUS" },
      },
      {
        id: "actions",
        header: "",
        cell: ({ row }) => (
          <div className="flex justify-end gap-2">
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
          </div>
        ),
        meta: { mobileLabel: "操作" },
      },
    ],
    [statusMutation],
  );

  return (
    <div className="flex flex-col gap-4">
      <ReportPage
        title="题库管理"
        chapterLabel="CHAPTER 03 · LIBRARY"
        description="所有题目的列表与状态。点击右上「导入题库」批量上传 Excel。"
        queryKey="admin-questions"
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
      <NoticeText notice={notice} />

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-3xl">
          <DialogHeader chapter="CHAPTER 03 · LIBRARY">
            <DialogTitle>{editing ? "编辑题目" : "新增题目"}</DialogTitle>
            <DialogDescription>填写题干、选项和正确答案后保存。</DialogDescription>
          </DialogHeader>
          <form
            className="grid gap-4 md:grid-cols-2"
            onSubmit={(event) => {
              event.preventDefault();
              saveMutation.mutate(cleanForm(form));
            }}
          >
            <div className="flex flex-col gap-2 md:col-span-2">
              <Label htmlFor="stem">题干</Label>
              <Input
                id="stem"
                value={form.stem}
                onChange={(event) => setForm({ ...form, stem: event.target.value })}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="question_type">题型</Label>
              <select
                id="question_type"
                className="h-11 rounded-md border border-hairline bg-canvas px-3"
                value={form.question_type}
                onChange={(event) => setForm({ ...form, question_type: event.target.value })}
              >
                <option value="single">single</option>
                <option value="multiple">multiple</option>
                <option value="judge">judge</option>
              </select>
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="score">分值</Label>
              <Input
                id="score"
                type="number"
                min={0.5}
                step={0.5}
                value={form.score}
                onChange={(event) => setForm({ ...form, score: Number(event.target.value) })}
              />
            </div>
            {(["category_1", "category_2", "difficulty", "status"] as const).map((field) => (
              <div key={field} className="flex flex-col gap-2">
                <Label htmlFor={field}>{field}</Label>
                <Input
                  id={field}
                  value={String(form[field] ?? "")}
                  onChange={(event) => setForm({ ...form, [field]: event.target.value })}
                />
              </div>
            ))}
            <div className="flex flex-col gap-2 md:col-span-2">
              <Label htmlFor="analysis">解析</Label>
              <textarea
                id="analysis"
                rows={3}
                className="rounded-md border border-hairline bg-canvas p-3 text-body-sm"
                value={form.analysis ?? ""}
                onChange={(event) => setForm({ ...form, analysis: event.target.value })}
              />
            </div>
            <div className="flex flex-col gap-3 md:col-span-2">
              <span className="text-caption uppercase tracking-[0.16em] text-muted">OPTIONS</span>
              {form.options.map((option, index) => (
                <div key={option.label} className="grid gap-2 md:grid-cols-[80px_1fr_120px]">
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
                  <label className="flex items-center gap-2 text-body-sm">
                    <input
                      type="checkbox"
                      checked={option.is_correct}
                      onChange={(event) => {
                        const next = [...form.options];
                        next[index] = { ...option, is_correct: event.target.checked };
                        setForm({ ...form, options: next });
                      }}
                    />
                    正确答案
                  </label>
                </div>
              ))}
            </div>
            <DialogFooter className="md:col-span-2">
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                取消
              </Button>
              <Button type="submit" disabled={saveMutation.isPending}>
                {saveMutation.isPending ? "保存中" : "保存题目"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={deleteTarget !== null} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader chapter="CHAPTER 03 · LIBRARY">
            <DialogTitle>删除题目</DialogTitle>
            <DialogDescription>
              删除只影响当前题库记录，已生成的考试快照不会改变。
            </DialogDescription>
          </DialogHeader>
          <p className="text-body text-ink">{deleteTarget?.stem}</p>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setDeleteTarget(null)}>
              取消
            </Button>
            <Button
              type="button"
              disabled={deleteMutation.isPending}
              onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
            >
              确认删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
