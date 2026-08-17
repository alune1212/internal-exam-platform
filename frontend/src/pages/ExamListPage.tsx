import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, Clock, FileText, Hash } from "lucide-react";
import { Link } from "react-router-dom";

import { getActiveExams } from "@/api/exams";
import { StatusPill } from "@/components/editorial/StatusPill";
import {
  PageActions,
  PageHeader,
  PageSection,
  PageShell,
  PageStaleNotice,
  PageState,
} from "@/components/page";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { getCurrentCandidate } from "@/lib/candidateSession";
import { candidatePageCopy, candidatePageText, formatExamAvailability } from "@/lib/pageCopy";
import type { Exam } from "@/types/exam";

function resolveQuestionCount(rule: Record<string, unknown>): number | null {
  if (typeof rule.question_count === "number") {
    return rule.question_count;
  }
  if (Array.isArray(rule.counts)) {
    return rule.counts.reduce(
      (total, value) => (typeof value === "number" ? total + value : total),
      0,
    );
  }
  return null;
}

function resolveAvailability(exam: Exam, now = new Date()) {
  if (exam.availability_status === "not_started") {
    return {
      status: "not_started",
      label: formatExamAvailability("not_started"),
      canEnter: false,
      detail: exam.available_from ? new Date(exam.available_from).toLocaleString() : null,
      detailLabel: "开放时间",
      fallbackDetail: "等待开放",
    };
  }
  if (exam.availability_status === "ended") {
    return {
      status: "ended",
      label: formatExamAvailability("ended"),
      canEnter: false,
      detail: null,
      detailLabel: "结束时间",
      fallbackDetail: "新开考窗口已关闭",
    };
  }
  const from = exam.available_from ? new Date(exam.available_from) : null;
  const until = exam.available_until ? new Date(exam.available_until) : null;
  if (from && now < from) {
    return {
      status: "not_started",
      label: formatExamAvailability("not_started"),
      canEnter: false,
      detail: from.toLocaleString(),
      detailLabel: "开放时间",
      fallbackDetail: "等待开放",
    };
  }
  if (until && now > until) {
    return {
      status: "ended",
      label: formatExamAvailability("ended"),
      canEnter: false,
      detail: until.toLocaleString(),
      detailLabel: "结束时间",
      fallbackDetail: "新开考窗口已关闭",
    };
  }
  return {
    status: "open",
    label: formatExamAvailability("open"),
    canEnter: true,
    detail: from?.toLocaleString() ?? null,
    detailLabel: "开放时间",
    fallbackDetail: "随时可进入",
  };
}

