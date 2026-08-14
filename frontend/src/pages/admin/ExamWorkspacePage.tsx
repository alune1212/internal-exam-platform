import { useQuery } from "@tanstack/react-query";
import { ArrowRight, RefreshCw } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { ApiError, getErrorMessage } from "@/api/client";
import { getExamWorkspace } from "@/api/exams";
import { ExamContextNav } from "@/components/admin/ExamContextNav";
import { MetricCard } from "@/components/admin/MetricCard";
import { StatusPill, type StatusPillVariant } from "@/components/editorial/StatusPill";
import { PageHeader, PageSection, PageShell, PageStaleNotice, PageState } from "@/components/page";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { adminPageCopy, formatExamStatus } from "@/lib/pageCopy";
import { adminKeys } from "@/lib/queryKeys";
import type { ExamWorkspaceNextAction, ExamWorkspaceRead } from "@/types/exam";

const WORKSPACE_POLL_INTERVAL_MS = 15_000;
const ACTIVE_EXAM_STATUSES = new Set(["active", "published", "live"]);

const nextActionCopy: Record<ExamWorkspaceNextAction, { label: string; description: string }> = {
  manage_roster: { label: "管理名单", description: "先补齐本场考试的应考名单。" },
  fix_readiness: { label: "修复发布门禁", description: "发布预检仍有阻断项，暂不能发布。" },
  publish: { label: "发布考试", description: "发布预检已通过，可以冻结题池与名单。" },
  wait_invitation_delivery: {
    label: "等待邀请投递",
    description: "邀请发送任务仍在处理中，请等待投递状态稳定。",
  },
  send_invitations: {
    label: "发送邀请",
    description: "仍有未发送的邀请，发送后考生才能进入考试。",
  },
  resend_failed_invitations: {
    label: "重发失败邀请",
    description: "仍有失败邀请，可只重发失败项。",
  },
  wait_for_open: { label: "等待开放", description: "邀请投递已稳定，考试尚未到开放时间。" },
  monitor_exam: { label: "监控考试", description: "考试进行中，继续关注参考与作答状态。" },
  review_incidents: { label: "复核事故", description: "当前没有可用提交，先复核作废或中断记录。" },
  release_result_details: {
    label: "发布答案解析",
    description: "已有可用提交，可以一次性发布答案与解析。",
  },
  archive_exam: { label: "归档考试", description: "结果已发布且没有进行中的记录，可以归档。" },
  complete: { label: "已完成", description: "考试已归档，当前没有需要处理的生命周期动作。" },
};

type SummaryItem = { label: string; value: number; tone?: "default" | "success" | "warning" };

function statusVariant(status: string): StatusPillVariant {
  if (ACTIVE_EXAM_STATUSES.has(status)) return "success";
  if (status === "archived" || status === "ended" || status === "closed") return "warning";
  return "default";
}

