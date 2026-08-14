import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowRight, ClipboardCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate, useOutletContext, useParams } from "react-router-dom";

import { getActiveExams, startExam } from "@/api/exams";
import { ApiError } from "@/api/client";
import { NamePlate } from "@/components/editorial/NamePlate";
import type { CandidateSessionContext } from "@/components/layout/CandidateLayout";
import { PageHeader, PageSection, PageShell, PageStaleNotice, PageState } from "@/components/page";
import { Button } from "@/components/ui/button";
import { candidatePageCopy, candidatePageText, productTerms } from "@/lib/pageCopy";
import { setAttemptSession } from "@/lib/attemptSession";
import { candidateDisplayName } from "@/types/candidate";

const RULES: { text: string }[] = [
  { text: "考试中答案会自动保存，但倒计时不会暂停。" },
  { text: "可以主动交卷，到时间系统会自动交卷。" },
  { text: "交卷后自动判分，并按配置展示答案与解析。" },
  { text: "系统会在开始时生成题目快照，后续题库修改不影响本次结果。" },
];

const IN_PROGRESS_PATTERN = /#(\d+)/;
const SUBMITTED_CONFLICT_PATTERN = /已交卷|已提交/;

export function ExamStartPage() {
  const { examId = "1" } = useParams();
  const navigate = useNavigate();
  const { candidate } = useOutletContext<CandidateSessionContext>();
  const examQuery = useQuery({
    queryKey: ["candidate", candidate?.id ?? "anonymous", "active-exams"],
    queryFn: getActiveExams,
    enabled: Boolean(candidate),
    retry: false,
  });
  const exam = examQuery.data?.find((item) => String(item.id) === examId);
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const intervalId = window.setInterval(() => setNow(Date.now()), 1_000);
    return () => window.clearInterval(intervalId);
  }, []);
  const availableFrom = exam?.available_from ? Date.parse(exam.available_from) : null;
  const availableUntil = exam?.available_until ? Date.parse(exam.available_until) : null;
  const beforeOpen =
    Boolean(availableFrom && Number.isFinite(availableFrom) && now < availableFrom) ||
    exam?.availability_status === "not_started";
  const afterClose =
    Boolean(availableUntil && Number.isFinite(availableUntil) && now > availableUntil) ||
    exam?.availability_status === "ended";
  const canStart = Boolean(exam && !beforeOpen && !afterClose);
  const mutation = useMutation({
    mutationFn: () => startExam(examId),
    onSuccess: (result) => {
      if (candidate && result.attempt_session_credential) {
        setAttemptSession({
          candidateId: candidate.id,
          attemptId: result.attempt_id,
          credential: result.attempt_session_credential,
          generation: result.attempt_session_generation,
          answerRevision: result.answer_revision,
        });
      }
      navigate(`/exams/${examId}/taking?attemptId=${result.attempt_id}`);
    },
  });

  const apiError = mutation.error instanceof ApiError ? mutation.error : null;
  const errorMessage = apiError?.message ?? mutation.error?.message ?? "请稍后重试或联系管理员。";
  const isInProgressConflict = apiError?.detail?.includes("进行中") ?? false;
  const submittedAttemptId =
    apiError?.status === 409 && SUBMITTED_CONFLICT_PATTERN.test(apiError.detail ?? "")
      ? Number(apiError.detail?.match(IN_PROGRESS_PATTERN)?.[1] ?? 0) || null
      : null;
  const existingAttemptId =
    apiError?.status === 409 && isInProgressConflict
      ? Number(apiError.detail?.match(IN_PROGRESS_PATTERN)?.[1] ?? 0) || null
      : null;

  if (candidate && examQuery.isLoading) {
    return <PageState state="loading" rows={2} />;
  }
  const hasLoadError = examQuery.isError && !examQuery.data;
  const hasStaleError = examQuery.isError && Boolean(examQuery.data);

  if (candidate && (hasLoadError || !exam)) {
    return (
      <PageShell density="calm" width="full" stagger className="mx-auto max-w-3xl">
        <PageState
          state="error"
          eyebrow={candidatePageCopy.error}
          title="考试说明加载失败。"
          description="受邀考试暂不可用，请返回受邀考试列表重试。"
          action={{ label: "返回受邀考试", onClick: () => navigate("/exams") }}
          secondaryAction={
            hasLoadError ? { label: "重试", onClick: () => void examQuery.refetch() } : undefined
          }
        />
      </PageShell>
    );
  }

  return (
    <PageShell density="calm" width="full" stagger className="mx-auto max-w-3xl">
      {hasStaleError ? (
        <PageStaleNotice
          lastSuccessfulAt={examQuery.dataUpdatedAt}
          onRetry={() => examQuery.refetch()}
          retrying={examQuery.isFetching}
        />
      ) : null}
      <PageHeader
        eyebrow={candidatePageCopy.examRules}
        title={candidatePageText.examRules.title}
        description={candidatePageText.examRules.description}
      />

      <PageSection variant="panel" className="p-6 lg:p-8">
        <ol className="flex flex-col gap-3 text-body italic text-ink">
          {RULES.map((rule, index) => (
            <li key={rule.text} className="flex gap-3">
              <span className="font-mono text-caption uppercase tracking-[0.16em] text-muted">
                {String(index + 1).padStart(2, "0")}
              </span>
              <span>{rule.text}</span>
            </li>
          ))}
        </ol>
      </PageSection>

      {candidate ? (
        <div className="flex flex-col gap-3 rounded-lg border border-hairline bg-canvas p-5">
          <p className="text-caption uppercase tracking-[0.16em] text-muted">
            当前{productTerms.examTaker}
          </p>
          <NamePlate name={candidateDisplayName(candidate)} subtitle="应考人员" />
        </div>
      ) : null}

      <div className="flex flex-col gap-3">
        {candidate ? (
          <Button
            type="button"
            size="lg"
            disabled={mutation.isPending || !canStart}
            onClick={() => mutation.mutate()}
            className="self-start"
          >
            <ClipboardCheck data-icon="inline-start" />
            {mutation.isPending
              ? "正在开始"
              : beforeOpen
                ? "尚未开放"
                : afterClose
                  ? "开放已结束"
                  : "开始考试"}
            <ArrowRight data-icon="inline-end" />
          </Button>
        ) : (
          <Button asChild size="lg" className="self-start">
            <Link to={`/login?returnTo=${encodeURIComponent(`/exams/${examId}/start`)}`}>
              先登录
              <ArrowRight data-icon="inline-end" />
            </Link>
          </Button>
        )}
        {candidate && beforeOpen ? (
          <p className="text-body-sm text-muted" role="status">
            应考人员可在{" "}
            {exam?.available_from ? new Date(exam.available_from).toLocaleString() : "开放时间"}{" "}
            开始考试。
          </p>
        ) : null}
        {mutation.isError ? (
          <PageState
            state="error"
            eyebrow={candidatePageCopy.error}
            title="开始考试失败。"
            description={errorMessage}
            action={
              existingAttemptId
                ? {
                    label: "继续考试",
                    onClick: () =>
                      navigate(`/exams/${examId}/taking?attemptId=${existingAttemptId}`),
                  }
                : submittedAttemptId
                  ? {
                      label: "查看成绩",
                      onClick: () =>
                        navigate(`/exams/${examId}/result?attemptId=${submittedAttemptId}`),
                    }
                  : undefined
            }
            secondaryAction={{ label: "重试", onClick: () => mutation.reset() }}
            className="items-start py-4 text-left"
            role="alert"
          />
        ) : null}
      </div>
    </PageShell>
  );
}
