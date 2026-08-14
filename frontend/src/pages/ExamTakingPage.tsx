import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useBlocker, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { ApiError, getErrorMessage } from "@/api/client";
import { PageShell, PageState } from "@/components/page";
import { Button } from "@/components/ui/button";
import { ExamTakingWorkspace } from "@/features/exam/ExamTakingWorkspace";
import { useAttemptCountdown } from "@/features/exam/useAttemptCountdown";
import { useAttemptDraftQueue } from "@/features/exam/useAttemptDraftQueue";
import { useAttemptSession } from "@/features/exam/useAttemptSession";
import { useExamSubmission } from "@/features/exam/useExamSubmission";
import { clearCurrentCandidate, getCurrentCandidate } from "@/lib/candidateSession";
import { candidatePageCopy, formatQuestionEyebrow } from "@/lib/pageCopy";
import {
  buildQuestionNavItems,
  getQuestionTypeLabel,
  perTypeIndexOf,
  sortByType,
} from "@/lib/questionNavigation";
import { splitAnswer, toggleMultipleAnswer } from "@/lib/utils";
import type { AttemptQuestion } from "@/types/attempt";

const EMPTY_QUESTIONS: AttemptQuestion[] = [];
const SUBMITTED_STATUSES = new Set(["submitted", "auto_submitted"]);

