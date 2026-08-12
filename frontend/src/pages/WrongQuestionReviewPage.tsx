import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, RotateCcw } from "lucide-react";
import { useState } from "react";
import { Link, useOutletContext } from "react-router-dom";

import { getWrongPracticeQuestions } from "@/api/questions";
import type { CandidateSessionContext } from "@/components/layout/CandidateLayout";
import { PageShell, PageState } from "@/components/page";
import { Button } from "@/components/ui/button";

type MasteryFilter = "all" | "mastered" | "learning";

export function WrongQuestionReviewPage() {
  const { candidate } = useOutletContext<CandidateSessionContext>();
  const [category1, setCategory1] = useState("");
  const [category2, setCategory2] = useState("");
  const [mastery, setMastery] = useState<MasteryFilter>("all");
  const filters = {
    category_1: category1.trim() || undefined,
    category_2: category2.trim() || undefined,
    mastered: mastery === "all" ? undefined : mastery === "mastered",
  };
  const {
    data = [],
    isError,
    isLoading,
  } = useQuery({
    queryKey: ["candidate", candidate?.id ?? "anonymous", "practice-wrong", filters],
    queryFn: () => getWrongPracticeQuestions(filters),
    enabled: Boolean(candidate),
  });

  if (!candidate) {
    return (
      <PageShell className="mx-auto max-w-3xl py-12">
        <PageState
          state="notLoggedIn"
          title="请先登录。"
          description="登录后可查看自己的错题记录。"
        />
      </PageShell>
    );
  }

  return (
    <PageShell stagger className="max-w-4xl">
      <header className="flex flex-col gap-4 border-b border-hairline pb-5">
        <Button asChild variant="ghost" className="self-start">
          <Link to="/practice">
            <ArrowLeft data-icon="inline-start" />
            返回练习
          </Link>
        </Button>
        <div>
          <p className="text-caption uppercase tracking-[0.18em] text-muted">WRONG · 错题复习</p>
          <h1 className="mt-2 font-display text-display-lg font-semibold text-ink">错题复习</h1>
          <p className="mt-2 text-body text-muted">
            历史错误不会删除；最后一次答对后标记为已掌握。
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-3" aria-label="错题筛选">
          <label className="flex flex-col gap-1 text-body-sm text-muted">
            一级分类
            <input
              className="rounded-md border border-hairline bg-canvas px-3 py-2 text-ink"
              value={category1}
              onChange={(event) => setCategory1(event.target.value)}
            />
          </label>
          <label className="flex flex-col gap-1 text-body-sm text-muted">
            二级分类
            <input
              className="rounded-md border border-hairline bg-canvas px-3 py-2 text-ink"
              value={category2}
              onChange={(event) => setCategory2(event.target.value)}
            />
          </label>
          <label className="flex flex-col gap-1 text-body-sm text-muted">
            掌握状态
            <select
              className="rounded-md border border-hairline bg-canvas px-3 py-2 text-ink"
              value={mastery}
              onChange={(event) => setMastery(event.target.value as MasteryFilter)}
            >
              <option value="all">全部</option>
              <option value="learning">待巩固</option>
              <option value="mastered">已掌握</option>
            </select>
          </label>
        </div>
      </header>

      {isLoading ? <PageState state="loading" rows={3} /> : null}
      {isError ? (
        <PageState state="error" title="错题记录加载失败。" description="请稍后重试。" />
      ) : null}
      {!isLoading && !isError && data.length === 0 ? (
        <PageState
          state="empty"
          title="当前筛选下没有错题"
          description="完成练习后，答错的题目会出现在这里。"
        />
      ) : null}
      <div className="flex flex-col gap-5">
        {data.map((item) => (
          <article
            key={item.question_id}
            className="rounded-lg border border-hairline bg-surface-card p-5 shadow-card"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className={item.mastered ? "text-success" : "text-error"}>
                {item.mastered ? "已掌握" : "待巩固"}
              </span>
              <span className="text-body-sm text-muted">
                错 {item.incorrect_count} 次 · 共练习 {item.total_attempts} 次
              </span>
            </div>
            <h2 className="mt-3 font-display text-display-sm font-semibold text-ink">
              {item.stem}
            </h2>
            <p className="mt-3 text-body text-ink">正确答案：{item.correct_answer}</p>
            <p className="mt-2 whitespace-pre-wrap text-body text-muted">
              {item.analysis || "本题暂无解析。"}
            </p>
            <div className="mt-4 flex flex-wrap items-center gap-3">
              {item.category_1 ? (
                <span className="text-caption text-muted">{item.category_1}</span>
              ) : null}
              {item.category_2 ? (
                <span className="text-caption text-muted">{item.category_2}</span>
              ) : null}
              {item.status === "active" ? (
                <Button asChild variant="outline" className="ml-auto">
                  <Link to={`/practice?questionId=${item.question_id}`}>
                    <RotateCcw data-icon="inline-start" />
                    再次练习
                  </Link>
                </Button>
              ) : (
                <span className="ml-auto text-body-sm text-muted">题目已停用，仅保留历史</span>
              )}
            </div>
          </article>
        ))}
      </div>
    </PageShell>
  );
}