function ExamCard({ exam }: { exam: Exam }) {
  const isPublished =
    exam.status === "active" || exam.status === "live" || exam.status === "published";
  const hasInProgressAttempt =
    exam.latest_attempt_status === "in_progress" && exam.latest_attempt_id;
  const totalQuestions = resolveQuestionCount(exam.question_rule);
  const availability = resolveAvailability(exam);
  const canEnter = availability.canEnter || Boolean(hasInProgressAttempt);
  // The candidate active-exam endpoint is already scope-filtered; every row
  // returned here represents an invited exam for the current user.
  const isInvited = true;
  const totalScore =
    typeof exam.question_rule.total_score === "number" ? exam.question_rule.total_score : null;

  return (
    <Card surface="data" className="flex flex-col gap-5 p-5 lg:p-7" data-exam-id={exam.id}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <StatusPill variant="info">{isInvited ? candidatePageText.exams.invited : ""}</StatusPill>
        <StatusPill
          variant={
            availability.status === "open"
              ? "success"
              : availability.status === "not_started"
                ? "pending"
                : "neutral"
          }
        >
          {availability.status === "not_started"
            ? candidatePageText.exams.upcoming
            : availability.canEnter
              ? candidatePageText.exams.available
              : candidatePageText.exams.unavailable}
        </StatusPill>
      </div>
      <h2 className="min-w-0 break-words font-display text-display-sm font-semibold text-ink lg:text-display-md">
        {exam.title}
      </h2>
      <dl className="grid grid-cols-1 gap-3 border-y border-hairline-soft py-4 text-table-label text-muted sm:grid-cols-3">
        <div className="flex min-w-0 flex-col gap-1">
          <dt className="flex items-center gap-1">
            <Clock className="size-3" aria-hidden="true" /> 时长
          </dt>
          <dd className="font-mono text-body text-ink">{exam.duration_minutes} 分钟</dd>
        </div>
        <div className="flex min-w-0 flex-col gap-1">
          <dt className="flex items-center gap-1">
            <FileText className="size-3" aria-hidden="true" /> 题数
          </dt>
          <dd className="font-mono text-body text-ink">{totalQuestions ?? "—"}</dd>
        </div>
        <div className="flex min-w-0 flex-col gap-1">
          <dt className="flex items-center gap-1">
            <Hash className="size-3" aria-hidden="true" /> 总分
          </dt>
          <dd className="font-mono text-body text-ink">{totalScore ?? "—"}</dd>
        </div>
      </dl>
      <div className="flex flex-col gap-3 border-t border-hairline-soft pt-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="min-w-0 break-words text-body-sm text-muted">
          {availability.detail
            ? `${availability.detailLabel}：${availability.detail}`
            : availability.fallbackDetail}
        </p>
        <PageActions placement="card" aria-label="考试操作" className="shrink-0">
          {canEnter ? (
            <Button asChild size="sm">
              <Link
                to={
                  hasInProgressAttempt
                    ? `/exams/${exam.id}/taking?attemptId=${exam.latest_attempt_id}`
                    : `/exams/${exam.id}/start`
                }
              >
                {hasInProgressAttempt ? "继续考试" : isPublished ? "开始考试" : "查看说明"}
                <ArrowUpRight data-icon="inline-end" aria-hidden="true" />
              </Link>
            </Button>
          ) : (
            <Button type="button" size="sm" disabled>
              {availability.status === "not_started"
                ? candidatePageText.exams.upcoming
                : candidatePageText.exams.unavailable}
            </Button>
          )}
        </PageActions>
      </div>
    </Card>
  );
}

export function ExamListPage() {
  const candidate = getCurrentCandidate();
  const candidateId = candidate?.id ?? "anonymous";
  const { data, dataUpdatedAt, isError, isLoading, refetch, isFetching } = useQuery({
    queryKey: ["candidate", candidateId, "active-exams"],
    queryFn: getActiveExams,
    enabled: Boolean(candidate),
    retry: false,
  });
  const hasLoadError = isError && !data;
  const hasStaleError = isError && Boolean(data);

  return (
    <PageShell density="calm" width="wide" stagger data-testid="candidate-exam-list-shell">
      <PageHeader
        title={candidatePageText.exams.title}
        description={candidatePageText.exams.description}
      />

      {hasStaleError ? (
        <PageStaleNotice
          lastSuccessfulAt={dataUpdatedAt}
          onRetry={() => refetch()}
          retrying={isFetching}
        />
      ) : null}

      {isLoading ? (
        <PageSection variant="plain">
          <PageState state="loading" rows={3} surface="inherit" />
        </PageSection>
      ) : hasLoadError ? (
        <PageSection variant="plain">
          <PageState
            state="error"
            surface="inherit"
            eyebrow={candidatePageCopy.error}
            title={candidatePageText.exams.errorTitle}
            description={candidatePageText.exams.errorDescription}
            onRetry={() => void refetch()}
          />
        </PageSection>
      ) : data?.length ? (
        <PageSection variant="plain" aria-label="受邀考试列表">
          <div className="grid gap-5 md:grid-cols-2">
            {data.map((exam) => (
              <ExamCard key={exam.id} exam={exam} />
            ))}
          </div>
        </PageSection>
      ) : (
        <PageSection variant="plain">
          <PageState
            state="empty"
            surface="inherit"
            eyebrow={candidatePageCopy.empty}
            title={candidatePageText.exams.emptyTitle}
            description={candidatePageText.exams.emptyDescription}
          />
        </PageSection>
      )}
    </PageShell>
  );
}
