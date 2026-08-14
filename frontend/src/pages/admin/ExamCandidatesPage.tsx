import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { Download, Edit3, Plus, RefreshCw, RotateCcw, Save, Trash2, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { getErrorMessage } from "@/api/client";
import {
  createRetakeGrant,
  getAdminExams,
  getExamCandidates,
  getExamIncidents,
  importExamCandidates,
} from "@/api/exams";
import { downloadImportFailureReport, downloadImportTemplate } from "@/api/imports";
import {
  addExamRosterRow,
  getExamInvitationStatus,
  removeExamRosterRow,
  resendFailedExamInvitations,
  sendExamInvitations,
  updateExamRosterRow,
} from "@/api/invitations";
import { ExamContextNav } from "@/components/admin/ExamContextNav";
import { ImportPanel } from "@/components/admin/ImportPanel";
import { SimpleDataTable } from "@/components/admin/SimpleDataTable";
import { StatusPill, type StatusPillVariant } from "@/components/editorial/StatusPill";
import { PageHeader, PageSection, PageShell, PageState } from "@/components/page";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import {
  adminPageCopy,
  adminPageText,
  adminTableCopy,
  formatAttemptKind,
  formatAttemptStatus,
  formatExamStatus,
  formatInvitationErrorClass,
  importCopy,
} from "@/lib/pageCopy";
import { adminKeys } from "@/lib/queryKeys";
import type { ExamCandidateRow, ExamRosterPayload } from "@/types/exam";
import type { ImportFailure } from "@/types/imports";

type Notice = { tone: "success" | "error" | "warning"; message: string };
type RosterFormState = ExamRosterPayload & { candidateId?: number };

const emptyRosterForm: RosterFormState = {
  email: "",
  candidate_name: "",
  department: "",
  position: "",
  exam_group: "",
  remark: "",
};

const accountStatusLabels: Record<string, string> = {
  pending: "待完成注册",
  active: "已启用",
  inactive: "已停用",
};

const invitationStatusLabels: Record<string, string> = {
  not_sent: "未发送",
  sent: "已发送",
  failed: "发送失败",
};

const INVITATION_POLL_INTERVAL_MS = 1_200;
const INVITATION_POLL_MAX_MS = 120_000;

function hasActiveInvitationClaim(rows: ExamCandidateRow[] | undefined): boolean {
  return Boolean(rows?.some((row) => row.invitation_claimed_at));
}

function scoreText(row: ExamCandidateRow) {
  if (row.latest_score == null || row.latest_total_score == null) return "-";
  return `${row.latest_score} / ${row.latest_total_score}`;
}

function statusVariant(status?: string | null): StatusPillVariant {
  if (status === "submitted" || status === "auto_submitted" || status === "sent") return "success";
  if (status === "in_progress" || status === "pending" || status === "not_sent") return "warning";
  if (status === "voided" || status === "failed" || status === "inactive") return "error";
  return "default";
}

function RosterForm({
  value,
  isPending,
  onChange,
  onCancel,
  onSubmit,
}: {
  value: RosterFormState;
  isPending: boolean;
  onChange: (value: RosterFormState) => void;
  onCancel: () => void;
  onSubmit: () => void;
}) {
  const update = (key: keyof RosterFormState, next: string) => onChange({ ...value, [key]: next });
  return (
    <PageSection variant="card" aria-labelledby="roster-form-title" className="gap-5 p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-caption uppercase tracking-[0.16em] text-muted">
            ROSTER EDIT · 名单编辑
          </p>
          <h2
            id="roster-form-title"
            className="min-w-0 break-words font-display text-display-sm text-ink"
          >
            {value.candidateId ? "编辑应考人员" : "新增应考人员"}
          </h2>
          <p className="mt-1 text-body-sm text-muted">
            邮箱和名单姓名是必填项；账号显示名与发布后的名单快照保持独立。
          </p>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onCancel}
          aria-label="关闭名单编辑"
        >
          <X data-icon="inline-start" />
          关闭
        </Button>
      </div>
      <FieldGroup className="grid gap-4 md:grid-cols-2">
        <Field>
          <FieldLabel htmlFor="roster-email">邮箱</FieldLabel>
          <Input
            id="roster-email"
            type="email"
            value={value.email}
            onChange={(event) => update("email", event.target.value)}
            required
          />
        </Field>
        <Field>
          <FieldLabel htmlFor="roster-name">名单姓名</FieldLabel>
          <Input
            id="roster-name"
            value={value.candidate_name}
            onChange={(event) => update("candidate_name", event.target.value)}
            required
          />
        </Field>
        <Field>
          <FieldLabel htmlFor="roster-department">部门（可选）</FieldLabel>
          <Input
            id="roster-department"
            value={value.department ?? ""}
            onChange={(event) => update("department", event.target.value)}
          />
        </Field>
        <Field>
          <FieldLabel htmlFor="roster-position">职位（可选）</FieldLabel>
          <Input
            id="roster-position"
            value={value.position ?? ""}
            onChange={(event) => update("position", event.target.value)}
          />
        </Field>
        <Field>
          <FieldLabel htmlFor="roster-group">考试组（可选）</FieldLabel>
          <Input
            id="roster-group"
            value={value.exam_group ?? ""}
            onChange={(event) => update("exam_group", event.target.value)}
          />
        </Field>
        <Field>
          <FieldLabel htmlFor="roster-remark">备注（可选）</FieldLabel>
          <Input
            id="roster-remark"
            value={value.remark ?? ""}
            onChange={(event) => update("remark", event.target.value)}
          />
        </Field>
      </FieldGroup>
      <div className="flex flex-wrap gap-3">
        <Button
          type="button"
          disabled={isPending || !value.email.trim() || !value.candidate_name.trim()}
          onClick={onSubmit}
        >
          <Save data-icon="inline-start" />
          {isPending ? "保存中" : "保存名单"}
        </Button>
        <Button type="button" variant="outline" disabled={isPending} onClick={onCancel}>
          取消
        </Button>
      </div>
    </PageSection>
  );
}

