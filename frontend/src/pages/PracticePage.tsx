import { useMutation, useQuery } from "@tanstack/react-query";
import { CheckCircle2, List, RotateCcw, Send, XCircle } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useOutletContext, useSearchParams } from "react-router-dom";

import { getPracticeQuestions, submitPracticeAnswer } from "@/api/questions";
import { ExamFocusMode } from "@/components/exam/ExamFocusMode";
import { ExamNavigator } from "@/components/exam/ExamNavigator";
import { ProgressCapsule } from "@/components/exam/ProgressCapsule";
import type { CandidateSessionContext } from "@/components/layout/CandidateLayout";
import { useCandidatePresentationMode } from "@/components/layout/candidate-presentation-mode";
import { PageActions, PageShell, PageStaleNotice, PageState } from "@/components/page";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import {
  buildQuestionNavItems,
  getQuestionTypeLabel,
  perTypeIndexOf,
  sortByType,
} from "@/lib/questionNavigation";
import { candidatePageCopy, candidatePageText, formatQuestionEyebrow } from "@/lib/pageCopy";
import { splitAnswer, toggleMultipleAnswer } from "@/lib/utils";
import type { PracticeAnswerResult, PracticeQuestion } from "@/types/question";

type AnswerMap = Record<number, string>;
type ResultMap = Record<number, PracticeAnswerResult>;