export function ExamTakingPage() {
  const { examId = "1" } = useParams();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const attemptId = searchParams.get("attemptId");
  const takeoverRequested = searchParams.get("takeover") === "1";
  const candidateId = getCurrentCandidate()?.id ?? null;
  const [activeIndex, setActiveIndex] = useState(0);

  const {
    data: attempt,
    error: attemptError,
    isError: isAttemptError,
    isLoading,
    session,
    sessionConflict,
    invalidateSession,
    takeover,
    takeoverError,
    takeoverPending,
  } = useAttemptSession(candidateId, attemptId);
  const {
    answers,
    answersRef,
    saveStatus,
    hasUnsynchronizedWork,
    updateAnswers,
    performFullSave,
    cancelPendingSave,
    clearDraft,
  } = useAttemptDraftQueue(attempt, session);
  const submission = useExamSubmission({
    examId,
    attemptId,
    session,
    performFullSave,
    cancelPendingSave,
    clearDraft,
    invalidateSession,
  });
  const remainingSeconds = useAttemptCountdown(attempt);
  const [navigationBypass, setNavigationBypass] = useState(false);
  const navigationBypassRef = useRef(false);
  const [liveAnnouncement, setLiveAnnouncement] = useState<string | undefined>();
  const shouldGuardNavigation = Boolean(
    attempt?.status === "in_progress" && hasUnsynchronizedWork && !navigationBypass,
  );
  const shouldBlockNavigation = useCallback(
    () => shouldGuardNavigation && !navigationBypassRef.current,
    [shouldGuardNavigation],
  );
  const blocker = useBlocker(shouldBlockNavigation);

  useEffect(() => {
    if (!shouldGuardNavigation && blocker.state === "blocked") {
      blocker.reset();
    }
  }, [blocker, shouldGuardNavigation]);

  useEffect(() => {
    if (!shouldGuardNavigation) return;

    function handleBeforeUnload(event: BeforeUnloadEvent) {
      event.preventDefault();
      event.returnValue = "";
    }

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [shouldGuardNavigation]);

  useEffect(() => {
    if (
      takeoverRequested &&
      candidateId !== null &&
      attemptId &&
      !session &&
      !takeoverPending &&
      !takeoverError
    ) {
      takeover();
    }
  }, [
    attemptId,
    candidateId,
    session,
    takeover,
    takeoverError,
    takeoverPending,
    takeoverRequested,
  ]);

  useEffect(() => {
    if (!takeoverRequested || !session) return;
    const nextSearchParams = new URLSearchParams(searchParams);
    nextSearchParams.delete("takeover");
    setSearchParams(nextSearchParams, { replace: true });
  }, [searchParams, session, setSearchParams, takeoverRequested]);

  const sortedQuestions = useMemo<AttemptQuestion[]>(
    () => (attempt ? sortByType(attempt.questions) : EMPTY_QUESTIONS),
    [attempt],
  );
  const total = sortedQuestions.length;
  const activeQuestion = sortedQuestions[activeIndex];
  const isLastQuestion = total > 0 && activeIndex === total - 1;
  const hasAttemptLoadError = isAttemptError && !attempt;

  const answeredCount = useMemo(
    () => sortedQuestions.reduce((count, question) => count + (answers[question.id] ? 1 : 0), 0),
    [answers, sortedQuestions],
  );
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
      updateAnswers({ ...answersRef.current, [question.id]: label });
    },
    [answersRef, updateAnswers],
  );
  const handleMultipleChange = useCallback(
    (question: AttemptQuestion, label: string, checked: boolean) => {
      const next = toggleMultipleAnswer(answersRef.current[question.id], label, checked);
      updateAnswers({ ...answersRef.current, [question.id]: next });
    },
    [answersRef, updateAnswers],
  );

  const goPrev = useCallback(() => setActiveIndex((index) => Math.max(0, index - 1)), []);
  const goNext = useCallback(() => {
    setActiveIndex((index) => Math.min(sortedQuestions.length - 1, index + 1));
  }, [sortedQuestions.length]);
  const handleNextAction = useCallback(() => {
    if (isLastQuestion) submission.requestSubmit("manual");
    else goNext();
  }, [goNext, isLastQuestion, submission]);

  const beginFreshTakeover = useCallback(() => {
    const returnTo = `/exams/${examId}/taking?attemptId=${encodeURIComponent(attemptId ?? "")}&takeover=1`;
    navigationBypassRef.current = true;
    setNavigationBypass(true);
    clearCurrentCandidate();
    navigate(`/login?returnTo=${encodeURIComponent(returnTo)}`, { replace: true });
  }, [attemptId, examId, navigate]);

  useEffect(() => {
    function handleKeydown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const workspace = target?.closest<HTMLElement>("[data-exam-workspace]");
      if (
        !workspace ||
        event.defaultPrevented ||
        event.isComposing ||
        event.metaKey ||
        event.ctrlKey ||
        event.altKey ||
        event.shiftKey ||
        target?.isContentEditable ||
        target?.closest(
          "button, a, input, textarea, select, option, [role='button'], [role='dialog'], [role='alertdialog'], [data-exam-overlay], [data-radix-dialog-content], [data-radix-popper-content-wrapper]",
        )
      ) {
        return;
      }
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        goPrev();
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        goNext();
      }
      if (!activeQuestion || submission.isPending || submission.submitStartedRef.current) return;

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
    submission.isPending,
    submission.submitStartedRef,
  ]);

  const autoSubmittedRef = useRef(false);
  useEffect(() => {
    if (!attempt || remainingSeconds !== 0 || autoSubmittedRef.current || submission.isPending) {
      return;
    }
    autoSubmittedRef.current = true;
    setLiveAnnouncement("考试时间已到，正在自动交卷。");
    submission.requestSubmit("manual");
  }, [attempt, remainingSeconds, submission]);

  if (!attemptId) {
    return (
      <PageShell density="focus" width="full" className="mx-auto max-w-3xl py-12">
        <div className="rounded-lg border border-hairline bg-surface-card p-8">
          <PageState
            state="notStarted"
            eyebrow={candidatePageCopy.notStarted}
            title="未开始考试。"
            description="请从考试列表进入并阅读规则。"
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

  if (!session) {
    const takeoverMessage = takeoverError
      ? getErrorMessage(takeoverError, "考试会话接管失败，请重新完成验证码登录。")
      : sessionConflict
        ? "其他页面或设备已接管本次考试。重新核验后可继续，已保存答案和考试截止时间不会变化。"
        : "当前浏览器没有本次考试的有效设备会话。重新核验后可恢复已保存答案。";
    return (
      <PageShell density="focus" width="full" className="mx-auto max-w-3xl py-12">
        <div className="rounded-lg border border-hairline bg-surface-card p-8">
          {takeoverPending ? (
            <PageState state="loading" rows={3} className="py-0" />
          ) : (
            <PageState
              state="error"
              eyebrow="DEVICE SESSION · 设备会话"
              title="需要重新核验并接管考试。"
              description={takeoverMessage}
              className="py-0"
            />
          )}
          {!takeoverPending ? (
            <div className="mt-6 flex justify-center">
              <Button type="button" onClick={beginFreshTakeover}>
                重新验证码登录并接管
              </Button>
            </div>
          ) : null}
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
    const isDeviceConflict =
      attemptError instanceof ApiError &&
      attemptError.status === 409 &&
      attemptError.detail?.includes("考试会话已失效");
    return (
      <PageShell density="focus" width="full" className="mx-auto max-w-3xl py-12">
        <div className="rounded-lg border border-hairline bg-surface-card p-8">
          <PageState
            state="error"
            eyebrow={candidatePageCopy.error}
            title={isDeviceConflict ? "考试设备会话已失效。" : "考试加载失败。"}
            description={getErrorMessage(attemptError, "请确认考试仍在开放时间内，并稍后重试。")}
            className="py-0"
          />
          <div className="mt-6 flex justify-center">
            {isDeviceConflict ? (
              <Button type="button" onClick={beginFreshTakeover}>
                重新验证码登录并接管
              </Button>
            ) : (
              <Button asChild>
                <Link to="/exams">返回考试列表</Link>
              </Button>
            )}
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
  const stemChapterLabel = formatQuestionEyebrow(
    perTypeIndexOf(sortedQuestions, activeQuestion.id),
    getQuestionTypeLabel(activeQuestion.question_type),
    activeQuestion.score,
  );
  const options = activeQuestion.options_snapshot.map((option) => ({
    label: option.label,
    content: option.content,
    selected: isMultiple ? selectedLabels.includes(option.label) : singleValue === option.label,
    disabled: submission.isPending,
  }));

  return (
    <ExamTakingWorkspace
      activeIndex={activeIndex}
      total={total}
      answeredCount={answeredCount}
      activeQuestionAnswered={Boolean(answers[activeQuestion.id])}
      remainingSeconds={remainingSeconds}
      stemChapterLabel={stemChapterLabel}
      stemTitle={activeQuestion.stem_snapshot}
      options={options}
      selectionType={questionType}
      navItems={navItems}
      activeQuestionId={activeQuestion.id}
      isLastQuestion={isLastQuestion}
      saveStatus={saveStatus}
      hasUnsynchronizedWork={hasUnsynchronizedWork}
      submitPending={submission.isPending}
      submitErrorVisible={submission.isError}
      onSelectOption={(label) => {
        if (submission.isPending || submission.submitStartedRef.current) return;
        if (isMultiple) {
          handleMultipleChange(activeQuestion, label, !selectedLabels.includes(label));
        } else {
          handleSingleChange(activeQuestion, label);
        }
      }}
      onPrev={goPrev}
      onSave={() => {
        cancelPendingSave();
        void performFullSave();
      }}
      onNext={handleNextAction}
      onJump={(id) => {
        const nextIndex = sortedQuestions.findIndex((question) => question.id === id);
        if (nextIndex >= 0) setActiveIndex(nextIndex);
      }}
      onSubmit={() => submission.requestSubmit("manual")}
      onRetrySave={() => void performFullSave()}
      onResolveConflict={beginFreshTakeover}
      navigationWarning={
        blocker.state === "blocked" ? { onStay: blocker.reset, onLeave: blocker.proceed } : null
      }
      liveAnnouncement={liveAnnouncement}
    />
  );
}
