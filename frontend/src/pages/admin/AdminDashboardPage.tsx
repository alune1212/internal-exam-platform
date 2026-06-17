import { useQuery } from "@tanstack/react-query";

import { getAdminExams } from "@/api/exams";
import { getAdminQuestions } from "@/api/questions";
import { getAbsentCandidates, getScoreReport } from "@/api/reports";
import { MetricCard } from "@/components/admin/MetricCard";
import { ChapterNumber } from "@/components/editorial/ChapterNumber";
import { ContentSkeleton } from "@/components/editorial/ContentSkeleton";
import { EmptyState } from "@/components/editorial/EmptyState";
import { cn } from "@/lib/utils";

type ActivityTone = "success" | "warning" | "error";

interface ActivityItem {
  id: string;
  title: string;
  caption: string;
  when: string;
  tone: ActivityTone;
}

const TONE_DOT: Record<ActivityTone, string> = {
  success: "bg-success",
  warning: "bg-warning",
  error: "bg-error",
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
    <li className="flex items-center gap-4 border-b border-hairline-soft py-3 last:border-b-0">
      <span className={cn("h-1.5 w-1.5 rounded-pill", TONE_DOT[item.tone])} aria-hidden="true" />
      <div className="flex flex-1 flex-col gap-1">
        <span className="text-body font-medium text-ink">{item.title}</span>
        <span className="text-caption italic text-muted">{item.caption}</span>
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
  const questions = useQuery({ queryKey: ["admin-questions"], queryFn: getAdminQuestions });
  const exams = useQuery({ queryKey: ["admin-exams"], queryFn: getAdminExams });
  const scores = useQuery({ queryKey: ["score-report"], queryFn: () => getScoreReport() });
  const absent = useQuery({
    queryKey: ["absent-candidates", "not_started"],
    queryFn: () => getAbsentCandidates("not_started"),
  });

  const liveExams = (exams.data ?? []).filter(
    (exam) => exam.status === "active" || exam.status === "live",
  ).length;

  const activity: ActivityItem[] = [
    ...(scores.data ?? []).slice(0, 5).map((score) => ({
      id: `score-${score.candidate_name}-${score.exam_title}`,
      title: `${score.candidate_name} 提交了 ${score.exam_title}`,
      caption: `得分 ${score.score} / ${score.total_score}`,
      when: score.submitted_at ?? "-",
      tone: "success" as const,
    })),
    ...(absent.data ?? []).slice(0, 5).map((candidate) => ({
      id: `absent-${candidate.candidate_id}-${candidate.exam_group ?? ""}`,
      title: `${candidate.name} 尚未参加考试`,
      caption: candidate.exam_group ?? candidate.department ?? "-",
      when: "未到",
      tone: "warning" as const,
    })),
  ];

  return (
    <div data-stagger className="flex flex-col gap-8">
      <header className="flex flex-col gap-3">
        <ChapterNumber>CHAPTER 01 · OVERVIEW</ChapterNumber>
        <h1 className="font-display text-display-lg font-semibold text-ink lg:text-display-xl">
          一切就绪。
        </h1>
        <p className="text-body-lg">最近一次刷新 · {new Date().toLocaleString("zh-CN")}</p>
      </header>

      <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="QUESTIONS · 题库"
          value={questions.data?.length ?? 0}
          unit="题"
          caption="所有状态的题目合计"
        />
        <MetricCard
          label="EXAMS LIVE · 进行中"
          value={liveExams}
          unit="场"
          tone="success"
          caption="status 为 active / live"
        />
        <MetricCard
          label="SUBMITTED · 已提交"
          value={scores.data?.length ?? 0}
          unit="次"
          caption="所有考试累计提交次数"
        />
        <MetricCard
          label="NOT STARTED · 未开始"
          value={absent.data?.length ?? 0}
          unit="人"
          tone="warning"
          caption="应考但尚未开始"
        />
      </section>

      <section className="flex flex-col gap-4 rounded-lg border border-hairline bg-canvas p-6 shadow-card lg:p-7">
        <header className="flex flex-col gap-1">
          <p className="text-caption uppercase tracking-[0.16em] text-muted">ACTIVITY · 最近活动</p>
          <h2 className="font-display text-display-sm font-semibold tracking-[-0.04em] text-ink">
            提交与未开始
          </h2>
        </header>
        {questions.isLoading || exams.isLoading || scores.isLoading || absent.isLoading ? (
          <ContentSkeleton rows={3} className="p-0" />
        ) : activity.length ? (
          <ul className="flex flex-col">
            {activity.map((item) => (
              <ActivityRow key={item.id} item={item} />
            ))}
          </ul>
        ) : (
          <EmptyState
            chapter="CHAPTER 00 · EMPTY"
            title="暂无活动记录。"
            description="当有人交卷或缺席名单产生后，最近活动会显示在这里。"
            className="py-8"
          />
        )}
      </section>
    </div>
  );
}
