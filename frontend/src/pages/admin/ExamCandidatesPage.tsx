import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { Download, RotateCcw, Trash2 } from "lucide-react";
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
import { ImportPanel } from "@/components/admin/ImportPanel";
import { SimpleDataTable } from "@/components/admin/SimpleDataTable";
import { StatusPill } from "@/components/editorial/StatusPill";
import { PageHeader, PageSection, PageShell, PageState } from "@/components/page";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  adminPageCopy,
  adminTableCopy,
  formatAttemptKind,
  formatAttemptStatus,
  formatExamStatus,
  importCopy,
} from "@/lib/pageCopy";
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
  const candidatesKey = ["admin", "exam-candidates", examId];
  const exams = useQuery({ queryKey: ["admin", "exams"], queryFn: getAdminExams });
  const currentExam = exams.data?.find((exam) => String(exam.id) === examId);
  const isFrozen = currentExam?.status === "active";
  const canEditCandidates = Boolean(currentExam) && !isFrozen;
  const candidates = useQuery({
    queryKey: candidatesKey,
    queryFn: () => getExamCandidates(examId),
    enabled: Boolean(currentExam),
  });
  const hasExamLoadError = exams.isError && !exams.data;
  const hasCandidateLoadError = candidates.isError && !candidates.data;
  const importMutation = useMutation({
    mutationFn: (selected: File) => importExamCandidates(examId, selected),
    onSuccess: () => {
      setNotice({ tone: "success", message: importCopy.rosterImportComplete });
      void queryClient.invalidateQueries({ queryKey: candidatesKey });
      void queryClient.invalidateQueries({ queryKey: ["admin", "absent-candidates"] });
    },
    onError: (error) =>
      setNotice({ tone: "error", message: getErrorMessage(error, importCopy.rosterImportFailed) }),
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
      setNotice({ tone: "success", message: "应考人员已从名单移除。" });
      void queryClient.invalidateQueries({ queryKey: candidatesKey });
    },
    onError: (error) =>
      setNotice({ tone: "error", message: getErrorMessage(error, "移除应考名单人员失败") }),
  });

  const handleDownloadTemplate = async () => {
    try {
      await downloadImportTemplate("candidates");
      setNotice({ tone: "success", message: "应考名单导入模板已开始下载。" });
    } catch (error) {
      setNotice({ tone: "error", message: getErrorMessage(error, "应考名单导入模板下载失败") });
    }
  };

  const handleDownloadFailureReport = async (batchId: number) => {
    try {
      await downloadImportFailureReport(batchId);
      setNotice({ tone: "success", message: importCopy.failureReportStarted });
    } catch (error) {
      setNotice({ tone: "error", message: getErrorMessage(error, importCopy.failureReportFailed) });
    }
  };

  const columns = useMemo<ColumnDef<ExamCandidateRow>[]>(
    () => [
      {
        id: "name",
        header: adminTableCopy.name,
        meta: { mobilePriority: "primary", mobileLabel: adminTableCopy.name },
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
        header: adminTableCopy.department,
        meta: { mobileLabel: adminTableCopy.department },
        cell: ({ row }) => <span className="text-muted">{row.original.department ?? "-"}</span>,
      },
      {
        id: "attempt",
        header: adminTableCopy.attempt,
        meta: { mobileLabel: adminTableCopy.attempt },
        cell: ({ row }) => (
          <>
            <StatusPill variant={statusVariant(row.original.latest_attempt_status)}>
              {formatAttemptStatus(row.original.latest_attempt_status)}
            </StatusPill>
            {row.original.attempt_no ? (
              <span className="ml-2 font-mono text-caption text-muted">
                #{row.original.attempt_no} · {formatAttemptKind(row.original.attempt_kind)}
              </span>
            ) : null}
          </>
        ),
      },
      {
        id: "score",
        header: adminTableCopy.score,
        meta: { mobileLabel: adminTableCopy.score },
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
            {canEditCandidates ? (
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
    [canEditCandidates, retakeMutation, removeMutation],
  );

  const examStatusLabel = exams.isLoading
    ? "LOADING · 正在确认"
    : hasExamLoadError
      ? "ERROR · 加载失败"
      : currentExam
        ? formatExamStatus(currentExam.status)
        : "MISSING · 未找到考试";

  return (
    <PageShell data-testid="exam-candidates-shell" density="workbench" width="full" stagger>
      <PageHeader
        eyebrow={adminPageCopy.roster}
        title="应考名单"
        description="本名单决定谁可以进入这场考试。考试发布后名单冻结，只保留补考授权操作。"
      />

      <ImportPanel
        fileInputId="exam-candidate-file"
        fileLabel={importCopy.selectExcelFile}
        selectedFile={file}
        fileDisabled={!canEditCandidates}
        uploadDisabled={!canEditCandidates}
        onFileChange={setFile}
        uploadLabel={importCopy.uploadRoster}
        pendingLabel={importCopy.importing}
        pendingAriaLabel="正在导入应考名单"
        isPending={importMutation.isPending}
        onUpload={() => file && importMutation.mutate(file)}
        intro={
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-caption uppercase tracking-[0.16em] text-muted">IMPORT</p>
              <p className="text-body text-ink">
                {exams.isLoading
                  ? "正在确认考试状态，暂不能修改应考名单。"
                  : hasExamLoadError
                    ? "考试状态加载失败，暂不能修改应考名单。"
                    : !currentExam
                      ? "未找到这场考试，暂不能修改应考名单。"
                      : isFrozen
                        ? "考试已发布，不能再修改应考名单。"
                        : "上传 Excel 后写入本场应考名单。"}
              </p>
            </div>
            <StatusPill variant={isFrozen ? "success" : "default"}>{examStatusLabel}</StatusPill>
          </div>
        }
        templateAction={
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => void handleDownloadTemplate()}
          >
            <Download data-icon="inline-start" />
            {importCopy.rosterTemplate}
          </Button>
        }
      >
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
      </ImportPanel>

      <PageSection variant="table">
        {exams.isLoading ? (
          <PageState
            state="loading"
            rows={3}
            className="border-0 bg-transparent py-10 shadow-none"
          />
        ) : hasExamLoadError ? (
          <PageState
            state="error"
            eyebrow={adminPageCopy.error}
            title="考试状态加载失败。"
            description="应考名单依赖考试状态，暂不能展示或维护。"
            className="border-0 bg-transparent py-10 shadow-none"
          />
        ) : !currentExam ? (
          <PageState
            state="error"
            eyebrow={adminPageCopy.error}
            title="未找到考试。"
            description="请返回考试列表确认考试是否仍然存在。"
            className="border-0 bg-transparent py-10 shadow-none"
          />
        ) : candidates.isLoading ? (
          <PageState
            state="loading"
            rows={3}
            className="border-0 bg-transparent py-10 shadow-none"
          />
        ) : hasCandidateLoadError ? (
          <PageState
            state="error"
            eyebrow={adminPageCopy.error}
            title="应考名单加载失败。"
            description="请稍后重试，或检查应考名单接口。"
            className="border-0 bg-transparent py-10 shadow-none"
          />
        ) : (
          <SimpleDataTable
            columns={columns}
            data={candidates.data ?? []}
            emptyText="暂无应考名单人员"
            rowKey={(row) => row.candidate_id}
          />
        )}
      </PageSection>
    </PageShell>
  );
}