export function PracticePage() {
  const { candidate } = useOutletContext<CandidateSessionContext>();
  const { requestPresentationMode } = useCandidatePresentationMode();
  const [answers, setAnswers] = useState<AnswerMap>({});
  const [results, setResults] = useState<ResultMap>({});
  const [activeIndex, setActiveIndex] = useState(0);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [searchParams] = useSearchParams();

  const { data, dataUpdatedAt, isError, isLoading, isFetching, refetch } = useQuery({
    queryKey: ["candidate", candidate?.id ?? "anonymous", "practice-questions"],
    queryFn: getPracticeQuestions,
    enabled: Boolean(candidate),
    retry: false,
  });

  const mutation = useMutation({
    mutationFn: submitPracticeAnswer,
    onSuccess: (result) => {
      setResults((current) => ({ ...current, [result.question_id]: result }));
    },
  });

  const sortedData = useMemo<PracticeQuestion[]>(() => sortByType(data ?? []), [data]);
  const total = sortedData.length;
  const hasLoadError = isError && !data;
  const hasStaleError = isError && Boolean(data);
  const staleNotice = hasStaleError ? (
    <PageStaleNotice
      lastSuccessfulAt={dataUpdatedAt}
      onRetry={() => refetch()}
      retrying={isFetching}
    />
  ) : null;
  const activeQuestion: PracticeQuestion | undefined = sortedData[activeIndex];
  const isActivePracticeWorkspace = Boolean(
    candidate && !isLoading && !hasLoadError && total > 0 && activeQuestion,
  );
  const activeResult = activeQuestion ? results[activeQuestion.id] : undefined;
  const answeredCount = useMemo(
    () => sortedData.reduce((count, question) => count + (answers[question.id] ? 1 : 0), 0),
    [answers, sortedData],
  );

  useEffect(() => {
    if (!isActivePracticeWorkspace) return;
    return requestPresentationMode("focus");
  }, [isActivePracticeWorkspace, requestPresentationMode]);

  const navItems = useMemo(
    () =>
      buildQuestionNavItems({
        questions: sortedData,
        answers,
        getSubmittedResult: (question) => {
          const result = results[question.id];
          return result ? (result.is_correct ? "correct" : "wrong") : undefined;
        },
        getTargetId: () => "practice-question-focus",
      }),
    [answers, results, sortedData],
  );

  useEffect(() => {
    const requestedId = Number(searchParams.get("questionId"));
    if (!requestedId) return;
    const requestedIndex = sortedData.findIndex((question) => question.id === requestedId);
    if (requestedIndex >= 0) setActiveIndex(requestedIndex);
  }, [searchParams, sortedData]);

  function handleSingleChange(question: PracticeQuestion, label: string) {
    setAnswers((current) => ({ ...current, [question.id]: label }));
  }

  function handleMultipleChange(question: PracticeQuestion, label: string, checked: boolean) {
    setAnswers((current) => ({
      ...current,
      [question.id]: toggleMultipleAnswer(current[question.id], label, checked),
    }));
  }

  function handleSubmit(question: PracticeQuestion) {
    if (!candidate || results[question.id]) {
      return;
    }
    mutation.mutate({
      question_id: question.id,
      selected_answer: answers[question.id] ?? "",
    });
  }

  function handleRetry(question: PracticeQuestion) {
    setResults((current) => {
      const next = { ...current };
      delete next[question.id];
      return next;
    });
    setAnswers((current) => ({ ...current, [question.id]: "" }));
  }

  const goPrev = useCallback(() => setActiveIndex((index) => Math.max(0, index - 1)), []);
  const goNext = useCallback(
    () => setActiveIndex((index) => Math.min(sortedData.length - 1, index + 1)),
    [sortedData.length],
  );

  useEffect(() => {
    function handleKeydown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      if (target) {
        const tag = target.tagName.toLowerCase();
        if (tag === "input" || tag === "textarea" || target.isContentEditable) {
          return;
        }
      }
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        goPrev();
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        goNext();
      }
    }
    window.addEventListener("keydown", handleKeydown);
    return () => window.removeEventListener("keydown", handleKeydown);
  }, [goNext, goPrev]);

  if (!candidate) {
    return (
      <PageShell density="calm" width="reading">
        <PageState
          state="notLoggedIn"
          surface="inherit"
          eyebrow={candidatePageCopy.notLoggedIn}
          title={candidatePageText.practice.loginTitle}
          description={candidatePageText.practice.loginDescription}
          className="py-0"
        />
        <PageActions placement="card" align="center" className="justify-center">
          <Button asChild>
            <Link to="/login?returnTo=%2Fpractice">去登录</Link>
          </Button>
        </PageActions>
      </PageShell>
    );
  }

  if (isLoading) {
    return (
      <PageShell density="calm" width="reading">
        <PageState state="loading" rows={4} surface="inherit" />
      </PageShell>
    );
  }

  if (hasLoadError) {
    return (
      <PageShell density="calm" width="reading">
        <PageState
          state="error"
          surface="inherit"
          eyebrow={candidatePageCopy.error}
          title={candidatePageText.practice.errorTitle}
          description={candidatePageText.practice.errorDescription}
          onRetry={() => void refetch()}
        />
      </PageShell>
    );
  }

  if (total === 0 || !activeQuestion) {
    return (
      <PageShell density="calm" width="reading">
        {staleNotice}
        <PageState
          state="empty"
          surface="inherit"
          eyebrow={candidatePageCopy.empty}
          title={candidatePageText.practice.emptyTitle}
          description={candidatePageText.practice.emptyDescription}
        />
      </PageShell>
    );
  }

  const questionType = activeQuestion.question_type as "single" | "multiple" | "judge";
  const isMultiple = questionType === "multiple";
  const selectedLabels = isMultiple ? splitAnswer(answers[activeQuestion.id]) : [];
  const singleValue = !isMultiple ? (answers[activeQuestion.id] ?? "") : "";
  const stemChapterLabel = formatQuestionEyebrow(
    perTypeIndexOf(sortedData, activeQuestion.id),
    getQuestionTypeLabel(activeQuestion.question_type),
    activeQuestion.score,
  );

  const options = activeQuestion.options.map((option) => ({
    label: option.label,
    content: option.content,
    selected: isMultiple ? selectedLabels.includes(option.label) : singleValue === option.label,
    disabled: mutation.isPending || Boolean(activeResult),
  }));

  const handleSelectOption = (label: string) => {
    if (mutation.isPending || activeResult) {
      return;
    }
    if (isMultiple) {
      handleMultipleChange(activeQuestion, label, !selectedLabels.includes(label));
    } else {
      handleSingleChange(activeQuestion, label);
    }
  };

  const jumpToQuestion = (id: number) => {
    const nextIndex = sortedData.findIndex((question) => question.id === id);
    if (nextIndex >= 0) {
      setActiveIndex(nextIndex);
    }
  };

  const answerFeedback = activeResult ? (
    <Alert variant={activeResult.is_correct ? "success" : "error"} className="w-full gap-4 p-4">
      <p className="flex items-center gap-2 font-medium">
        {activeResult.is_correct ? (
          <CheckCircle2 aria-hidden="true" />
        ) : (
          <XCircle aria-hidden="true" />
        )}
        {activeResult.is_correct ? "回答正确" : "回答错误"}
      </p>
      <p className="text-body text-ink">正确答案：{activeResult.correct_answer}</p>
      <ul className="flex flex-col gap-2 text-body-sm">
        {activeResult.option_comparison.map((option) => (
          <li key={option.label} className="flex flex-wrap gap-2">
            <span className="font-mono text-ink">{option.label}</span>
            <span className="text-muted">{option.content}</span>
            {option.selected ? <span className="text-ink">你的选择</span> : null}
            {option.correct ? <span className="text-success">正确选项</span> : null}
          </li>
        ))}
      </ul>
      <div>
        <p className="text-caption uppercase tracking-caption text-muted">答案解析</p>
        <p className="mt-1 whitespace-pre-wrap text-body text-ink">
          {activeResult.analysis || "本题暂无解析。"}
        </p>
      </div>
      <Button type="button" variant="outline" onClick={() => handleRetry(activeQuestion)}>
        <RotateCcw data-icon="inline-start" />
        重新练习本题
      </Button>
    </Alert>
  ) : (
    <span className="text-body-sm text-muted">提交后立即显示正确答案与解析。</span>
  );

  return (
    <PageShell density="focus" width="focus" stagger className="relative">
      <PageActions aria-label="练习辅助操作" className="justify-end">
        <Button asChild variant="outline" size="sm">
          <Link to="/practice/wrong-questions">查看错题复习</Link>
        </Button>
      </PageActions>

      {staleNotice}

      <div className="hidden flex-1 grid-cols-[1fr_240px] gap-8 lg:grid">
        <div id="practice-question-focus" className="flex flex-col gap-4">
          <ExamFocusMode
            progress={{ current: activeIndex + 1, total, answered: answeredCount }}
            remainingSeconds={Number.POSITIVE_INFINITY}
            stem={{ chapterLabel: stemChapterLabel, title: activeQuestion.stem }}
            options={options}
            selectionType={questionType}
            questionHeadingId="practice-question-heading-desktop"
            onSelectOption={handleSelectOption}
            nav={{
              onPrev: goPrev,
              onNext: goNext,
              prevDisabled: activeIndex === 0,
              nextDisabled: activeIndex === total - 1,
            }}
          >
            <div className="flex flex-wrap items-center gap-3">
              {!activeResult ? (
                <Button
                  type="button"
                  onClick={() => handleSubmit(activeQuestion)}
                  disabled={!answers[activeQuestion.id] || mutation.isPending}
                  aria-label="提交本题"
                >
                  <Send data-icon="inline-start" />
                  {mutation.isPending ? "正在提交" : "提交本题"}
                </Button>
              ) : null}
              {answerFeedback}
            </div>
          </ExamFocusMode>
        </div>

        <aside className="self-start lg:sticky lg:top-24 lg:z-sticky lg:w-60">
          <ExamNavigator
            items={navItems}
            activeId={activeQuestion.id}
            desktopLayout
            idPrefix="exam-nav-desktop"
            onJump={(_targetId, id) => jumpToQuestion(id)}
          />
        </aside>
      </div>

      <div className="flex min-w-0 flex-1 flex-col pb-[calc(6rem+env(safe-area-inset-bottom))] lg:hidden">
        <ExamFocusMode
          progress={{ current: activeIndex + 1, total, answered: answeredCount }}
          remainingSeconds={Number.POSITIVE_INFINITY}
          stem={{ chapterLabel: stemChapterLabel, title: activeQuestion.stem }}
          options={options}
          selectionType={questionType}
          questionHeadingId="practice-question-heading-mobile"
          onSelectOption={handleSelectOption}
          nav={{
            onPrev: goPrev,
            onNext: goNext,
            prevDisabled: activeIndex === 0,
            nextDisabled: activeIndex === total - 1,
          }}
        >
          <div className="flex flex-wrap items-center gap-3">
            {!activeResult ? (
              <Button
                type="button"
                onClick={() => handleSubmit(activeQuestion)}
                disabled={!answers[activeQuestion.id] || mutation.isPending}
                aria-label="提交本题"
              >
                <Send data-icon="inline-start" />
                {mutation.isPending ? "正在提交" : "提交本题"}
              </Button>
            ) : null}
            {answerFeedback}
          </div>
        </ExamFocusMode>

        <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
          <div className="pointer-events-none fixed inset-x-0 bottom-0 z-overlay flex justify-center px-3 pb-[max(var(--space-inline),env(safe-area-inset-bottom))] pt-3 landscape:justify-end">
            <div className="pointer-events-auto flex w-full max-w-md items-center gap-2 rounded-pill border border-footer bg-footer p-2 shadow-elevate landscape:w-auto">
              <ProgressCapsule
                current={activeIndex + 1}
                total={total}
                answered={answeredCount}
                variant="dark"
                className="min-w-0 flex-1 landscape:hidden"
              />
              <SheetTrigger asChild>
                <button
                  type="button"
                  className="inline-flex min-h-touch-target min-w-touch-target shrink-0 items-center justify-center rounded-pill text-canvas"
                >
                  <List aria-hidden="true" />
                  <span className="sr-only">打开题号导航</span>
                </button>
              </SheetTrigger>
            </div>
          </div>

          <SheetContent
            side="bottom"
            className="flex max-h-[85dvh] min-h-0 flex-col gap-4 rounded-t-lg bg-canvas p-5 pb-[calc(1.25rem+env(safe-area-inset-bottom))]"
          >
            <SheetHeader className="border-b border-hairline pb-3">
              <SheetTitle className="font-display text-display-sm">题号导航</SheetTitle>
              <SheetDescription className="sr-only">选择练习题号。</SheetDescription>
            </SheetHeader>
            <div className="flex-1 overflow-y-auto overscroll-contain">
              <ExamNavigator
                items={navItems}
                activeId={activeQuestion.id}
                sheetLayout
                desktopLayout={false}
                idPrefix="exam-nav-mobile"
                onJump={(_targetId, id) => {
                  jumpToQuestion(id);
                  setSheetOpen(false);
                }}
              />
            </div>
          </SheetContent>
        </Sheet>
      </div>
    </PageShell>
  );
}
