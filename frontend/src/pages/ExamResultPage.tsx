import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { getAttemptResult } from "@/api/attempts";
import { ChapterNumber } from "@/components/editorial/ChapterNumber";
import { ContentSkeleton } from "@/components/editorial/ContentSkeleton";
import { EmptyState } from "@/components/editorial/EmptyState";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function ExamResultPage() {
  const [searchParams] = useSearchParams();
  const attemptId = searchParams.get("attemptId");
  const [filter, setFilter] = useState<"all" | "wrong">("all");

  const { data: result, isLoading } = useQuery({
    queryKey: ["attempt-result", attemptId],
    queryFn: () => getAttemptResult(attemptId ?? ""),
    enabled: Boolean(attemptId),
  });

  const visibleQuestions =
    result?.questions.filter((question) => (filter === "wrong" ? !question.is_correct : true)) ??
    [];

  return (
    <div data-stagger className="flex flex-col gap-6">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-hairline pb-4">
        <div className="flex flex-col gap-1">
          <ChapterNumber>CHAPTER 99 · RESULT</ChapterNumber>
          <h1 className="font-display text-display-md font-semibold text-ink">考试结果</h1>
        </div>
        <Button asChild variant="ghost" size="sm">
          <Link to="/exams">返回考试列表</Link>
        </Button>
      </header>

      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        <Card className="border-0 bg-footer text-canvas shadow-pop">
          <CardContent className="flex flex-col gap-6 p-6 md:p-8">
            <ChapterNumber className="text-footer-soft">CHAPTER 99 · RESULT</ChapterNumber>
            <h1 className="font-display text-display-xl font-semibold leading-[1.08] text-canvas">
              考试结束。
            </h1>

            <div className="flex flex-col gap-2 border-t border-footer-soft pt-6">
              <span className="text-caption uppercase tracking-[0.16em] text-footer-soft">
                YOUR SCORE · 你的分数
              </span>
              <p className="font-display text-display-xl font-semibold tabular-nums leading-none text-canvas md:text-display-2xl">
                {result ? `${result.score}` : "—"}
                <span className="ml-2 text-body-lg text-footer-soft">
                  / {result ? result.total_score : "—"}
                </span>
              </p>
              {result?.pass_score != null ? (
                <div className="flex flex-wrap items-center gap-2 text-body-sm">
                  <span
                    className={cn(
                      "font-display text-display-sm font-semibold",
                      result.is_passed ? "text-success-on-dark" : "text-error-on-dark",
                    )}
                  >
                    {result.is_passed ? "PASSED · 已通过" : "FAILED · 未通过"}
                  </span>
                  <span className="text-footer-soft">及格线 {result.pass_score} 分</span>
                </div>
              ) : null}
            </div>

            <div className="flex flex-wrap items-center gap-6 border-t border-footer-soft pt-6 text-body">
              <div className="flex flex-col gap-1">
                <span className="text-caption uppercase tracking-[0.16em] text-footer-soft">
                  正确
                </span>
                <span className="font-display text-display-md font-semibold tabular-nums text-success-on-dark">
                  {result?.correct_count ?? "—"}
                </span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-caption uppercase tracking-[0.16em] text-footer-soft">
                  错误
                </span>
                <span className="font-display text-display-md font-semibold tabular-nums text-error-on-dark">
                  {result?.wrong_count ?? "—"}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        <section className="flex flex-col gap-4">
          <header className="flex flex-wrap items-end justify-between gap-3 border-b border-hairline pb-3">
            <div className="flex flex-col gap-1">
              <span className="font-display text-caption uppercase italic tracking-[0.18em] text-muted">
                CHAPTER R · REVIEW
              </span>
              <h2 className="font-display text-display-md font-semibold text-ink">答案与解析</h2>
            </div>
            <div className="inline-flex items-center gap-2 rounded-pill border border-hairline bg-canvas p-1 text-body-sm">
              <button
                type="button"
                onClick={() => setFilter("all")}
                className={cn(
                  "rounded-pill px-4 py-1",
                  filter === "all" ? "bg-ink text-canvas" : "text-muted",
                )}
              >
                全部 ({result?.questions.length ?? 0})
              </button>
              <button
                type="button"
                onClick={() => setFilter("wrong")}
                className={cn(
                  "rounded-pill px-4 py-1",
                  filter === "wrong" ? "bg-ink text-canvas" : "text-muted",
                )}
              >
                只看错题 ({result?.wrong_count ?? 0})
              </button>
            </div>
          </header>

          <div className="flex flex-col gap-4">
            {visibleQuestions.length ? (
              visibleQuestions.map((question, index) => (
                <article
                  key={question.attempt_question_id}
                  className="flex flex-col gap-3 rounded-lg border border-hairline bg-canvas p-5 shadow-card"
                >
                  <header className="flex items-baseline justify-between gap-3">
                    <span className="font-mono text-caption uppercase tracking-[0.16em] text-muted">
                      Q {String(index + 1).padStart(2, "0")}
                    </span>
                    <span
                      className={cn(
                        "text-caption uppercase tracking-[0.16em]",
                        question.is_correct ? "text-success" : "text-error",
                      )}
                    >
                      {question.is_correct ? "CORRECT · 正确" : "WRONG · 错误"}
                    </span>
                  </header>
                  <p className="text-body text-ink">{question.stem_snapshot}</p>
                  <dl className="grid gap-1 border-t border-hairline pt-3 text-body-sm">
                    <div className="flex flex-wrap items-baseline gap-2">
                      <dt className="text-caption uppercase tracking-[0.16em] text-muted">
                        你的答案
                      </dt>
                      <dd className="text-ink">{question.selected_answer || "未作答"}</dd>
                    </div>
                    <div className="flex flex-wrap items-baseline gap-2">
                      <dt className="text-caption uppercase tracking-[0.16em] text-muted">
                        正确答案
                      </dt>
                      <dd className="text-ink">{question.correct_answer_snapshot}</dd>
                    </div>
                    <div className="flex flex-wrap items-baseline gap-2">
                      <dt className="text-caption uppercase tracking-[0.16em] text-muted">得分</dt>
                      <dd className="font-mono tabular-nums text-ink">
                        {question.score_awarded} / {question.score}
                      </dd>
                    </div>
                  </dl>
                  {question.analysis_snapshot ? (
                    <p className="text-body-sm text-muted">
                      <span className="text-caption uppercase tracking-[0.16em]">解析 · </span>
                      {question.analysis_snapshot}
                    </p>
                  ) : null}
                </article>
              ))
            ) : (
              <div className="rounded-lg border border-hairline bg-canvas">
                {isLoading ? (
                  <ContentSkeleton rows={4} />
                ) : (
                  <EmptyState
                    chapter="CHAPTER 00 · EMPTY"
                    title="暂无结果，请先完成考试。"
                    description="提交考试后，这里会显示答案、得分与解析。"
                    className="py-10"
                  />
                )}
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
