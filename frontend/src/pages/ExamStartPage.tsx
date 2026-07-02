import { useMutation } from "@tanstack/react-query";
import { ArrowRight, ClipboardCheck } from "lucide-react";
import { Link, useNavigate, useOutletContext, useParams } from "react-router-dom";

import { startExam } from "@/api/exams";
import { ApiError } from "@/api/client";
import { NamePlate } from "@/components/editorial/NamePlate";
import type { CandidateSessionContext } from "@/components/layout/CandidateLayout";
import { PageHeader, PageSection, PageShell, PageState } from "@/components/page";
import { Button } from "@/components/ui/button";
import { candidatePageCopy, productTerms } from "@/lib/pageCopy";

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
  const mutation = useMutation({
    mutationFn: () => startExam(examId),
    onSuccess: (result) => {
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

  return (
    <PageShell density="calm" width="full" stagger className="mx-auto max-w-3xl">
      <PageHeader
        eyebrow={candidatePageCopy.examRules}
        title="确认考试规则"
        description="阅读下面的规则后再开始考试。开始后系统会立即生成题目快照并启动倒计时。"
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
          <NamePlate
            candidate={{
              name: candidate.name,
              employeeNo: candidate.employee_no ?? undefined,
              department: candidate.department ?? undefined,
            }}
          />
        </div>
      ) : null}

      <div className="flex flex-col gap-3">
        {candidate ? (
          <Button
            type="button"
            size="lg"
            disabled={mutation.isPending}
            onClick={() => mutation.mutate()}
            className="self-start"
          >
            <ClipboardCheck data-icon="inline-start" />
            {mutation.isPending ? "正在开始" : "开始考试"}
            <ArrowRight data-icon="inline-end" />
          </Button>
        ) : (
          <Button asChild size="lg" className="self-start">
            <Link to="/login">
              先登录{productTerms.examTaker}
              <ArrowRight data-icon="inline-end" />
            </Link>
          </Button>
        )}
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
