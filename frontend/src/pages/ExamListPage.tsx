import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, Clock, FileText, Hash } from "lucide-react";
import { Link } from "react-router-dom";

import { getActiveExams } from "@/api/exams";
import { PageHeader, PageShell, PageState } from "@/components/page";
import { Button } from "@/components/ui/button";
import { getCurrentCandidate } from "@/lib/candidateSession";
import {
  candidatePageCopy,
  candidatePageText,
  formatExamAvailability,
  formatExamStatus,
} from "@/lib/pageCopy";
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
  const isLive = exam.status === "active" || exam.status === "live" || exam.status === "published";
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
    <article className="flex flex-col gap-5 rounded-lg border border-hairline bg-canvas p-6 shadow-card lg:p-7">
      <p className="font-body text-caption font-medium uppercase italic tracking-[0.18em] text-muted">
        {isInvited
          ? candidatePageText.exams.invited
          : formatExamStatus(isLive ? "active" : exam.status)}
      </p>
      <h2 className="font-display text-display-sm font-semibold text-ink lg:text-display-md">
        {exam.title}
      </h2>
      <dl className="grid grid-cols-3 gap-3 border-y border-hairline-soft py-3 text-caption text-muted">
        <div className="flex flex-col gap-1">
          <dt className="flex items-center gap-1 uppercase tracking-[0.16em]">
            <Clock className="size-3" /> 时长
          </dt>
          <dd className="font-mono text-body text-ink">{exam.duration_minutes} 分钟</dd>
        </div>
        <div className="flex flex-col gap-1">
          <dt className="flex items-center gap-1 uppercase tracking-[0.16em]">
            <FileText className="size-3" /> 题数
          </dt>
          <dd className="font-mono text-body text-ink">{totalQuestions ?? "-"}</dd>
        </div>
        <div className="flex flex-col gap-1">
          <dt className="flex items-center gap-1 uppercase tracking-[0.16em]">
            <Hash className="size-3" /> 总分
          </dt>
          <dd className="font-mono text-body text-ink">{totalScore ?? "-"}</dd>
        </div>
      </dl>
      <div className="flex items-center justify-between gap-3">
        <p className="text-caption italic text-muted">
          {availability.detail
            ? `${availability.detailLabel} · ${availability.detail}`
            : availability.fallbackDetail}
        </p>
        {canEnter ? (
          <Button asChild size="sm">
            <Link
              to={
                hasInProgressAttempt
                  ? `/exams/${exam.id}/taking?attemptId=${exam.latest_attempt_id}`
                  : `/exams/${exam.id}/start`
              }
            >
              {hasInProgressAttempt ? "继续考试" : isLive ? "开始考试" : "查看说明"}
              <ArrowUpRight data-icon="inline-end" />
            </Link>
          </Button>
        ) : (
          <Button type="button" size="sm" disabled>
            {availability.status === "not_started"
              ? candidatePageText.exams.upcoming
              : candidatePageText.exams.unavailable}
          </Button>
        )}
      </div>
      <p className="text-caption uppercase tracking-[0.16em] text-muted">
        {availability.status === "not_started"
          ? candidatePageText.exams.upcoming
          : availability.canEnter
            ? candidatePageText.exams.available
            : candidatePageText.exams.unavailable}
      </p>
    </article>
  );
}

export function ExamListPage() {
  const candidate = getCurrentCandidate();
  const candidateId = candidate?.id ?? "anonymous";
  const { data, isError, isLoading } = useQuery({
    queryKey: ["candidate", candidateId, "active-exams"],
    queryFn: getActiveExams,
    enabled: Boolean(candidate),
  });
  const hasLoadError = isError;

  return (
    <PageShell density="calm" stagger data-testid="candidate-exam-list-shell">
      <PageHeader
        eyebrow={candidatePageCopy.exams}
        title={candidatePageText.exams.title}
        description={candidatePageText.exams.description}
      />

      {isLoading ? (
        <PageState state="loading" rows={3} />
      ) : hasLoadError ? (
        <PageState
          state="error"
          eyebrow={candidatePageCopy.error}
          title={candidatePageText.exams.errorTitle}
          description={candidatePageText.exams.errorDescription}
        />
      ) : data?.length ? (
        <div className="grid gap-5 md:grid-cols-2">
          {data.map((exam) => (
            <ExamCard key={exam.id} exam={exam} />
          ))}
        </div>
      ) : (
        <PageState
          state="empty"
          eyebrow={candidatePageCopy.empty}
          title={candidatePageText.exams.emptyTitle}
          description={candidatePageText.exams.emptyDescription}
        />
      )}
    </PageShell>
  );
}