export function ExamCandidatesPage() {
  const { examId = "1" } = useParams();
  const [file, setFile] = useState<File | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [editing, setEditing] = useState<RosterFormState | null>(null);
  const [pollingInvitations, setPollingInvitations] = useState(false);
  const [invitationPollStartedAt, setInvitationPollStartedAt] = useState(0);
  const queryClient = useQueryClient();
  const candidatesKey = ["admin", "exam-candidates", examId];
  const exams = useQuery({ queryKey: ["admin", "exams"], queryFn: getAdminExams });
  const currentExam = exams.data?.find((exam) => String(exam.id) === examId);
  const isFrozen = ["active", "published", "live", "archived", "ended", "closed"].includes(
    currentExam?.status ?? "",
  );
  const canSendInvitations =
    isFrozen && !["archived", "ended", "closed"].includes(currentExam?.status ?? "");
  const canEditCandidates = Boolean(currentExam) && !isFrozen;
  const candidates = useQuery({
    queryKey: candidatesKey,
    queryFn: () => getExamCandidates(examId),
    enabled: Boolean(currentExam),
  });
  const invitationStatus = useQuery({
    queryKey: ["admin", "exam-invitations", examId],
    queryFn: () => getExamInvitationStatus(examId),
    enabled: pollingInvitations,
    refetchInterval: pollingInvitations ? INVITATION_POLL_INTERVAL_MS : false,
  });
  const incidents = useQuery({
    queryKey: ["admin", "exam-incidents", examId],
    queryFn: () => getExamIncidents(examId),
    enabled: Boolean(currentExam),
  });
  const hasExamLoadError = exams.isError && !exams.data;
  const hasCandidateLoadError = candidates.isError && !candidates.data;

  const invalidateWorkspace = () => {
    void queryClient.invalidateQueries({ queryKey: adminKeys.examWorkspace(examId) });
  };

  useEffect(() => {
    if (!pollingInvitations) return;
    const timer = window.setTimeout(() => {
      setPollingInvitations(false);
      void queryClient
        .fetchQuery({
          queryKey: ["admin", "exam-invitations", examId],
          queryFn: () => getExamInvitationStatus(examId),
        })
        .then((status) => {
          if (hasActiveInvitationClaim(status.rows)) {
            setNotice({
              tone: "warning",
              message: "邀请仍在后台处理中，自动刷新已暂停。请稍后点击“刷新邀请状态”查看最终结果。",
            });
          }
        })
        .catch(() => {
          setNotice({
            tone: "warning",
            message: "自动刷新已暂停，最终邀请状态暂时获取失败。请稍后点击“刷新邀请状态”。",
          });
        });
      void queryClient.invalidateQueries({ queryKey: ["admin", "exam-candidates", examId] });
    }, INVITATION_POLL_MAX_MS);
    return () => window.clearTimeout(timer);
  }, [examId, pollingInvitations, queryClient]);

  useEffect(() => {
    if (
      !pollingInvitations ||
      invitationStatus.isFetching ||
      invitationStatus.dataUpdatedAt < invitationPollStartedAt ||
      hasActiveInvitationClaim(invitationStatus.data?.rows)
    ) {
      return;
    }
    setPollingInvitations(false);
    void queryClient.invalidateQueries({ queryKey: ["admin", "exam-candidates", examId] });
  }, [
    examId,
    invitationPollStartedAt,
    invitationStatus.data?.rows,
    invitationStatus.dataUpdatedAt,
    invitationStatus.isFetching,
    pollingInvitations,
    queryClient,
  ]);

  const onRosterSuccess = (message: string) => {
    setNotice({ tone: "success", message });
    setEditing(null);
    void queryClient.invalidateQueries({ queryKey: candidatesKey });
    void queryClient.invalidateQueries({ queryKey: ["admin", "absent-candidates"] });
    invalidateWorkspace();
  };

  const importMutation = useMutation({
    mutationFn: (selected: File) => importExamCandidates(examId, selected),
    onSuccess: () => onRosterSuccess(importCopy.rosterImportComplete),
    onError: (error) =>
      setNotice({ tone: "error", message: getErrorMessage(error, importCopy.rosterImportFailed) }),
  });
  const retakeMutation = useMutation({
    mutationFn: (candidateId: number) => createRetakeGrant(examId, candidateId),
    onSuccess: () => {
      setNotice({ tone: "success", message: "补考授权已创建。" });
      void queryClient.invalidateQueries({ queryKey: candidatesKey });
      invalidateWorkspace();
    },
    onError: (error) =>
      setNotice({ tone: "error", message: getErrorMessage(error, "补考授权失败") }),
  });
  const removeMutation = useMutation({
    mutationFn: (candidateId: number) => removeExamRosterRow(examId, candidateId),
    onSuccess: () => onRosterSuccess("应考人员已从草稿名单移除。"),
    onError: (error) =>
      setNotice({ tone: "error", message: getErrorMessage(error, "移除应考人员失败") }),
  });
  const saveMutation = useMutation({
    mutationFn: (value: RosterFormState) => {
      const payload: ExamRosterPayload = {
        email: value.email.trim(),
        candidate_name: value.candidate_name.trim(),
        department: value.department?.trim() || null,
        position: value.position?.trim() || null,
        exam_group: value.exam_group?.trim() || null,
        remark: value.remark?.trim() || null,
      };
      return value.candidateId
        ? updateExamRosterRow(examId, value.candidateId, payload)
        : addExamRosterRow(examId, payload);
    },
    onSuccess: (_data, value) =>
      onRosterSuccess(value.candidateId ? "应考人员名单已更新。" : "应考人员已加入草稿名单。"),
    onError: (error) =>
      setNotice({ tone: "error", message: getErrorMessage(error, "名单保存失败") }),
  });
  const invitationMutation = useMutation({
    mutationFn: (action: "send" | "resend") =>
      action === "send" ? sendExamInvitations(examId) : resendFailedExamInvitations(examId),
    onSuccess: (result, action) => {
      setNotice({
        tone: "success",
        message: `${action === "send" ? "初次邀请" : "失败重发"}已接受 ${result.accepted_count} 条，${result.rejected_count} 条未排入发送。正在刷新收件状态。`,
      });
      setInvitationPollStartedAt(Date.now());
      setPollingInvitations(true);
      void queryClient.invalidateQueries({ queryKey: candidatesKey });
      void queryClient.invalidateQueries({ queryKey: ["admin", "exam-invitations", examId] });
      invalidateWorkspace();
    },
    onError: (error) =>
      setNotice({ tone: "error", message: getErrorMessage(error, "邀请发送操作失败") }),
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
        id: "roster",
        header: "ROSTER · 名单身份",
        meta: { mobilePriority: "primary", mobileLabel: "名单身份" },
        cell: ({ row }) => (
          <div className="min-w-48">
            <span className="block font-medium text-ink">{row.original.roster_name}</span>
            <span className="block font-mono text-caption text-muted">
              {row.original.roster_email}
            </span>
          </div>
        ),
      },
      {
        id: "organization",
        header: "ORG · 组织信息",
        meta: { mobileLabel: "组织信息" },
        cell: ({ row }) => (
          <span className="text-muted">
            {[row.original.department, row.original.position, row.original.exam_group]
              .concat(row.original.roster_remark ?? "")
              .filter(Boolean)
              .join(" · ") || "-"}
          </span>
        ),
      },
      {
        id: "account",
        header: "ACCOUNT · 账户",
        meta: { mobileLabel: "账户" },
        cell: ({ row }) => (
          <StatusPill variant={statusVariant(row.original.account_status)}>
            {accountStatusLabels[row.original.account_status] ?? "未知状态"}
          </StatusPill>
        ),
      },
      {
        id: "invitation",
        header: "INVITATION · 邀请",
        meta: { mobileLabel: "邀请" },
        cell: ({ row }) => (
          <div className="flex flex-col gap-1">
            <StatusPill
              variant={
                row.original.invitation_claimed_at
                  ? "warning"
                  : statusVariant(row.original.invitation_status)
              }
            >
              {row.original.invitation_claimed_at
                ? "发送中"
                : (invitationStatusLabels[row.original.invitation_status] ?? "未知状态")}
            </StatusPill>
            {row.original.invitation_status === "failed" && row.original.invitation_error_class ? (
              <span className="text-caption text-error">
                {formatInvitationErrorClass(row.original.invitation_error_class)}
              </span>
            ) : null}
          </div>
        ),
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
        header: "ACTION · 操作",
        meta: { mobileLabel: "操作" },
        cell: ({ row }) => (
          <div className="flex flex-wrap justify-end gap-2">
            {row.original.latest_attempt_status === "submitted" ||
            row.original.latest_attempt_status === "auto_submitted" ||
            row.original.latest_attempt_status === "voided" ? (
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
              <>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() =>
                    setEditing({
                      candidateId: row.original.candidate_id,
                      email: row.original.roster_email,
                      candidate_name: row.original.roster_name,
                      department: row.original.department ?? "",
                      position: row.original.position ?? "",
                      exam_group: row.original.exam_group ?? "",
                      remark: row.original.roster_remark ?? "",
                    })
                  }
                >
                  <Edit3 data-icon="inline-start" />
                  编辑
                </Button>
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
              </>
            ) : null}
          </div>
        ),
      },
    ],
    [canEditCandidates, removeMutation, retakeMutation],
  );

  const examStatusLabel = exams.isLoading
    ? "LOADING · 正在确认"
    : hasExamLoadError
      ? "ERROR · 加载失败"
      : currentExam
        ? formatExamStatus(currentExam.status)
        : "MISSING · 未找到考试";

  const rosterRows = invitationStatus.data?.rows ?? candidates.data ?? [];
  const hasNotSent = rosterRows.some(
    (row) => row.invitation_status === "not_sent" && !row.invitation_claimed_at,
  );
  const hasFailed = rosterRows.some(
    (row) => row.invitation_status === "failed" && !row.invitation_claimed_at,
  );

  return (
    <PageShell data-testid="exam-candidates-shell" density="workbench" width="full" stagger>
      <PageHeader
        eyebrow={adminPageCopy.roster}
        title={adminPageText.roster.title}
        description="管理冻结的应考人员名单、账户状态与邀请投递结果。发布后名单身份和组织字段不可编辑。"
        actions={
          canSendInvitations ? (
            <div id="invitation-actions" className="flex flex-wrap gap-2">
              <Button
                type="button"
                size="sm"
                variant="ghost"
                disabled={invitationStatus.isFetching}
                onClick={() => {
                  void invitationStatus.refetch();
                  void candidates.refetch();
                }}
              >
                <RefreshCw data-icon="inline-start" />
                {invitationStatus.isFetching ? "刷新中" : "刷新邀请状态"}
              </Button>
              <Button
                type="button"
                size="sm"
                disabled={!hasNotSent || invitationMutation.isPending}
                onClick={() => invitationMutation.mutate("send")}
              >
                初次发送邀请
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={!hasFailed || invitationMutation.isPending}
                onClick={() => invitationMutation.mutate("resend")}
              >
                仅重发失败项
              </Button>
            </div>
          ) : null
        }
      />

      <ExamContextNav examId={examId} examTitle={currentExam?.title} />

      {notice ? (
        <Alert
          variant={
            notice.tone === "success" ? "success" : notice.tone === "warning" ? "warning" : "error"
          }
        >
          <AlertDescription>{notice.message}</AlertDescription>
        </Alert>
      ) : null}

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
              <p className="text-caption uppercase tracking-[0.16em] text-muted">
                IMPORT · 名单导入
              </p>
              <p className="text-body text-ink">
                {exams.isLoading
                  ? "正在确认考试状态，暂不能修改应考名单。"
                  : hasExamLoadError
                    ? "考试状态加载失败，暂不能修改应考名单。"
                    : !currentExam
                      ? "未找到这场考试，暂不能修改应考名单。"
                      : isFrozen
                        ? "考试已发布，名单已冻结；只能查看邀请投递状态。"
                        : "上传精简 Excel：email、candidate_name 及可选组织字段。"}
              </p>
            </div>
            <StatusPill variant={isFrozen ? "success" : "default"}>{examStatusLabel}</StatusPill>
          </div>
        }
        templateAction={
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => void handleDownloadTemplate()}
            >
              <Download data-icon="inline-start" />
              {importCopy.rosterTemplate}
            </Button>
            {canEditCandidates ? (
              <Button type="button" size="sm" onClick={() => setEditing({ ...emptyRosterForm })}>
                <Plus data-icon="inline-start" />
                新增应考人员
              </Button>
            ) : null}
          </div>
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
      </ImportPanel>

      {editing && canEditCandidates ? (
        <RosterForm
          value={editing}
          isPending={saveMutation.isPending}
          onChange={setEditing}
          onCancel={() => setEditing(null)}
          onSubmit={() => saveMutation.mutate(editing)}
        />
      ) : null}

      <PageSection variant="table">
        {exams.isLoading ? (
          <PageState state="loading" rows={3} surface="inherit" className="py-10" />
        ) : hasExamLoadError ? (
          <PageState
            state="error"
            eyebrow={adminPageCopy.error}
            title="考试状态加载失败。"
            description="应考名单依赖考试状态，暂不能展示或维护。"
            surface="inherit"
            className="py-10"
          />
        ) : !currentExam ? (
          <PageState
            state="error"
            eyebrow={adminPageCopy.error}
            title="未找到考试。"
            description="请返回考试列表确认考试是否仍然存在。"
            surface="inherit"
            className="py-10"
          />
        ) : candidates.isLoading ? (
          <PageState state="loading" rows={3} surface="inherit" className="py-10" />
        ) : hasCandidateLoadError ? (
          <PageState
            state="error"
            eyebrow={adminPageCopy.error}
            title={adminPageText.roster.errorTitle}
            description="请稍后重试，或检查应考名单接口。"
            surface="inherit"
            className="py-10"
          />
        ) : (
          <SimpleDataTable
            columns={columns}
            data={rosterRows}
            emptyText="暂无应考名单人员；正式考试仅对已冻结名单开放。"
            rowKey={(row) => row.candidate_id}
          />
        )}
      </PageSection>

      <PageSection variant="card" aria-labelledby="incident-title" className="grid gap-4 lg:p-8">
        <div className="flex flex-col gap-1">
          <span className="text-caption uppercase tracking-[0.16em] text-muted">
            INCIDENTS · 事故记录
          </span>
          <h2
            id="incident-title"
            className="min-w-0 break-words font-display text-display-sm text-ink"
          >
            作废与补考结果
          </h2>
          <p className="text-body-sm text-muted">
            作废记录保留原始快照和时间证据，但不计入正常成绩、正确率、排名和参考完成统计。
          </p>
        </div>
        {incidents.isLoading ? (
          <PageState state="loading" rows={2} surface="inherit" className="py-4" />
        ) : incidents.isError ? (
          <Alert variant="error">
            <AlertDescription>事故记录加载失败，请稍后刷新。</AlertDescription>
          </Alert>
        ) : incidents.data?.length ? (
          <ul className="grid gap-3">
            {incidents.data.map((incident) => (
              <li
                key={incident.attempt_id}
                className="grid gap-2 rounded-md border border-hairline bg-canvas p-4 md:grid-cols-[1fr_auto]"
              >
                <div>
                  <p className="font-medium text-ink">
                    考试记录 #{incident.attempt_id} · 应考人员 #{incident.candidate_id}
                  </p>
                  <p className="mt-1 text-body-sm text-muted">{incident.reason}</p>
                  <p className="mt-1 font-mono text-caption text-muted">
                    {new Date(incident.voided_at).toLocaleString()} · {incident.voided_by}
                  </p>
                </div>
                <StatusPill variant={incident.retake_granted ? "success" : "error"}>
                  {incident.retake_granted ? "已授权补考" : "待处理"}
                </StatusPill>
              </li>
            ))}
          </ul>
        ) : (
          <p className="rounded-md border border-hairline bg-canvas p-4 text-body-sm text-muted">
            当前没有作废事故记录。
          </p>
        )}
      </PageSection>
    </PageShell>
  );
}
