import { useMutation, useQuery } from "@tanstack/react-query";
import { List, Send } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useOutletContext } from "react-router-dom";

import { getPracticeQuestions, submitPracticeAnswer } from "@/api/questions";
import { ExamFocusMode } from "@/components/exam/ExamFocusMode";
import { ExamNavigator } from "@/components/exam/ExamNavigator";
import { ProgressCapsule } from "@/components/exam/ProgressCapsule";
import { ChapterNumber } from "@/components/editorial/ChapterNumber";
import type { CandidateSessionContext } from "@/components/layout/CandidateLayout";
import { PageShell, PageState } from "@/components/page";
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
import { candidatePageCopy, formatQuestionEyebrow } from "@/lib/pageCopy";
import { splitAnswer, toggleMultipleAnswer } from "@/lib/utils";
import type { PracticeAnswerResult, PracticeQuestion } from "@/types/question";

type AnswerMap = Record<number, string>;
type ResultMap = Record<number, PracticeAnswerResult>;

export function PracticePage() {
  const { candidate } = useOutletContext<CandidateSessionContext>();
  const [answers, setAnswers] = useState<AnswerMap>({});
  const [results, setResults] = useState<ResultMap>({});
  const [activeIndex, setActiveIndex] = useState(0);
  const [sheetOpen, setSheetOpen] = useState(false);

  const {
    data = [],
    isError,
    isLoading,
  } = useQuery({
    queryKey: ["candidate", candidate?.id ?? "anonymous", "practice-questions"],
    queryFn: getPracticeQuestions,
    enabled: Boolean(candidate),
  });

  const mutation = useMutation({
    mutationFn: submitPracticeAnswer,
    onSuccess: (result) => {
      setResults((current) => ({ ...current, [result.question_id]: result }));
    },
  });

  const sortedData = useMemo<PracticeQuestion[]>(() => sortByType(data), [data]);
  const total = sortedData.length;
  const hasLoadError = isError && total === 0;
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
        getTargetId: () => "practice-question-focus",
      }),
    [answers, sortedData],
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
      <PageShell density="focus" width="full" className="mx-auto max-w-3xl py-12">
        <div className="rounded-lg border border-hairline bg-surface-card p-8">
          <PageState
            state="notLoggedIn"
            eyebrow={candidatePageCopy.notLoggedIn}
            title="请先登录考试人。"
            description="登录后可提交练习答案并记录练习结果。"
            className="py-0"
          />
          <div className="mt-6 flex justify-center">
            <Button asChild>
              <Link to="/login">去登录</Link>
            </Button>
          </div>
        </div>
      </PageShell>
    );
  }

  if (isLoading) {
    return (
      <PageShell density="focus" width="full" className="mx-auto max-w-3xl py-12">
        <PageState state="loading" rows={4} className="bg-surface-card p-8" />
      </PageShell>
    );
  }

  if (hasLoadError) {
    return (
      <PageShell density="focus" width="full" className="mx-auto max-w-3xl py-12">
        <PageState
          state="error"
          eyebrow={candidatePageCopy.error}
          title="练习题加载失败。"
          description="请稍后重试，或联系管理员确认题库状态。"
        />
      </PageShell>
    );
  }

  if (total === 0 || !activeQuestion) {
    return (
      <PageShell density="focus" width="full" className="mx-auto max-w-3xl py-12">
        <PageState
          state="empty"
          eyebrow={candidatePageCopy.empty}
          title="练习题库为空。"
          description="管理员导入题库并启用题目后会显示在这里。"
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
    <span className="inline-flex items-center gap-2 text-body text-success">已保存本题作答。</span>
  ) : (
    <span className="text-body-sm text-muted">作答后保存本题记录。</span>
  );

  return (
    <PageShell density="focus" width="full" stagger className="relative">
      <div className="flex flex-col gap-3 border-b border-hairline pb-4">
        <ChapterNumber>{candidatePageCopy.practice}</ChapterNumber>
        <h1 className="font-display text-display-lg font-semibold text-ink lg:text-display-xl">
          练习题库
        </h1>
        <p className="max-w-2xl text-body-lg text-muted">
          练习结果不计入正式成绩。作答后记录本题答案。
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

          <SheetContent
            side="bottom"
            className="flex h-[80vh] flex-col gap-4 rounded-t-lg bg-canvas p-5"
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
