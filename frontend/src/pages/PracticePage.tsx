import { useMutation, useQuery } from "@tanstack/react-query";
import { CheckCircle2, List, Send, XCircle } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useOutletContext } from "react-router-dom";

import { getPracticeQuestions, submitPracticeAnswer } from "@/api/questions";
import { ExamFocusMode } from "@/components/exam/ExamFocusMode";
import { ExamNavigator } from "@/components/exam/ExamNavigator";
import { ProgressCapsule } from "@/components/exam/ProgressCapsule";
import { ChapterNumber } from "@/components/editorial/ChapterNumber";
import { ContentSkeleton } from "@/components/editorial/ContentSkeleton";
import { EmptyState } from "@/components/editorial/EmptyState";
import type { CandidateSessionContext } from "@/components/layout/CandidateLayout";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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
import { cn, splitAnswer, toggleMultipleAnswer } from "@/lib/utils";
import type { PracticeAnswerResult, PracticeQuestion } from "@/types/question";

type AnswerMap = Record<number, string>;
type ResultMap = Record<number, PracticeAnswerResult>;

export function PracticePage() {
  const { candidate } = useOutletContext<CandidateSessionContext>();
  const [answers, setAnswers] = useState<AnswerMap>({});
  const [results, setResults] = useState<ResultMap>({});
  const [activeIndex, setActiveIndex] = useState(0);
  const [sheetOpen, setSheetOpen] = useState(false);

  const { data = [], isLoading } = useQuery({
    queryKey: ["practice-questions"],
    queryFn: getPracticeQuestions,
  });

  const mutation = useMutation({
    mutationFn: submitPracticeAnswer,
    onSuccess: (result) => {
      setResults((current) => ({ ...current, [result.question_id]: result }));
    },
  });

  const sortedData = useMemo<PracticeQuestion[]>(() => sortByType(data), [data]);
  const total = sortedData.length;
  const activeQuestion: PracticeQuestion | undefined = sortedData[activeIndex];
  const activeResult = activeQuestion ? results[activeQuestion.id] : undefined;
  const answeredCount = useMemo(
    () => sortedData.reduce((count, question) => count + (answers[question.id] ? 1 : 0), 0),
    [answers, sortedData],
  );

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
    [answers, sortedData, results],
  );

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
    if (!candidate) {
      return;
    }
    mutation.mutate({
      question_id: question.id,
      selected_answer: answers[question.id] ?? "",
    });
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
      <div className="mx-auto max-w-3xl py-12">
        <Card className="bg-surface-card">
          <CardContent className="flex flex-col gap-4 p-8">
            <ChapterNumber>CHAPTER 00 · NOT LOGGED IN</ChapterNumber>
            <h1 className="font-display text-display-lg font-semibold text-ink">
              请先登录考试人。
            </h1>
            <p className="text-body text-muted">登录后可提交练习答案并记录练习结果。</p>
            <Button asChild>
              <Link to="/login">去登录</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl py-12">
        <Card className="bg-surface-card">
          <CardContent className="p-8">
            <ContentSkeleton rows={4} className="p-0" />
          </CardContent>
        </Card>
      </div>
    );
  }

  if (total === 0 || !activeQuestion) {
    return (
      <div className="mx-auto max-w-3xl py-12">
        <EmptyState
          chapter="CHAPTER 00 · EMPTY"
          title="题库为空。"
          description="管理员导入题库后会显示在这里。"
        />
      </div>
    );
  }

  const questionType = activeQuestion.question_type as "single" | "multiple" | "judge";
  const isMultiple = questionType === "multiple";
  const selectedLabels = isMultiple ? splitAnswer(answers[activeQuestion.id]) : [];
  const singleValue = !isMultiple ? (answers[activeQuestion.id] ?? "") : "";
  const stemChapterLabel = `CHAPTER ${String(
    perTypeIndexOf(sortedData, activeQuestion.id),
  ).padStart(
    2,
    "0",
  )} · ${getQuestionTypeLabel(activeQuestion.question_type)} · ${activeQuestion.score} 分`;

  const options = activeQuestion.options.map((option) => ({
    label: option.label,
    content: option.content,
    selected: isMultiple ? selectedLabels.includes(option.label) : singleValue === option.label,
    disabled: mutation.isPending,
  }));

  const handleSelectOption = (label: string) => {
    if (mutation.isPending) {
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
    <span
      className={cn(
        "inline-flex items-center gap-2 text-body",
        activeResult.is_correct ? "text-success" : "text-error",
      )}
    >
      {activeResult.is_correct ? <CheckCircle2 /> : <XCircle />}
      {activeResult.is_correct ? "回答正确" : "回答错误"}，正确答案：{activeResult.correct_answer}
    </span>
  ) : (
    <span className="text-body-sm text-muted">提交后显示正确答案和解析。</span>
  );

  return (
    <div data-stagger className="flex flex-col gap-6">
      <div className="flex flex-col gap-3 border-b border-hairline pb-4">
        <ChapterNumber>CHAPTER PR · PRACTICE</ChapterNumber>
        <h1 className="font-display text-display-lg font-semibold text-ink md:text-display-xl">
          刷一遍，<em className="italic">记一遍</em>。
        </h1>
        <p className="max-w-2xl text-body-lg text-muted">
          练习结果不计入正式成绩。提交后即时显示对错与解析。
        </p>
      </div>

      <div className="hidden flex-1 grid-cols-[1fr_240px] gap-8 lg:grid">
        <div id="practice-question-focus" className="flex flex-col gap-4">
          <ExamFocusMode
            progress={{ current: activeIndex + 1, total, answered: answeredCount }}
            remainingSeconds={Number.POSITIVE_INFINITY}
            stem={{ chapterLabel: stemChapterLabel, title: activeQuestion.stem }}
            options={options}
            selectionType={questionType}
            onSelectOption={handleSelectOption}
            nav={{
              onPrev: goPrev,
              onNext: goNext,
              prevDisabled: activeIndex === 0,
              nextDisabled: activeIndex === total - 1,
            }}
          >
            <div className="flex flex-wrap items-center gap-3">
              <Button
                type="button"
                onClick={() => handleSubmit(activeQuestion)}
                disabled={!answers[activeQuestion.id] || mutation.isPending}
                aria-label="提交本题"
              >
                <Send data-icon="inline-start" />
                {mutation.isPending ? "正在提交" : "提交本题"}
              </Button>
              {answerFeedback}
            </div>
            {activeResult?.analysis ? (
              <p className="text-body-sm text-muted">
                <span className="text-caption uppercase tracking-[0.16em]">解析 · </span>
                {activeResult.analysis}
              </p>
            ) : null}
          </ExamFocusMode>
        </div>

        <aside className="self-start lg:sticky lg:top-24 lg:z-30 lg:w-60">
          <ExamNavigator
            items={navItems}
            activeId={activeQuestion.id}
            desktopLayout
            onJump={(_targetId, id) => jumpToQuestion(id)}
          />
        </aside>
      </div>

      <div className="flex flex-1 flex-col pb-24 lg:hidden">
        <ExamFocusMode
          progress={{ current: activeIndex + 1, total, answered: answeredCount }}
          remainingSeconds={Number.POSITIVE_INFINITY}
          stem={{ chapterLabel: stemChapterLabel, title: activeQuestion.stem }}
          options={options}
          selectionType={questionType}
          onSelectOption={handleSelectOption}
          nav={{
            onPrev: goPrev,
            onNext: goNext,
            prevDisabled: activeIndex === 0,
            nextDisabled: activeIndex === total - 1,
          }}
        >
          <div className="flex flex-wrap items-center gap-3">
            <Button
              type="button"
              onClick={() => handleSubmit(activeQuestion)}
              disabled={!answers[activeQuestion.id] || mutation.isPending}
              aria-label="提交本题"
            >
              <Send data-icon="inline-start" />
              {mutation.isPending ? "正在提交" : "提交本题"}
            </Button>
            {activeResult ? answerFeedback : null}
          </div>
          {activeResult?.analysis ? (
            <p className="text-body-sm text-muted">
              <span className="text-caption uppercase tracking-[0.16em]">解析 · </span>
              {activeResult.analysis}
            </p>
          ) : null}
        </ExamFocusMode>

        <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
          <div className="fixed inset-x-0 bottom-3 z-40 flex justify-center px-3">
            <div className="flex w-full max-w-md items-center gap-2 rounded-pill border border-footer bg-footer p-2 shadow-elevate">
              <ProgressCapsule
                current={activeIndex + 1}
                total={total}
                answered={answeredCount}
                variant="dark"
                className="flex-1"
              />
              <SheetTrigger asChild>
                <button
                  type="button"
                  className="inline-flex size-9 shrink-0 items-center justify-center rounded-pill text-canvas"
                >
                  <List aria-hidden="true" />
                  <span className="sr-only">打开题号导航</span>
                </button>
              </SheetTrigger>
            </div>
          </div>

          <SheetContent side="bottom" className="flex h-[80vh] flex-col gap-4 bg-canvas p-5">
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
                onJump={(_targetId, id) => {
                  jumpToQuestion(id);
                  setSheetOpen(false);
                }}
              />
            </div>
          </SheetContent>
        </Sheet>
      </div>
    </div>
  );
}