function formatObservedAt(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function actionHref(examId: string, action: ExamWorkspaceNextAction) {
  switch (action) {
    case "manage_roster":
      return `/admin/exams/${examId}/candidates`;
    case "fix_readiness":
    case "publish":
      return `/admin/exams/${examId}/edit#publish`;
    case "wait_invitation_delivery":
    case "send_invitations":
    case "resend_failed_invitations":
      return `/admin/exams/${examId}/candidates#invitation-actions`;
    case "wait_for_open":
    case "monitor_exam":
      return `/admin/exams/${examId}/candidates`;
    case "review_incidents":
      return `/admin/exams/${examId}/candidates#incident-title`;
    case "release_result_details":
      return `/admin/exams/${examId}/edit#result-release`;
    case "archive_exam":
      return `/admin/exams/${examId}/edit#archive`;
    case "complete":
      return `/admin/exams/${examId}/edit`;
  }
}

function SummaryGroup({ title, items }: { title: string; items: SummaryItem[] }) {
  return (
    <PageSection variant="plain" className="gap-3" aria-labelledby={`${title}-summary-title`}>
      <div className="flex items-baseline justify-between gap-3">
        <h2
          id={`${title}-summary-title`}
          className="min-w-0 break-words font-display text-display-sm text-ink"
        >
          {title}
        </h2>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {items.map((item) => (
          <MetricCard key={item.label} {...item} />
        ))}
      </div>
    </PageSection>
  );
}

function WorkspaceState({
  state,
  title,
  description,
  examId,
  onRetry,
}: {
  state: "loading" | "error";
  title: string;
  description: string;
  examId?: string;
  onRetry?: () => void;
}) {
  const navigate = useNavigate();

  return (
    <PageShell data-testid="exam-workspace-shell" density="workbench" width="full" stagger>
      <PageHeader eyebrow="EXAM WORKSPACE · 考试工作台" title="考试工作台" />
      {examId ? <ExamContextNav examId={examId} /> : null}
      <PageSection variant="card">
        <PageState
          state={state}
          eyebrow={state === "error" ? adminPageCopy.error : "WORKSPACE · 加载中"}
          title={title}
          description={description}
          action={onRetry ? { label: "重试", onClick: onRetry } : undefined}
          secondaryAction={
            state === "error"
              ? { label: "返回考试列表", onClick: () => navigate("/admin/exams") }
              : undefined
          }
          surface="inherit"
          className="py-8"
        />
      </PageSection>
    </PageShell>
  );
}

function readinessText(workspace: ExamWorkspaceRead) {
  if (workspace.exam.status !== "draft") {
    return "考试已发布；题池与名单按冻结快照提供汇总。";
  }
  if (!workspace.readiness) {
    return "发布预检尚未返回，请打开考试编排查看。";
  }
  return workspace.readiness.ready
    ? `发布预检通过：${workspace.readiness.roster_count} 名应考人员，预计冻结 ${workspace.readiness.prospective_pool_count} 道题。`
    : `发布预检有 ${workspace.readiness.blockers.length} 个阻断项，暂不能发布。`;
}

export function ExamWorkspacePage() {
  const { examId } = useParams();
  const workspace = useQuery({
    queryKey: adminKeys.examWorkspace(examId ?? "missing"),
    queryFn: () => {
      if (!examId) throw new Error("missing exam id");
      return getExamWorkspace(examId);
    },
    enabled: Boolean(examId),
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    refetchInterval: (query) => {
      const status = query.state.data?.exam.status;
      return status && ACTIVE_EXAM_STATUSES.has(status) ? WORKSPACE_POLL_INTERVAL_MS : false;
    },
  });

  if (workspace.isLoading || !examId) {
    return (
      <WorkspaceState
        state="loading"
        examId={examId}
        title="正在读取考试工作台。"
        description="正在汇总发布、名单、邀请与作答状态。"
      />
    );
  }

  if ((workspace.isError && !workspace.data) || !workspace.data) {
    const missing = workspace.error instanceof ApiError && workspace.error.status === 404;
    return (
      <WorkspaceState
        state="error"
        examId={examId}
        title={missing ? "未找到考试。" : "考试工作台加载失败。"}
        description={
          missing
            ? "请返回考试列表确认考试是否仍然存在。"
            : getErrorMessage(workspace.error, "请稍后重试，或确认后台服务是否可用。")
        }
        onRetry={() => void workspace.refetch()}
      />
    );
  }

  const data = workspace.data;
  const nextAction = nextActionCopy[data.next_action];
  const nextActionTarget = actionHref(examId, data.next_action);

  return (
    <PageShell data-testid="exam-workspace-shell" density="workbench" width="full" stagger>
      <PageHeader
        eyebrow="EXAM WORKSPACE · 考试工作台"
        title={`考试工作台 · ${data.exam.title}`}
        description="按一次服务器观察汇总本场考试的生命周期状态；所有操作仍需在目标页面重新校验。"
        actions={
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              size="sm"
              variant="ghost"
              disabled={workspace.isFetching}
              onClick={() => void workspace.refetch()}
            >
              <RefreshCw data-icon="inline-start" />
              {workspace.isFetching ? "刷新中" : "刷新工作台"}
            </Button>
            <Button asChild size="sm" variant="outline">
              <Link to={`/admin/exams/${examId}/edit`}>编排考试</Link>
            </Button>
          </div>
        }
      >
        <div className="flex flex-wrap items-center gap-3">
          <StatusPill variant={statusVariant(data.exam.status)}>
            {formatExamStatus(data.exam.status)}
          </StatusPill>
          <span className="text-body-sm text-muted">
            数据观测时间：{" "}
            <time dateTime={data.observed_at} data-observed-at={data.observed_at}>
              {formatObservedAt(data.observed_at)}
            </time>
          </span>
        </div>
      </PageHeader>

      <ExamContextNav examId={examId} examTitle={data.exam.title} />

      {workspace.isError ? (
        <PageStaleNotice
          lastSuccessfulAt={data.observed_at}
          title="工作台刷新失败"
          description={`暂时保留上一次成功读取的汇总。${getErrorMessage(workspace.error, "请稍后重试")}。`}
          retrying={workspace.isFetching}
          onRetry={() => workspace.refetch()}
        />
      ) : null}

      <Alert variant={data.next_action === "complete" ? "success" : "warning"}>
        <AlertTitle>下一步建议</AlertTitle>
        <AlertDescription>
          <span className="font-medium text-ink">{nextAction.label}：</span>{" "}
          <span data-next-action-reason>{data.next_action_reason || nextAction.description}</span>
          {data.next_action_reason ? <span className="ml-1">{nextAction.description}</span> : null}
        </AlertDescription>
      </Alert>

      <PageSection variant="card" aria-labelledby="workspace-readiness-title">
        <div className="flex flex-col gap-2">
          <span className="text-caption uppercase tracking-[0.16em] text-muted">
            PUBLICATION · 发布状态
          </span>
          <h2
            id="workspace-readiness-title"
            className="min-w-0 break-words font-display text-display-sm text-ink"
          >
            发布预检与生命周期
          </h2>
          <p className="text-body-sm text-muted">{readinessText(data)}</p>
        </div>
        {data.readiness?.blockers.length ? (
          <div aria-label="发布阻断项" className="rounded-md border border-error p-4">
            <h3 className="min-w-0 break-words text-caption font-semibold uppercase tracking-[0.14em] text-error">
              BLOCKERS · 阻断项
            </h3>
            <ul className="mt-3 list-disc space-y-2 pl-5 text-body-sm text-ink">
              {data.readiness.blockers.map((issue) => (
                <li key={issue.code}>{issue.message}</li>
              ))}
            </ul>
          </div>
        ) : null}
        {data.readiness?.warnings.length ? (
          <div aria-label="发布警告" className="rounded-md border border-warning p-4">
            <h3 className="min-w-0 break-words text-caption font-semibold uppercase tracking-[0.14em] text-warning">
              WARNINGS · 警告
            </h3>
            <ul className="mt-3 list-disc space-y-2 pl-5 text-body-sm text-ink">
              {data.readiness.warnings.map((issue) => (
                <li key={issue.code}>{issue.message}</li>
              ))}
            </ul>
          </div>
        ) : null}
        <div className="flex flex-wrap gap-3">
          <Button asChild size="sm">
            <Link to={nextActionTarget}>
              {nextAction.label}
              <ArrowRight data-icon="inline-end" />
            </Link>
          </Button>
          <Button asChild size="sm" variant="outline">
            <Link to={`/admin/exams/${examId}/edit#publish`}>查看发布预检</Link>
          </Button>
        </div>
      </PageSection>

      <SummaryGroup
        title="名单摘要"
        items={[
          { label: "名单总数", value: data.roster_summary.total_count },
          { label: "已启用账户", value: data.roster_summary.active_count, tone: "success" },
          { label: "待完成注册", value: data.roster_summary.pending_count, tone: "warning" },
          { label: "已停用账户", value: data.roster_summary.inactive_count },
        ]}
      />

      <SummaryGroup
        title="邀请摘要"
        items={[
          { label: "未发送邀请", value: data.invitation_summary.not_sent_count, tone: "warning" },
          { label: "已发送邀请", value: data.invitation_summary.sent_count, tone: "success" },
          { label: "失败邀请", value: data.invitation_summary.failed_count, tone: "warning" },
          { label: "发送中", value: data.invitation_summary.in_flight_count, tone: "warning" },
        ]}
      />

      <SummaryGroup
        title="参考摘要"
        items={[
          { label: "未开始", value: data.attendance_summary.not_started_count },
          { label: "进行中", value: data.attendance_summary.in_progress_count, tone: "warning" },
          { label: "已提交", value: data.attendance_summary.submitted_count, tone: "success" },
        ]}
      />

      <SummaryGroup
        title="作答记录"
        items={[
          { label: "进行中记录", value: data.attempt_summary.in_progress_count, tone: "warning" },
          { label: "正常提交", value: data.attempt_summary.submitted_count, tone: "success" },
          { label: "自动提交", value: data.attempt_summary.auto_submitted_count, tone: "success" },
          { label: "作废记录", value: data.attempt_summary.voided_count },
        ]}
      />

      <PageSection variant="plain" aria-labelledby="workspace-incidents-title">
        <div className="flex flex-col gap-2">
          <span className="text-caption uppercase tracking-[0.16em] text-muted">
            INCIDENTS · 事故
          </span>
          <h2
            id="workspace-incidents-title"
            className="min-w-0 break-words font-display text-display-sm text-ink"
          >
            事故与补考
          </h2>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <MetricCard label="作废事故" value={data.incident_summary.voided_count} />
          <MetricCard
            label="未使用补考授权"
            value={data.incident_summary.unused_retake_count}
            tone="warning"
          />
        </div>
      </PageSection>

      <PageSection variant="card" aria-labelledby="workspace-actions-title">
        <div className="flex flex-col gap-2">
          <span className="text-caption uppercase tracking-[0.16em] text-muted">
            SURFACES · 现有页面
          </span>
          <h2
            id="workspace-actions-title"
            className="min-w-0 break-words font-display text-display-sm text-ink"
          >
            打开相关操作
          </h2>
          <p className="text-body-sm text-muted">
            工作台只提供深链接，不绕过现有发布、邀请、事故、结果或归档门禁。
          </p>
        </div>
        <div className="flex flex-wrap gap-2" role="group" aria-label="考试操作页面">
          <Button asChild size="sm" variant="outline">
            <Link to={`/admin/exams/${examId}/edit#publish`}>发布 / 编排</Link>
          </Button>
          <Button asChild size="sm" variant="outline">
            <Link to={`/admin/exams/${examId}/candidates`}>名单</Link>
          </Button>
          <Button asChild size="sm" variant="outline">
            <Link to={`/admin/exams/${examId}/candidates#invitation-actions`}>邀请投递</Link>
          </Button>
          <Button asChild size="sm" variant="outline">
            <Link to={`/admin/exams/${examId}/candidates#incident-title`}>事故记录</Link>
          </Button>
          <Button asChild size="sm" variant="outline">
            <Link to={`/admin/reports/scores?exam_id=${encodeURIComponent(examId)}`}>成绩结果</Link>
          </Button>
          <Button asChild size="sm" variant="outline">
            <Link to={`/admin/exams/${examId}/edit#archive`}>归档 / 编排</Link>
          </Button>
        </div>
      </PageSection>
    </PageShell>
  );
}
