import { useMutation, useQuery } from "@tanstack/react-query";
import { List, Send } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { getAttempt, saveAttemptAnswers, submitAttempt } from "@/api/attempts";
import { ApiError, getErrorMessage } from "@/api/client";
import { ExamFocusMode } from "@/components/exam/ExamFocusMode";
import { ExamNavigator } from "@/components/exam/ExamNavigator";
import { ProgressCapsule } from "@/components/exam/ProgressCapsule";
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
import { getCurrentCandidate } from "@/lib/candidateSession";
import { candidateActionCopy, candidatePageCopy, formatQuestionEyebrow } from "@/lib/pageCopy";
import { splitAnswer, toggleMultipleAnswer } from "@/lib/utils";
import type { AttemptQuestion } from "@/types/attempt";

type AnswerMap = Record<number, string>;
type SaveStatus = "saved" | "pending" | "saving" | "error";

const EMPTY_QUESTIONS: AttemptQuestion[] = [];
const SUBMITTED_STATUSES = new Set(["submitted", "auto_submitted"]);
const SAVE_DEBOUNCE_MS = 150;
const SAVE_STATUS_LABEL: Record<SaveStatus, string> = {
  pending: candidateActionCopy.savePending,
  saving: candidateActionCopy.savingAnswer,
  saved: candidateActionCopy.savedAnswer,
  error: candidateActionCopy.saveFailed,
};

