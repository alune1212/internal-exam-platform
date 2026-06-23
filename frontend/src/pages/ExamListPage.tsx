import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, Clock, FileText, Hash } from "lucide-react";
import { Link } from "react-router-dom";

import { getActiveExams } from "@/api/exams";
import { PageHeader, PageShell, PageState } from "@/components/page";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { candidatePageCopy } from "@/lib/pageCopy";
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
      label: "未开始",
      canEnter: false,
      detail: exam.available_from ? new Date(exam.available_from).toLocaleString() : null,
    };
  }
  if (exam.availability_status === "ended") {
    return {
      status: "ended",
      label: "已结束",
      canEnter: false,
      detail: exam.available_until ? new Date(exam.available_until).toLocaleString() : null,
    };
  }
  const from = exam.available_from ? new Date(exam.available_from) : null;
  const until = exam.available_until ? new Date(exam.available_until) : null;
  if (from && now < from) {
    return {
      status: "not_started",
      label: "未开始",
      canEnter: false,
      detail: from.toLocaleString(),
    };
  }
  if (until && now > until) {
    return { status: "ended", label: "已结束", canEnter: false, detail: until.toLocaleString() };
  }
  return {
    status: "open",
    label: "可进入",
    canEnter: true,
    detail: from?.toLocaleString() ?? null,
  };
}

function ExamCard({ exam }: { exam: Exam }) {
  const isLive = exam.status === "active" || exam.status === "live";
  const hasInProgressAttempt =
    exam.latest_attempt_status === "in_progress" && exam.latest_attempt_id;
  const totalQuestions = resolveQuestionCount(exam.question_rule);
  const availability = resolveAvailability(exam);
  const canEnter = availability.canEnter || Boolean(hasInProgressAttempt);
  const totalScore =
    typeof exam.question_rule.total_score === "number" ? exam.question_rule.total_score : null;

  return (
    <article className="flex flex-col gap-5 rounded-lg border border-hairline bg-canvas p-6 shadow-card lg:p-7">
      <p className="font-body text-caption font-medium uppercase italic tracking-[0.18em] text-muted">
        {isLive ? "LIVE · 进行中" : "DRAFT · 未开始"}
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
          {availability.detail ? `开放时间 · ${availability.detail}` : "随时开考"}
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
              {hasInProgressAttempt ? "继续考试" : isLive ? "进入考试" : "查看说明"}
              <ArrowUpRight data-icon="inline-end" />
            </Link>
          </Button>
        ) : (
          <Button type="button" size="sm" disabled>
            不可进入
          </Button>
        )}
      </div>
      <p className="text-caption uppercase tracking-[0.16em] text-muted">{availability.label}</p>
    </article>
  );
}

function resolveHeading(examCount: number, isLoading: boolean): string {
  if (isLoading) {
    return "正在加载今日考试……";
  }
  if (examCount === 0) {
    return "今天暂无考试安排。";
  }
  if (examCount === 1) {
    return "今天有一场考试等着你。";
  }
  return `今天有 ${examCount} 场考试等着你。`;
}

export function ExamListPage() {
  const { data = [], isLoading } = useQuery({
    queryKey: ["active-exams"],
    queryFn: getActiveExams,
  });

  return (
    <PageShell density="calm" stagger data-testid="candidate-exam-list-shell">
      <PageHeader
        eyebrow={candidatePageCopy.exams}
        title={resolveHeading(data.length, isLoading)}
      />

      {isLoading ? (
        <div className="grid gap-5 md:grid-cols-2" aria-busy="true">
          <Skeleton className="h-[220px] w-full" />
          <Skeleton className="h-[220px] w-full" />
        </div>
      ) : data.length ? (
        <div className="grid gap-5 md:grid-cols-2">
          {data.map((exam) => (
            <ExamCard key={exam.id} exam={exam} />
          ))}
        </div>
      ) : (
        <PageState
          state="empty"
          eyebrow={candidatePageCopy.empty}
          title="暂无可参加考试。"
          description="管理员发布考试后会显示在这里。"
        />
      )}
    </PageShell>
  );
}
