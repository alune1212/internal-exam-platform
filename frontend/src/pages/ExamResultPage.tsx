import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { getAttemptResult } from "@/api/attempts";
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
import { getCurrentCandidate } from "@/lib/candidateSession";
import { candidatePageCopy, candidatePageText } from "@/lib/pageCopy";
import { cn } from "@/lib/utils";

export function ExamResultPage() {
  const [searchParams] = useSearchParams();
  const attemptId = searchParams.get("attemptId");
  const [filter, setFilter] = useState<"all" | "wrong">("all");
  const candidateId = getCurrentCandidate()?.id ?? "anonymous";

  const {
    data: result,
    dataUpdatedAt,
    isError,
    isLoading,
    isFetching,
    refetch,
  } = useQuery({
    queryKey: ["candidate", candidateId, "attempt-result", attemptId],
    queryFn: () => getAttemptResult(attemptId ?? ""),
    enabled: Boolean(attemptId),
    retry: false,
  });

  const hasLoadError = isError && !result;
  const pageHeader = (
    <PageHeader
      title={candidatePageText.result.title}
      description={candidatePageText.result.description}
      actions={
        <Button asChild variant="ghost" size="sm">
          <Link to="/exams">返回考试列表</Link>
        </Button>
      }
    />
  );

  if (isLoading) {
    return (
      <PageShell density="calm" width="wide" stagger>
        {pageHeader}
        <PageSection variant="plain">
          <PageState state="loading" rows={4} surface="inherit" />
        </PageSection>
      </PageShell>
    );
  }

  if (hasLoadError) {
    return (
      <PageShell density="calm" width="wide" stagger>
        {pageHeader}
        <PageSection variant="plain">
          <PageState
            state="error"
            surface="inherit"
            eyebrow={candidatePageCopy.error}
            title={candidatePageText.result.errorTitle}
            description={candidatePageText.result.errorDescription}
            onRetry={() => void refetch()}
          />
        </PageSection>
      </PageShell>
    );
  }

  if (!result) {
    return (
      <PageShell density="calm" width="wide" stagger>
        {pageHeader}
        <PageSection variant="plain">
          <PageState
            state="empty"
            surface="inherit"
            eyebrow={candidatePageCopy.empty}
            title={candidatePageText.result.emptyTitle}
            description={candidatePageText.result.emptyDescription}
          />
        </PageSection>
      </PageShell>
    );
  }

  const visibleQuestions = result.questions
    .map((question, index) => ({ question, index }))
    .filter(({ question }) =>
      filter === "wrong" && !question.is_correct ? true : filter === "all",
    );

  return (
    <PageShell density="calm" width="wide" stagger>
      {isError ? (
        <PageStaleNotice
          lastSuccessfulAt={dataUpdatedAt}
          onRetry={() => refetch()}
          retrying={isFetching}
        />
      ) : null}
      {pageHeader}

      <PageSection variant="summary" data-testid="result-summary">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="flex min-w-0 flex-col gap-3">
            <h2 className="min-w-0 break-words font-display text-display-lg font-semibold text-ink lg:text-display-xl">
              考试已交卷。
            </h2>
            <div className="flex flex-col gap-2">
              <span className="text-status text-muted">最终得分</span>
              <p className="break-words font-mono text-display-2xl font-semibold tabular-nums text-ink">
                {result.score}
                <span className="ml-2 text-body-lg font-normal text-muted">
                  / {result.total_score}
                </span>
              </p>
              {result.pass_score != null ? (
                <div className="flex flex-wrap items-center gap-2 text-body-sm">
                  <StatusPill variant={result.is_passed ? "success" : "error"}>
                    {result.is_passed ? "已通过" : "未通过"}
                  </StatusPill>
                  <span className="text-muted">及格线 {result.pass_score} 分</span>
                </div>
              ) : null}
            </div>
          </div>

          <dl className="grid grid-cols-2 gap-x-8 gap-y-4 border-t border-hairline-soft pt-5 sm:grid-cols-3 lg:border-l lg:border-t-0 lg:pl-8 lg:pt-0">
            <div className="flex min-w-0 flex-col gap-1">
              <dt className="text-status text-muted">答对</dt>
              <dd className="font-mono text-display-md font-semibold tabular-nums text-success">
                {result.correct_count}
              </dd>
            </div>
            <div className="flex min-w-0 flex-col gap-1">
              <dt className="text-status text-muted">答错</dt>
              <dd className="font-mono text-display-md font-semibold tabular-nums text-error">
                {result.wrong_count}
              </dd>
            </div>
            <div className="col-span-2 flex min-w-0 flex-col gap-1 sm:col-span-1">
              <dt className="text-status text-muted">题目数</dt>
              <dd className="font-mono text-display-md font-semibold tabular-nums text-ink">
                {result.questions.length}
              </dd>
            </div>
          </dl>
        </div>
      </PageSection>

      <PageSection
        variant="plain"
        data-testid="result-attempt-context"
        className="gap-5 border-y border-hairline py-6"
      >
        <div className="flex flex-col gap-1">
          <h2 className="min-w-0 break-words font-display text-display-md font-semibold text-ink">
            本次作答
          </h2>
          <p className="text-body-sm text-muted">以下信息来自当前答卷和已选作答记录。</p>
        </div>
        <dl className="grid grid-cols-1 gap-4 text-body-sm sm:grid-cols-3">
          <div className="flex min-w-0 flex-col gap-1">
            <dt className="text-status text-muted">作答编号</dt>
            <dd className="break-words font-mono text-body text-ink">{result.attempt_id}</dd>
          </div>
          <div className="flex min-w-0 flex-col gap-1">
            <dt className="text-status text-muted">当前筛选</dt>
            <dd className="text-body text-ink">{filter === "all" ? "全部题目" : "只看错题"}</dd>
          </div>
          <div className="flex min-w-0 flex-col gap-1">
            <dt className="text-status text-muted">答题记录</dt>
            <dd className="text-body text-ink">{result.questions.length} 题</dd>
          </div>
        </dl>
      </PageSection>

      {!result.show_answer_after_submit ? (
        <PageSection variant="plain" data-testid="result-release-gate">
          <PageState
            state="empty"
            surface="inherit"
            eyebrow="答案发布"
            title="答案与解析尚未发布。"
            description="当前仅显示分数和通过状态。管理员会在全部考试记录结束后一次性发布答案与解析。"
          />
        </PageSection>
      ) : (
        <PageSection variant="plain" data-testid="result-review" className="gap-6">
          <header className="flex flex-col gap-3 border-b border-hairline pb-4 sm:flex-row sm:items-end sm:justify-between">
            <div className="flex min-w-0 flex-col gap-1">
              <h2 className="min-w-0 break-words font-display text-display-md font-semibold text-ink">
                答题回顾
              </h2>
              <p className="text-body-sm text-muted">按题目顺序核对答案、解析和得分。</p>
            </div>
            <PageActions placement="report" aria-label="答题筛选" className="shrink-0">
              <Button
                type="button"
                size="sm"
                variant="ghost"
                aria-pressed={filter === "all"}
                onClick={() => setFilter("all")}
                className={cn(filter === "all" && "bg-surface-card")}
              >
                全部（{result.questions.length}）
              </Button>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                aria-pressed={filter === "wrong"}
                onClick={() => setFilter("wrong")}
                className={cn(filter === "wrong" && "bg-surface-card")}
              >
                只看错题（{result.wrong_count}）
              </Button>
            </PageActions>
          </header>

          <div className="flex flex-col">
            {visibleQuestions.length ? (
              visibleQuestions.map(({ question, index }) => (
                <article
                  key={question.attempt_question_id}
                  className="flex min-w-0 flex-col gap-4 border-b border-hairline-soft py-5 first:pt-0 last:border-b-0 last:pb-0"
                >
                  <header className="flex min-w-0 flex-wrap items-baseline justify-between gap-3">
                    <h3 className="min-w-0 break-words font-display text-display-sm font-semibold text-ink">
                      第 {String(index + 1).padStart(2, "0")} 题
                    </h3>
                    <StatusPill variant={question.is_correct ? "success" : "error"}>
                      {question.is_correct ? "正确" : "错误"}
                    </StatusPill>
                  </header>
                  <p className="min-w-0 break-words text-body text-ink">{question.stem_snapshot}</p>
                  <dl className="grid min-w-0 gap-2 border-t border-hairline-soft pt-4 text-body-sm">
                    <div className="flex min-w-0 flex-wrap items-baseline gap-2">
                      <dt className="shrink-0 text-status text-muted">你的答案</dt>
                      <dd className="min-w-0 break-words text-ink">
                        {question.selected_answer || "未作答"}
                      </dd>
                    </div>
                    <div className="flex min-w-0 flex-wrap items-baseline gap-2">
                      <dt className="shrink-0 text-status text-muted">正确答案</dt>
                      <dd className="min-w-0 break-words text-ink">
                        {question.correct_answer_snapshot ?? "未提供"}
                      </dd>
                    </div>
                    <div className="flex min-w-0 flex-wrap items-baseline gap-2">
                      <dt className="shrink-0 text-status text-muted">得分</dt>
                      <dd className="font-mono tabular-nums text-ink">
                        {question.score_awarded} / {question.score}
                      </dd>
                    </div>
                  </dl>
                  {question.analysis_snapshot ? (
                    <p className="min-w-0 break-words text-body-sm text-muted">
                      <span className="font-medium text-ink">解析：</span>
                      {question.analysis_snapshot}
                    </p>
                  ) : null}
                </article>
              ))
            ) : (
              <PageState
                state="empty"
                surface="inherit"
                eyebrow={candidatePageCopy.empty}
                title="暂无匹配题目。"
                description="切换筛选条件后可查看全部答题结果。"
                className="border-y border-hairline py-10"
              />
            )}
          </div>
        </PageSection>
      )}
    </PageShell>
  );
}
