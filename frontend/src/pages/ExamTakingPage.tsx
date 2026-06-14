import { useMutation, useQuery } from "@tanstack/react-query";
import { List, LogOut, Send } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { getAttempt, saveAttemptAnswers, submitAttempt } from "@/api/attempts";
import { getActiveExams } from "@/api/exams";
import { ExamFocusMode } from "@/components/exam/ExamFocusMode";
import { ExamNavigator } from "@/components/exam/ExamNavigator";
import { ProgressCapsule } from "@/components/exam/ProgressCapsule";
import { Timer } from "@/components/exam/Timer";
import { ChapterNumber } from "@/components/editorial/ChapterNumber";
import { Wordmark } from "@/components/editorial/Wordmark";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { buildQuestionNavItems, getQuestionTypeLabel } from "@/lib/questionNavigation";
import { cn, splitAnswer, toggleMultipleAnswer } from "@/lib/utils";
import type { AttemptQuestion } from "@/types/attempt";

type AnswerMap = Record<number, string>;

export function ExamTakingPage() {
  const { examId = "1" } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const attemptId = searchParams.get("attemptId");

  const [answers, setAnswers] = useState<AnswerMap>({});
  const [now, setNow] = useState(() => Date.now());
  const [activeIndex, setActiveIndex] = useState(0);
  const [sheetOpen, setSheetOpen] = useState(false);

  const { data: attempt, isLoading } = useQuery({
    queryKey: ["attempt", attemptId],
    queryFn: () => getAttempt(attemptId ?? ""),
    enabled: Boolean(attemptId),
  });

  const { data: exams = [] } = useQuery({ queryKey: ["active-exams"], queryFn: getActiveExams });

  const saveMutation = useMutation({
    mutationFn: (items: Array<{ attempt_question_id: number; selected_answer: string }>) =>
      saveAttemptAnswers(attemptId ?? "", items),
  });

  const submitMutation = useMutation({
    mutationFn: async (submitType: "manual" | "auto" = "manual") => {
      if (!attempt) {
        return null;
      }
      const items = attempt.questions.map((question) => ({
        attempt_question_id: question.id,
        selected_answer: answers[question.id] ?? "",
      }));
      await saveAttemptAnswers(String(attempt.id), items);
      return submitAttempt(String(attempt.id), submitType);
    },
    onSuccess: (result) => {
      if (result) {
        navigate(`/exams/${examId}/result?attemptId=${result.attempt_id}`);
      }
    },
  });

  useEffect(() => {
    if (!attempt) {
      return;
    }
    setAnswers(
      Object.fromEntries(
        attempt.questions.map((question) => [question.id, question.selected_answer ?? ""]),
      ),
    );
  }, [attempt]);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const durationMinutes = exams.find((exam) => String(exam.id) === examId)?.duration_minutes;

  const remainingSeconds = useMemo(() => {
    if (!attempt || !durationMinutes) {
      return Number.POSITIVE_INFINITY;
    }
    const endsAt = new Date(attempt.started_at).getTime() + durationMinutes * 60 * 1000;
    return Math.max(0, Math.floor((endsAt - now) / 1000));
  }, [attempt, durationMinutes, now]);

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
    submitMutation.mutate("auto");
  }, [attempt, remainingSeconds, submitMutation]);

  const total = attempt?.questions.length ?? 0;
  const activeQuestion: AttemptQuestion | undefined = attempt?.questions[activeIndex];

  const answeredCount = useMemo(() => {
    if (!attempt) {
      return 0;
    }
    return attempt.questions.reduce((count, question) => count + (answers[question.id] ? 1 : 0), 0);
  }, [answers, attempt]);

  const navItems = useMemo(
    () =>
      buildQuestionNavItems({
        questions: attempt?.questions ?? [],
        answers,
        getTargetId: () => "exam-question-focus",
      }),
    [answers, attempt?.questions],
  );

  function handleSingleChange(question: AttemptQuestion, label: string) {
    setAnswers((current) => ({ ...current, [question.id]: label }));
    saveMutation.mutate([{ attempt_question_id: question.id, selected_answer: label }]);
  }

  function handleMultipleChange(question: AttemptQuestion, label: string, checked: boolean) {
    const next = toggleMultipleAnswer(answers[question.id], label, checked);
    setAnswers((current) => ({ ...current, [question.id]: next }));
    saveMutation.mutate([{ attempt_question_id: question.id, selected_answer: next }]);
  }

  function handleSave() {
    if (!attempt) {
      return;
    }
    saveMutation.mutate(
      attempt.questions.map((question) => ({
        attempt_question_id: question.id,
        selected_answer: answers[question.id] ?? "",
      })),
    );
  }

  const goPrev = useCallback(() => {
    setActiveIndex((index) => Math.max(0, index - 1));
  }, []);

  const goNext = useCallback(() => {
    if (!attempt) {
      return;
    }
    setActiveIndex((index) => Math.min(attempt.questions.length - 1, index + 1));
  }, [attempt]);

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

  if (!attemptId) {
    return (
      <div className="mx-auto max-w-3xl py-12">
        <Card className="bg-surface-card">
          <CardContent className="flex flex-col gap-4 p-8">
            <ChapterNumber>CHAPTER 00 · NOT STARTED</ChapterNumber>
            <h1 className="font-display text-display-lg font-semibold italic text-ink">
              未开始考试。
            </h1>
            <Button asChild>
              <Link to={`/exams/${examId}/start`}>返回考试说明</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (isLoading || !attempt || !activeQuestion) {
    return (
      <div className="mx-auto max-w-3xl py-12">
        <Card className="bg-surface-card">
          <CardContent className="p-8">
            <p className="text-body text-muted">正在加载题目</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const isMultiple = activeQuestion.question_type === "multiple";
  const selectedLabels = isMultiple ? splitAnswer(answers[activeQuestion.id]) : [];
  const singleValue = !isMultiple ? (answers[activeQuestion.id] ?? "") : "";
  const stemChapterLabel = `CHAPTER ${String(activeIndex + 1).padStart(2, "0")} · ${getQuestionTypeLabel(
    activeQuestion.question_type,
  )} · ${activeQuestion.score} 分`;

  const options = activeQuestion.options_snapshot.map((option) => ({
    label: option.label,
    content: option.content,
    selected: isMultiple ? selectedLabels.includes(option.label) : singleValue === option.label,
  }));

  const handleSelectOption = (label: string) => {
    if (isMultiple) {
      handleMultipleChange(activeQuestion, label, !selectedLabels.includes(label));
    } else {
      handleSingleChange(activeQuestion, label);
    }
  };

  const jumpToQuestion = (id: number) => {
    const nextIndex = attempt.questions.findIndex((question) => question.id === id);
    if (nextIndex >= 0) {
      setActiveIndex(nextIndex);
    }
  };

  return (
    <div className="flex min-h-[calc(100vh-10rem)] flex-col gap-6">
      <header className="sticky top-0 z-30 -mx-4 border-b border-hairline-soft bg-canvas px-4 py-3 md:-mx-8 md:px-8">
        <div className="flex items-center justify-between gap-4">
          <Wordmark subtitle={`— ${attempt.questions.length} 题`} />
          <div className="hidden items-center gap-3 md:flex">
            <ProgressCapsule current={activeIndex + 1} total={total} answered={answeredCount} />
            <Timer remainingSeconds={remainingSeconds} />
          </div>
          <Button asChild variant="ghost" size="icon" aria-label="退出考试">
            <Link to="/exams">
              <LogOut />
            </Link>
          </Button>
        </div>
      </header>

      <div className="hidden flex-1 grid-cols-[1fr_240px] gap-8 lg:grid">
        <div id="exam-question-focus">
          <ExamFocusMode
            progress={{ current: activeIndex + 1, total, answered: answeredCount }}
            remainingSeconds={remainingSeconds}
            stem={{ chapterLabel: stemChapterLabel, title: activeQuestion.stem_snapshot }}
            options={options}
            onSelectOption={handleSelectOption}
            nav={{
              onPrev: goPrev,
              onSave: handleSave,
              onNext: goNext,
              prevDisabled: activeIndex === 0,
              nextDisabled: activeIndex === total - 1,
              saving: saveMutation.isPending,
            }}
          />
        </div>
        <aside className="sticky top-24 self-start">
          <ExamNavigator
            items={navItems}
            activeId={activeQuestion.id}
            desktopLayout
            onJump={(_targetId, id) => jumpToQuestion(id)}
            onSubmit={() => submitMutation.mutate("manual")}
            submitLabel={submitMutation.isPending ? "正在交卷" : "提前交卷"}
          />
        </aside>
      </div>

      <div className="flex flex-1 flex-col pb-24 lg:hidden">
        <ExamFocusMode
          progress={{ current: activeIndex + 1, total, answered: answeredCount }}
          remainingSeconds={remainingSeconds}
          stem={{ chapterLabel: stemChapterLabel, title: activeQuestion.stem_snapshot }}
          options={options}
          onSelectOption={handleSelectOption}
          nav={{
            onPrev: goPrev,
            onNext: goNext,
            prevDisabled: activeIndex === 0,
            nextDisabled: activeIndex === total - 1,
          }}
        />

        <div className="fixed inset-x-0 bottom-3 z-40 flex justify-center px-3">
          <div className="flex w-full max-w-md items-center gap-2 rounded-pill border border-footer bg-footer p-2 shadow-elevate">
            <ProgressCapsule
              current={activeIndex + 1}
              total={total}
              answered={answeredCount}
              variant="dark"
              className="flex-1"
            />
            <button
              type="button"
              aria-label="打开题号导航"
              onClick={() => setSheetOpen(true)}
              className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-pill text-canvas"
            >
              <List />
            </button>
          </div>
        </div>
      </div>

      {sheetOpen
        ? createPortal(
            <MobileNavigatorSheet
              items={navItems}
              activeId={activeQuestion.id}
              onJump={(id) => {
                jumpToQuestion(id);
                setSheetOpen(false);
              }}
              onSubmit={() => {
                setSheetOpen(false);
                submitMutation.mutate("manual");
              }}
              submitting={submitMutation.isPending}
              onClose={() => setSheetOpen(false)}
            />,
            document.body,
          )
        : null}

      {saveMutation.isError ? (
        <p className="sr-only" role="alert">
          暂存失败，请稍后重试。
        </p>
      ) : null}
      {submitMutation.isError ? (
        <p className="sr-only" role="alert">
          交卷失败，请确认考试仍在进行中。
        </p>
      ) : null}
    </div>
  );
}

function MobileNavigatorSheet({
  items,
  activeId,
  onJump,
  onSubmit,
  submitting,
  onClose,
}: {
  items: ReturnType<typeof buildQuestionNavItems>;
  activeId: number;
  onJump: (id: number) => void;
  onSubmit: () => void;
  submitting: boolean;
  onClose: () => void;
}) {
  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, []);

  return (
    <div
      className="fixed inset-0 z-50 flex items-end bg-ink"
      style={{ backgroundColor: "color-mix(in srgb, var(--ink) 40%, transparent)" }}
      role="dialog"
      aria-modal="true"
      aria-label="题号导航"
      onClick={onClose}
    >
      <div
        className={cn(
          "flex h-[80vh] w-full flex-col gap-4 rounded-t-lg bg-canvas p-5 shadow-elevate",
        )}
        onClick={(event) => event.stopPropagation()}
      >
        <header className="flex items-center justify-between border-b border-hairline pb-3">
          <span className="font-display text-display-sm font-semibold text-ink">题号导航</span>
          <Button type="button" variant="ghost" size="sm" onClick={onClose} aria-label="关闭">
            关闭
          </Button>
        </header>
        <div className="flex-1 overflow-y-auto overscroll-contain">
          <ExamNavigator
            items={items}
            activeId={activeId}
            sheetLayout
            desktopLayout={false}
            onJump={(_targetId, id) => onJump(id)}
          />
        </div>
        <Button type="button" onClick={onSubmit} disabled={submitting} className="w-full">
          <Send data-icon="inline-start" />
          {submitting ? "正在交卷" : "提前交卷"}
        </Button>
      </div>
    </div>
  );
}
