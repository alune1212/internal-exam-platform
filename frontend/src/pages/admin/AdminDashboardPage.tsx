import { useQuery } from "@tanstack/react-query";
import * as React from "react";

import { getAdminExams } from "@/api/exams";
import { getAdminQuestions } from "@/api/questions";
import { getAbsentCandidates, getScoreReport } from "@/api/reports";
import { MetricCard } from "@/components/admin/MetricCard";
import { ActivityDot, type ActivityDotStatus } from "@/components/editorial/ActivityDot";
import { PageHeader, PageSection, PageShell, PageStaleNotice, PageState } from "@/components/page";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { adminPageCopy, formatAttemptStatus, formatExamStatus } from "@/lib/pageCopy";

interface ActivityItem {
  id: string;
  title: string;
  caption: string;
  when: string;
  tone: ActivityDotStatus;
}

const ACTIVITY_STATUS_LABEL: Record<ActivityDotStatus, string> = {
  neutral: "一般状态",
  success: "已交卷",
  warning: "需要关注",
  error: "异常",
  info: "提示",
};

function resolveActivityTime(value: string): { label: string; dateTime?: string } {
  if (value === "-") {
    return { label: value };
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return { label: value };
  }
  return {
    label: date.toLocaleString("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }),
    dateTime: value,
  };
}

function ActivityRow({ item }: { item: ActivityItem }) {
  const activityTime = resolveActivityTime(item.when);

  return (
    <li className="flex min-w-0 items-start gap-3 border-b border-hairline-soft py-3 last:border-b-0">
      <ActivityDot
        status={item.tone}
        aria-label={ACTIVITY_STATUS_LABEL[item.tone]}
        className="mt-1 shrink-0"
      />
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <span className="break-words text-body font-medium text-ink">{item.title}</span>
        <span className="break-words text-caption text-muted">{item.caption}</span>
      </div>
      {activityTime.dateTime ? (
        <time className="shrink-0 text-caption text-muted" dateTime={activityTime.dateTime}>
          {activityTime.label}
        </time>
      ) : (
        <span className="shrink-0 text-caption text-muted">{activityTime.label}</span>
      )}
    </li>
  );
}

export function AdminDashboardPage() {
  const questions = useQuery({
    queryKey: ["admin", "questions"],
    queryFn: getAdminQuestions,
    retry: false,
  });
  const exams = useQuery({
    queryKey: ["admin", "exams"],
    queryFn: getAdminExams,
    retry: false,
  });
  const scores = useQuery({
    queryKey: ["admin", "score-report"],
    queryFn: () => getScoreReport(),
    retry: false,
  });
  const absent = useQuery({
    queryKey: ["admin", "absent-candidates", "not_started"],
    queryFn: () => getAbsentCandidates("not_started"),
    retry: false,
  });

  const questionsLoading = !questions.data && questions.isLoading;
  const examsLoading = !exams.data && exams.isLoading;
  const scoresLoading = !scores.data && scores.isLoading;
  const absentLoading = !absent.data && absent.isLoading;
  const questionsError = questions.isError && !questions.data;
  const examsError = exams.isError && !exams.data;
  const scoresError = scores.isError && !scores.data;
  const absentError = absent.isError && !absent.data;
  const hasStaleData =
    (questions.isError && Boolean(questions.data)) ||
    (exams.isError && Boolean(exams.data)) ||
    (scores.isError && Boolean(scores.data)) ||
    (absent.isError && Boolean(absent.data));
  const liveExams = (exams.data ?? []).filter(
    (exam) => exam.status === "active" || exam.status === "live",
  ).length;
  const hasMetricError = questionsError || examsError || scoresError || absentError;
  const activityUnavailable = (scores.isError && !scores.data) || (absent.isError && !absent.data);

  const retryDashboard = () =>
    Promise.all([questions.refetch(), exams.refetch(), scores.refetch(), absent.refetch()]);

  const retryActivity = () => Promise.all([scores.refetch(), absent.refetch()]);

  const activity = React.useMemo<ActivityItem[]>(
    () => [
      ...(scores.data ?? []).slice(0, 5).map((score) => ({
        id: `score-${score.roster_name}-${score.exam_title}`,
        title: `${score.roster_name} 已交卷：${score.exam_title}`,
        caption: `得分 ${score.score} / ${score.total_score}`,
        when: score.submitted_at ?? "-",
        tone: "success" as const,
      })),
      ...(absent.data ?? []).slice(0, 5).map((candidate) => ({
        id: `absent-${candidate.candidate_id}-${candidate.exam_group ?? ""}`,
        title: `${candidate.roster_name} 尚未开始考试`,
        caption: candidate.exam_group ?? candidate.department ?? "-",
        when: "未到",
        tone: "warning" as const,
      })),
    ],
    [scores.data, absent.data],
  );

  const lastRefreshedLabel = React.useMemo(() => {
    // Intl format only needs to refresh alongside the queries, not on every render.
    const lastUpdate = Math.max(
      questions.dataUpdatedAt,
      exams.dataUpdatedAt,
      scores.dataUpdatedAt,
      absent.dataUpdatedAt,
    );
    return lastUpdate ? new Date(lastUpdate).toLocaleString("zh-CN") : "尚未刷新";
  }, [questions.dataUpdatedAt, exams.dataUpdatedAt, scores.dataUpdatedAt, absent.dataUpdatedAt]);

  return (
    <PageShell data-testid="admin-dashboard-shell" density="workbench" width="wide">
      <PageHeader title="仪表盘" description={`最近一次刷新 · ${lastRefreshedLabel}`}>
        <p className="text-body-sm text-muted" role="status">
          {hasMetricError ? "部分数据暂不可用，详见下方提示。" : "关键数据已就绪。"}
        </p>
      </PageHeader>

      {hasStaleData ? (
        <PageStaleNotice
          lastSuccessfulAt={Math.max(
            questions.dataUpdatedAt,
            exams.dataUpdatedAt,
            scores.dataUpdatedAt,
            absent.dataUpdatedAt,
          )}
          onRetry={retryDashboard}
          retrying={
            questions.isFetching || exams.isFetching || scores.isFetching || absent.isFetching
          }
        />
      ) : null}

      <section
        aria-label="关键指标"
        data-dashboard-metrics=""
        className="grid min-w-0 grid-cols-1 gap-4 sm:grid-cols-2 2xl:grid-cols-4"
      >
        <MetricCard
          label={adminPageCopy.library}
          value={questionsLoading ? "…" : questionsError ? "—" : (questions.data?.length ?? 0)}
          unit="题"
          caption="所有状态的题目合计"
        />
        <MetricCard
          label={formatExamStatus("active")}
          value={examsLoading ? "…" : examsError ? "—" : liveExams}
          unit="场"
          tone="success"
          caption="已发布考试"
        />
        <MetricCard
          label={formatAttemptStatus("submitted")}
          value={scoresLoading ? "…" : scoresError ? "—" : (scores.data?.length ?? 0)}
          unit="次"
          caption="所有考试累计交卷次数"
        />
        <MetricCard
          label={formatAttemptStatus("not_started")}
          value={absentLoading ? "…" : absentError ? "—" : (absent.data?.length ?? 0)}
          unit="人"
          tone="warning"
          caption="应考但尚未开始"
        />
      </section>
      {hasMetricError ? (
        <Alert
          data-dashboard-alert="metrics"
          variant="error"
          className="items-start gap-3 sm:flex-row sm:items-center"
        >
          <AlertDescription>
            部分仪表盘指标加载失败，当前数值已标记为不可用，请稍后重试。
          </AlertDescription>
          <Button type="button" size="sm" variant="outline" onClick={() => void retryDashboard()}>
            重试指标
          </Button>
        </Alert>
      ) : null}

      <PageSection variant="panel" data-dashboard-activity="" className="gap-4">
        <header className="flex flex-col gap-1">
          <h2 className="min-w-0 break-words font-display text-display-sm font-semibold text-ink">
            最近活动
          </h2>
          <p className="text-body-sm text-muted">交卷与未开始</p>
        </header>
        {scoresLoading || absentLoading ? (
          <PageState
            state="loading"
            surface="inherit"
            rows={3}
            showLoadingCaption={false}
            className="p-0"
          />
        ) : activityUnavailable ? (
          <PageState
            state="error"
            surface="inherit"
            title="最近活动加载失败。"
            description="请稍后重试，或检查成绩与参考状态接口。"
            onRetry={() => void retryActivity()}
            className="py-8"
          />
        ) : activity.length ? (
          <ul className="flex flex-col">
            {activity.map((item) => (
              <ActivityRow key={item.id} item={item} />
            ))}
          </ul>
        ) : (
          <PageState
            state="empty"
            surface="inherit"
            title="暂无活动记录。"
            description="当有人交卷或参考状态变化后，最近活动会显示在这里。"
            className="py-8"
          />
        )}
      </PageSection>
    </PageShell>
  );
}
