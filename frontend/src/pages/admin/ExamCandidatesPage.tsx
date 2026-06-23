import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { Download, FileUp, RotateCcw, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import {
  createRetakeGrant,
  getAdminExams,
  getExamCandidates,
  importExamCandidates,
  removeExamCandidate,
} from "@/api/exams";
import { getErrorMessage } from "@/api/client";
import { downloadImportFailureReport, downloadImportTemplate } from "@/api/imports";
import { SimpleDataTable } from "@/components/admin/SimpleDataTable";
import { StatusPill } from "@/components/editorial/StatusPill";
import { PageHeader, PageSection, PageShell } from "@/components/page";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Spinner } from "@/components/ui/spinner";
import { adminPageCopy } from "@/lib/pageCopy";
import type { ExamCandidateRow } from "@/types/exam";
import type { ImportFailure } from "@/types/imports";

function scoreText(row: ExamCandidateRow) {
  if (row.latest_score == null || row.latest_total_score == null) {
    return "-";
  }
  return `${row.latest_score} / ${row.latest_total_score}`;
}

function statusVariant(status?: string | null) {
  if (status === "submitted" || status === "auto_submitted") return "success";
  if (status === "in_progress") return "warning";
  return "default";
}

export function ExamCandidatesPage() {
  const { examId = "1" } = useParams();
  const [file, setFile] = useState<File | null>(null);
  const [notice, setNotice] = useState<{ tone: "success" | "error"; message: string } | null>(null);
  const queryClient = useQueryClient();
  const candidatesKey = ["exam-candidates", examId];
  const exams = useQuery({ queryKey: ["admin-exams"], queryFn: getAdminExams });
  const currentExam = exams.data?.find((exam) => String(exam.id) === examId);
  const isFrozen = currentExam?.status === "active";
  const candidates = useQuery({
    queryKey: candidatesKey,
    queryFn: () => getExamCandidates(examId),
  });
  const importMutation = useMutation({
    mutationFn: (selected: File) => importExamCandidates(examId, selected),
    onSuccess: () => {
      setNotice({ tone: "success", message: "应考人员导入完成。" });
      void queryClient.invalidateQueries({ queryKey: candidatesKey });
      void queryClient.invalidateQueries({ queryKey: ["absent-candidates"] });
    },
    onError: (error) =>
      setNotice({ tone: "error", message: getErrorMessage(error, "应考人员导入失败") }),
  });
  const retakeMutation = useMutation({
    mutationFn: (candidateId: number) => createRetakeGrant(examId, candidateId),
    onSuccess: () => {
      setNotice({ tone: "success", message: "补考授权已创建。" });
      void queryClient.invalidateQueries({ queryKey: candidatesKey });
    },
    onError: (error) =>
      setNotice({ tone: "error", message: getErrorMessage(error, "补考授权失败") }),
  });
  const removeMutation = useMutation({
    mutationFn: (candidateId: number) => removeExamCandidate(examId, candidateId),
    onSuccess: () => {
      setNotice({ tone: "success", message: "应考人员已移除。" });
      void queryClient.invalidateQueries({ queryKey: candidatesKey });
    },
    onError: (error) =>
      setNotice({ tone: "error", message: getErrorMessage(error, "移除应考人员失败") }),
  });

  const handleDownloadTemplate = async () => {
    try {
      await downloadImportTemplate("candidates");
      setNotice({ tone: "success", message: "人员模板已开始下载。" });
    } catch (error) {
      setNotice({ tone: "error", message: getErrorMessage(error, "人员模板下载失败") });
    }
  };

  const handleDownloadFailureReport = async (batchId: number) => {
    try {
      await downloadImportFailureReport(batchId);
      setNotice({ tone: "success", message: "失败明细已开始下载。" });
    } catch (error) {
      setNotice({ tone: "error", message: getErrorMessage(error, "失败明细下载失败") });
    }
  };

  const columns = useMemo<ColumnDef<ExamCandidateRow>[]>(
    () => [
      {
        id: "name",
        header: "NAME",
        meta: { mobilePriority: "primary", mobileLabel: "姓名" },
        cell: ({ row }) => (
          <>
            <span className="font-medium text-ink">{row.original.candidate_name}</span>
            <span className="ml-2 font-mono text-caption text-muted">
              {row.original.employee_no ?? "-"}
            </span>
          </>
        ),
      },
      {
        id: "dept",
        header: "DEPT",
        meta: { mobileLabel: "部门" },
        cell: ({ row }) => <span className="text-muted">{row.original.department ?? "-"}</span>,
      },
      {
        id: "attempt",
        header: "ATTEMPT",
        meta: { mobileLabel: "状态" },
        cell: ({ row }) => (
          <>
            <StatusPill variant={statusVariant(row.original.latest_attempt_status)}>
              {row.original.latest_attempt_status ?? "not_started"}
            </StatusPill>
            {row.original.attempt_no ? (
              <span className="ml-2 font-mono text-caption text-muted">
                #{row.original.attempt_no} {row.original.attempt_kind}
              </span>
            ) : null}
          </>
        ),
      },
      {
        id: "score",
        header: "SCORE",
        meta: { mobileLabel: "分数" },
        cell: ({ row }) => (
          <span className="font-mono tabular-nums">{scoreText(row.original)}</span>
        ),
      },
      {
        id: "action",
        header: "",
        meta: { mobileLabel: "操作" },
        cell: ({ row }) => (
          <div className="flex justify-end gap-2">
            {row.original.latest_attempt_status === "submitted" ||
            row.original.latest_attempt_status === "auto_submitted" ? (
              <Button
                type="button"
                size="sm"
                variant={row.original.has_unused_retake_grant ? "outline" : "default"}
                disabled={row.original.has_unused_retake_grant || retakeMutation.isPending}
                onClick={() => retakeMutation.mutate(row.original.candidate_id)}
              >
                <RotateCcw data-icon="inline-start" />
                {row.original.has_unused_retake_grant ? "已授权" : "授权补考"}
              </Button>
            ) : null}
            {!isFrozen ? (
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={removeMutation.isPending}
                onClick={() => removeMutation.mutate(row.original.candidate_id)}
              >
                <Trash2 data-icon="inline-start" />
                移除
              </Button>
            ) : null}
          </div>
        ),
      },
    ],
    [isFrozen, retakeMutation, removeMutation],
  );

  return (
    <PageShell data-testid="exam-candidates-shell" density="workbench" width="full" stagger>
      <PageHeader
        eyebrow={adminPageCopy.candidates}
        title="应考人员名单"
        description="本名单决定谁可以进入这场考试。考试发布后名单冻结，只保留补考授权操作。"
      />

      <PageSection variant="panel" className="gap-4 rounded-lg p-6 lg:p-8">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-caption uppercase tracking-[0.16em] text-muted">IMPORT</p>
            <p className="text-body text-ink">
              {isFrozen ? "考试已发布，不能再修改应考名单。" : "上传 Excel 后写入本场应考名单。"}
            </p>
          </div>
          <StatusPill variant={isFrozen ? "success" : "default"}>
            {currentExam?.status ?? "loading"}
          </StatusPill>
        </div>
        <div className="flex flex-col gap-3 md:flex-row md:items-center">
          <Field className="w-full md:max-w-md">
            <FieldLabel htmlFor="exam-candidate-file">选择 Excel 文件</FieldLabel>
            <Input
              id="exam-candidate-file"
              type="file"
              accept=".xlsx,.xls"
              disabled={isFrozen}
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
          </Field>
          <Button
            type="button"
            className="self-start"
            disabled={!file || importMutation.isPending || isFrozen}
            onClick={() => file && importMutation.mutate(file)}
          >
            {importMutation.isPending ? (
              <Spinner data-icon="inline-start" aria-label="正在导入应考人员" />
            ) : (
              <FileUp data-icon="inline-start" />
            )}
            {importMutation.isPending ? "正在导入..." : "上传应考人员"}
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => void handleDownloadTemplate()}
          >
            <Download data-icon="inline-start" />
            下载人员模板
          </Button>
        </div>
        {importMutation.data ? (
          <div className="flex flex-col gap-2 md:flex-row md:items-center">
            <p className="text-body-sm text-muted">
              成功 <span className="font-mono text-ink">{importMutation.data.success_count}</span>{" "}
              行，失败{" "}
              <span className="font-mono text-error">{importMutation.data.failed_count}</span> 行
            </p>
            {importMutation.data.failed_count > 0 ? (
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="self-start"
                onClick={() => void handleDownloadFailureReport(importMutation.data.batch_id)}
              >
                <Download data-icon="inline-start" />
                下载失败明细
              </Button>
            ) : null}
          </div>
        ) : null}
        {importMutation.data?.failures.length ? (
          <>
            <Separator />
            <ul className="flex flex-col gap-1 text-caption text-muted">
              {importMutation.data.failures.map((failure: ImportFailure) => (
                <li key={failure.row_number} className="font-mono">
                  行 {failure.row_number} · {failure.reason}
                </li>
              ))}
            </ul>
          </>
        ) : null}
        {notice ? (
          <Alert variant={notice.tone === "success" ? "success" : "error"}>
            <AlertDescription>{notice.message}</AlertDescription>
          </Alert>
        ) : null}
      </PageSection>

      <PageSection variant="table">
        <SimpleDataTable
          columns={columns}
          data={candidates.data ?? []}
          emptyText="暂无应考人员"
          rowKey={(row) => row.candidate_id}
        />
      </PageSection>
    </PageShell>
  );
}
