import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, Clock, FileText, Hash } from "lucide-react";
import { Link } from "react-router-dom";

import { getActiveExams } from "@/api/exams";
import { ChapterNumber } from "@/components/editorial/ChapterNumber";
import { EmptyState } from "@/components/editorial/EmptyState";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
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

function ExamCard({ exam }: { exam: Exam }) {
  const isLive = exam.status === "active" || exam.status === "live";
  const totalQuestions = resolveQuestionCount(exam.question_rule);
  const startsAt =
    typeof exam.question_rule.starts_at === "string" ? exam.question_rule.starts_at : null;
  const totalScore =
    typeof exam.question_rule.total_score === "number" ? exam.question_rule.total_score : null;

  return (
    <article className="flex flex-col gap-5 rounded-lg border border-hairline bg-canvas p-6 shadow-card lg:p-7">
      <p className="font-body text-caption font-medium uppercase italic tracking-[0.18em] text-muted">
        {isLive ? "LIVE · 进行中" : "DRAFT · 未开始"}
      </p>
      <h2 className="font-display text-[22px] font-semibold tracking-[-0.04em] text-ink lg:text-[24px]">
        {exam.title}
      </h2>
      <dl className="grid grid-cols-3 gap-3 border-y border-hairline-soft py-3 text-caption text-muted">
        <div className="flex flex-col gap-1">
          <dt className="flex items-center gap-1 uppercase tracking-[0.16em]">
            <Clock className="h-3 w-3" /> 时长
          </dt>
          <dd className="font-mono text-base text-ink">{exam.duration_minutes} 分钟</dd>
        </div>
        <div className="flex flex-col gap-1">
          <dt className="flex items-center gap-1 uppercase tracking-[0.16em]">
            <FileText className="h-3 w-3" /> 题数
          </dt>
          <dd className="font-mono text-base text-ink">{totalQuestions ?? "-"}</dd>
        </div>
        <div className="flex flex-col gap-1">
          <dt className="flex items-center gap-1 uppercase tracking-[0.16em]">
            <Hash className="h-3 w-3" /> 总分
          </dt>
          <dd className="font-mono text-base text-ink">{totalScore ?? "-"}</dd>
        </div>
      </dl>
      <div className="flex items-center justify-between gap-3">
        <p className="text-caption italic text-muted">
          {startsAt ? `开始时间 · ${startsAt}` : "随时开考"}
        </p>
        <Button asChild size="sm">
          <Link to={`/exams/${exam.id}/start`}>
            {isLive ? "进入考试" : "查看说明"}
            <ArrowUpRight data-icon="inline-end" />
          </Link>
        </Button>
      </div>
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
    <div data-stagger className="flex flex-col gap-8">
      <header className="flex flex-col gap-3">
        <ChapterNumber>CHAPTER 02 · EXAMS</ChapterNumber>
        <h1 className="font-display text-display-lg font-semibold text-ink lg:text-display-xl">
          {resolveHeading(data.length, isLoading)}
        </h1>
      </header>

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
        <EmptyState
          chapter="CHAPTER 02 · EXAMS"
          title="暂无可参加考试。"
          description="管理员发布 active 考试后会显示在这里。"
        />
      )}
    </div>
  );
}