export function ExamTakingPage() {
  const { examId = "1" } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const attemptId = searchParams.get("attemptId");

  const [answers, setAnswers] = useState<AnswerMap>({});
  const [now, setNow] = useState(() => Date.now());
  const [attemptClock, setAttemptClock] = useState<{ serverNow: number; clientNow: number } | null>(
    null,
  );
  const [activeIndex, setActiveIndex] = useState(0);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("saved");
  const [submitErrorVisible, setSubmitErrorVisible] = useState(false);
  const latestAnswersRef = useRef<AnswerMap>({});
  const saveQueueRef = useRef<Promise<void>>(Promise.resolve());
  const saveDebounceRef = useRef<number | null>(null);
  const submitStartedRef = useRef(false);
  const candidateId = getCurrentCandidate()?.id ?? "anonymous";

  const {
    data: attempt,
    error: attemptError,
    isError: isAttemptError,
    isLoading,
  } = useQuery({
    queryKey: ["candidate", candidateId, "attempt", attemptId],
    queryFn: () => getAttempt(attemptId ?? ""),
    enabled: Boolean(attemptId),
  });

  const sortedQuestions = useMemo<AttemptQuestion[]>(
    () => (attempt ? sortByType(attempt.questions) : EMPTY_QUESTIONS),
    [attempt],
  );
  const total = sortedQuestions.length;
  const activeQuestion: AttemptQuestion | undefined = sortedQuestions[activeIndex];
  const isLastQuestion = total > 0 && activeIndex === total - 1;
  const hasAttemptLoadError = isAttemptError && !attempt;

  const buildAnswerItems = useCallback(
    () =>
      sortedQuestions.map((question) => ({
        attempt_question_id: question.id,
        selected_answer: latestAnswersRef.current[question.id] ?? "",
      })),
    [sortedQuestions],
  );

  const saveMutation = useMutation({
    mutationFn: (items: Array<{ attempt_question_id: number; selected_answer: string }>) =>
      saveAttemptAnswers(attemptId ?? "", items),
    retry: (failureCount, error) => !(error instanceof ApiError) && failureCount < 2,
  });

  const cancelPendingSave = useCallback(() => {
    if (saveDebounceRef.current) {
      window.clearTimeout(saveDebounceRef.current);
      saveDebounceRef.current = null;
    }
  }, []);

  const performFullSave = useCallback(
    async ({ throwOnError = false }: { throwOnError?: boolean } = {}) => {
      if (!attempt) {
        return;
      }
      const items = buildAnswerItems();
      const run = saveQueueRef.current
        .catch(() => undefined)
        .then(async () => {
          setSaveStatus("saving");
          setSubmitErrorVisible(false);
          await saveMutation.mutateAsync(items);
          setSaveStatus("saved");
        });
      const guarded = run.catch((error: unknown) => {
        setSaveStatus("error");
        if (throwOnError) {
          throw error;
        }
      });
      saveQueueRef.current = guarded;
      await guarded;
    },
    [attempt, buildAnswerItems, saveMutation],
  );

  const submitMutation = useMutation({
    mutationFn: async (submitType: "manual" = "manual") => {
      if (!attempt) {
        return null;
      }
      cancelPendingSave();
      await saveQueueRef.current.catch(() => undefined);
      await performFullSave({ throwOnError: true });
      return submitAttempt(String(attempt.id), submitType);
    },
    onSuccess: (result) => {
      if (result) {
        navigate(`/exams/${examId}/result?attemptId=${result.attempt_id}`);
      }
    },
    onError: () => {
      setSubmitErrorVisible(true);
    },
    retry: false,
  });

  const scheduleFullSave = useCallback(() => {
    if (!attempt) {
      return;
    }
    setSaveStatus("pending");
    setSubmitErrorVisible(false);
    cancelPendingSave();
    saveDebounceRef.current = window.setTimeout(() => {
      saveDebounceRef.current = null;
      void performFullSave();
    }, SAVE_DEBOUNCE_MS);
  }, [attempt, cancelPendingSave, performFullSave]);

  useEffect(
    () => () => {
      if (saveDebounceRef.current) {
        window.clearTimeout(saveDebounceRef.current);
      }
    },
    [],
  );

  const requestSubmit = useCallback(
    (submitType: "manual") => {
      if (submitStartedRef.current || submitMutation.isPending) {
        return;
      }
      submitStartedRef.current = true;
      submitMutation.mutate(submitType, {
        onError: () => {
          submitStartedRef.current = false;
        },
      });
    },
    [submitMutation],
  );

  useEffect(() => {
    if (!attempt) {
      return;
    }
    if (SUBMITTED_STATUSES.has(attempt.status)) {
      return;
    }
    const initialAnswers = Object.fromEntries(
      attempt.questions.map((question) => [question.id, question.selected_answer ?? ""]),
    );
    latestAnswersRef.current = initialAnswers;
    setAnswers(initialAnswers);
    setSaveStatus("saved");
  }, [attempt]);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!attempt) {
      setAttemptClock(null);
      return;
    }
    const serverNow = new Date(attempt.server_now).getTime();
    setAttemptClock({
      serverNow: Number.isFinite(serverNow) ? serverNow : Date.now(),
      clientNow: Date.now(),
    });
  }, [attempt]);

  const remainingSeconds = useMemo(() => {
    if (!attempt) {
      return Number.POSITIVE_INFINITY;
    }
    const endsAt = new Date(attempt.ends_at).getTime();
    const serverOffset = attemptClock ? attemptClock.clientNow - attemptClock.serverNow : 0;
    return Math.max(0, Math.floor((endsAt - (now - serverOffset)) / 1000));
  }, [attempt, attemptClock, now]);

  const autoSubmittedRef = useRef(false);
  useEffect(() => {
    if (
      !attempt ||
      remainingSeconds !== 0 ||
      autoSubmittedRef.current ||
      submitMutation.isPending
    ) {
      return;
    }
    autoSubmittedRef.current = true;
    requestSubmit("manual");
  }, [attempt, remainingSeconds, requestSubmit, submitMutation.isPending]);

  const answeredCount = useMemo(() => {
    return sortedQuestions.reduce((count, question) => count + (answers[question.id] ? 1 : 0), 0);
  }, [answers, sortedQuestions]);

  const navItems = useMemo(
    () =>
      buildQuestionNavItems({
        questions: sortedQuestions,
        answers,
        getTargetId: () => "exam-question-focus",
      }),
    [answers, sortedQuestions],
  );

  const handleSingleChange = useCallback(
    (question: AttemptQuestion, label: string) => {
      const nextAnswers = { ...latestAnswersRef.current, [question.id]: label };
      latestAnswersRef.current = nextAnswers;
      setAnswers(nextAnswers);
      scheduleFullSave();
    },
    [scheduleFullSave],
  );

  const handleMultipleChange = useCallback(
    (question: AttemptQuestion, label: string, checked: boolean) => {
      const next = toggleMultipleAnswer(latestAnswersRef.current[question.id], label, checked);
      const nextAnswers = { ...latestAnswersRef.current, [question.id]: next };
      latestAnswersRef.current = nextAnswers;
      setAnswers(nextAnswers);
      scheduleFullSave();
    },
    [scheduleFullSave],
  );

  function handleSave() {
    if (!attempt) {
      return;
    }
    cancelPendingSave();
    void performFullSave();
  }

  const goPrev = useCallback(() => {
    setActiveIndex((index) => Math.max(0, index - 1));
  }, []);

  const goNext = useCallback(() => {
    if (!attempt) {
      return;
    }
    setActiveIndex((index) => Math.min(sortedQuestions.length - 1, index + 1));
  }, [attempt, sortedQuestions]);

  const handleNextAction = useCallback(() => {
    if (isLastQuestion) {
      requestSubmit("manual");
      return;
    }
    goNext();
  }, [goNext, isLastQuestion, requestSubmit]);

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

      if (!activeQuestion || submitMutation.isPending || submitStartedRef.current) {
        return;
      }

      const key = event.key.toUpperCase();
      const numericIndex = Number.parseInt(event.key, 10);
      const label =
        Number.isInteger(numericIndex) && numericIndex >= 1 && numericIndex <= 9
          ? String.fromCharCode(64 + numericIndex)
          : ["A", "B", "C", "D", "E", "F", "G", "H", "I"].includes(key)
            ? key
            : null;

      if (!label || !activeQuestion.options_snapshot.some((option) => option.label === label)) {
        return;
      }

      event.preventDefault();
      if (activeQuestion.question_type === "multiple") {
        handleMultipleChange(
          activeQuestion,
          label,
          !splitAnswer(answers[activeQuestion.id]).includes(label),
        );
      } else {
        handleSingleChange(activeQuestion, label);
      }
    }
    window.addEventListener("keydown", handleKeydown);
    return () => window.removeEventListener("keydown", handleKeydown);
  }, [
    activeQuestion,
    answers,
    goNext,
    goPrev,
    handleMultipleChange,
    handleSingleChange,
    submitMutation.isPending,
  ]);

  if (!attemptId) {
    return (
      <PageShell density="focus" width="full" className="mx-auto max-w-3xl py-12">
        <div className="rounded-lg border border-hairline bg-surface-card p-8">
          <PageState
            state="notStarted"
            eyebrow={candidatePageCopy.notStarted}
            title="未开始考试。"
            description="请从考试列表进入并确认考试规则。"
            className="py-0"
          />
          <div className="mt-6 flex justify-center">
            <Button asChild>
              <Link to={`/exams/${examId}/start`}>返回考试说明</Link>
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

  if (hasAttemptLoadError) {
    return (
      <PageShell density="focus" width="full" className="mx-auto max-w-3xl py-12">
        <div className="rounded-lg border border-hairline bg-surface-card p-8">
          <PageState
            state="error"
            eyebrow={candidatePageCopy.error}
            title="考试加载失败。"
            description={getErrorMessage(attemptError, "请确认考试仍在开放时间内，并稍后重试。")}
            className="py-0"
          />
          <div className="mt-6 flex justify-center">
            <Button asChild>
              <Link to="/exams">返回考试列表</Link>
            </Button>
          </div>
        </div>
      </PageShell>
    );
  }

  if (!attempt) {
    return (
      <PageShell density="focus" width="full" className="mx-auto max-w-3xl py-12">
        <PageState
          state="error"
          eyebrow={candidatePageCopy.error}
          title="未找到考试记录。"
          description="请从考试列表重新进入考试。"
        />
      </PageShell>
    );
  }

  if (SUBMITTED_STATUSES.has(attempt.status)) {
    return (
      <PageShell density="focus" width="full" className="mx-auto max-w-3xl py-12">
        <div className="rounded-lg border border-hairline bg-surface-card p-8">
          <PageState
            state="submitted"
            eyebrow={candidatePageCopy.submitted}
            title="考试已交卷。"
            description="你可以前往结果页查看本次交卷记录。"
            className="py-0"
          />
          <div className="mt-6 flex justify-center">
            <Button asChild>
              <Link to={`/exams/${examId}/result?attemptId=${attempt.id}`}>查看成绩</Link>
            </Button>
          </div>
        </div>
      </PageShell>
    );
  }

  if (!activeQuestion) {
    return (
      <PageShell density="focus" width="full" className="mx-auto max-w-3xl py-12">
        <PageState
          state="empty"
          eyebrow={candidatePageCopy.empty}
          title="本次考试暂无题目。"
          description="请联系管理员检查考试题池配置。"
        />
      </PageShell>
    );
  }

  const questionType = activeQuestion.question_type as "single" | "multiple" | "judge";
  const isMultiple = questionType === "multiple";
  const selectedLabels = isMultiple ? splitAnswer(answers[activeQuestion.id]) : [];
  const singleValue = !isMultiple ? (answers[activeQuestion.id] ?? "") : "";
  const perTypeNumber = perTypeIndexOf(sortedQuestions, activeQuestion.id);
  const stemChapterLabel = formatQuestionEyebrow(
    perTypeNumber,
    getQuestionTypeLabel(activeQuestion.question_type),
    activeQuestion.score,
  );

  const options = activeQuestion.options_snapshot.map((option) => ({
    label: option.label,
    content: option.content,
    selected: isMultiple ? selectedLabels.includes(option.label) : singleValue === option.label,
    disabled: submitMutation.isPending,
  }));

  const handleSelectOption = (label: string) => {
    if (submitMutation.isPending || submitStartedRef.current) {
      return;
    }
    if (isMultiple) {
      handleMultipleChange(activeQuestion, label, !selectedLabels.includes(label));
    } else {
      handleSingleChange(activeQuestion, label);
    }
  };

  const jumpToQuestion = (id: number) => {
    const nextIndex = sortedQuestions.findIndex((question) => question.id === id);
    if (nextIndex >= 0) {
      setActiveIndex(nextIndex);
    }
  };
  const nextQuestionLabel = isLastQuestion
    ? submitMutation.isPending
      ? candidateActionCopy.submittingExam
      : candidateActionCopy.submitExam
    : "下一题";

  return (
    <PageShell density="focus" width="full" stagger className="relative min-h-[calc(100vh-10rem)]">
      <div
        className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-hairline bg-canvas px-4 py-3 text-body-sm shadow-card"
        aria-live="polite"
      >
        <span
          className={
            saveStatus === "error"
              ? "font-medium text-error"
              : saveStatus === "saved"
                ? "font-medium text-success"
                : "font-medium text-muted"
          }
        >
          {SAVE_STATUS_LABEL[saveStatus]}
        </span>
        <div className="flex flex-wrap items-center gap-3">
          {submitErrorVisible ? (
            <span className="text-error">
              {candidateActionCopy.submitFailed}，请先确认答案已保存并重试。
            </span>
          ) : null}
          {saveStatus === "error" ? (
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => void performFullSave()}
              disabled={submitMutation.isPending}
            >
              {candidateActionCopy.retrySave}
            </Button>
          ) : null}
        </div>
      </div>
      <div className="hidden flex-1 grid-cols-[1fr_240px] gap-8 lg:grid">
        <div id="exam-question-focus">
          <ExamFocusMode
            progress={{ current: activeIndex + 1, total, answered: answeredCount }}
            remainingSeconds={remainingSeconds}
            stem={{ chapterLabel: stemChapterLabel, title: activeQuestion.stem_snapshot }}
            options={options}
            selectionType={questionType}
            onSelectOption={handleSelectOption}
            nav={{
              onPrev: goPrev,
              onSave: handleSave,
              onNext: handleNextAction,
              prevDisabled: activeIndex === 0,
              nextDisabled: isLastQuestion && submitMutation.isPending,
              nextLabel: nextQuestionLabel,
              saving: saveStatus === "saving",
            }}
          />
        </div>
        <aside className="self-start lg:sticky lg:top-24 lg:z-30 lg:w-60">
          <ExamNavigator
            items={navItems}
            activeId={activeQuestion.id}
            desktopLayout
            onJump={(_targetId, id) => jumpToQuestion(id)}
            onSubmit={() => requestSubmit("manual")}
            submitLabel={
              submitMutation.isPending
                ? candidateActionCopy.submittingExam
                : candidateActionCopy.submitExam
            }
            submitDisabled={submitMutation.isPending}
          />
        </aside>
      </div>

      <div className="flex flex-1 flex-col pb-24 lg:hidden">
        <ExamFocusMode
          progress={{ current: activeIndex + 1, total, answered: answeredCount }}
          remainingSeconds={remainingSeconds}
          stem={{ chapterLabel: stemChapterLabel, title: activeQuestion.stem_snapshot }}
          options={options}
          selectionType={questionType}
          onSelectOption={handleSelectOption}
          nav={{
            onPrev: goPrev,
            onNext: handleNextAction,
            prevDisabled: activeIndex === 0,
            nextDisabled: isLastQuestion && submitMutation.isPending,
            nextLabel: nextQuestionLabel,
          }}
        />

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
              <SheetDescription className="sr-only">选择题号或交卷。</SheetDescription>
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
            <Button
              type="button"
              onClick={() => {
                setSheetOpen(false);
                requestSubmit("manual");
              }}
              disabled={submitMutation.isPending}
              className="w-full"
            >
              <Send data-icon="inline-start" />
              {submitMutation.isPending
                ? candidateActionCopy.submittingExam
                : candidateActionCopy.submitExam}
            </Button>
          </SheetContent>
        </Sheet>
      </div>

      {submitMutation.isError ? (
        <p className="sr-only" role="alert">
          {candidateActionCopy.submitFailed}，请确认考试仍在进行中。
        </p>
      ) : null}
    </PageShell>
  );
}
