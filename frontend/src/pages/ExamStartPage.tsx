import { useMutation } from "@tanstack/react-query";
import { ArrowRight, ClipboardCheck } from "lucide-react";
import { Link, useNavigate, useOutletContext, useParams } from "react-router-dom";

import { startExam } from "@/api/exams";
import { ApiError } from "@/api/client";
import { ChapterNumber } from "@/components/editorial/ChapterNumber";
import { EmptyState } from "@/components/editorial/EmptyState";
import { NamePlate } from "@/components/editorial/NamePlate";
import type { CandidateSessionContext } from "@/components/layout/CandidateLayout";
import { Button } from "@/components/ui/button";

const RULES: { text: string }[] = [
  { text: "考试中答案会自动暂存，但倒计时不会暂停。" },
  { text: "可以提前交卷，到时间系统会自动提交。" },
  { text: "提交后自动判分，并按配置展示答案与排名。" },
  { text: "系统会在开始时生成题目快照，后续题库修改不影响本次结果。" },
];

const IN_PROGRESS_PATTERN = /#(\d+)/;

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
  const existingAttemptId =
    apiError?.status === 409
      ? Number(apiError.detail?.match(IN_PROGRESS_PATTERN)?.[1] ?? 0) || null
      : null;

  return (
    <div data-stagger className="mx-auto flex max-w-3xl flex-col gap-8">
      <header className="flex flex-col gap-3">
        <ChapterNumber>CHAPTER 02 · EXAMS</ChapterNumber>
        <h1 className="font-display text-display-lg font-semibold text-ink lg:text-display-xl">
          规则已阅，<em className="italic">开始倒计时</em>。
        </h1>
        <p className="text-body text-body-lg">
          仔细阅读下面的规则，然后开始倒计时。开始后系统会立即生成题目快照。
        </p>
      </header>

      <section className="rounded-lg border border-hairline bg-surface-card p-6 lg:p-8">
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
      </section>

      {candidate ? (
        <div className="flex flex-col gap-3 rounded-lg border border-hairline bg-canvas p-5">
          <p className="text-caption uppercase tracking-[0.16em] text-muted">当前考试人</p>
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
            {mutation.isPending ? "正在开始..." : "开始考试"}
            <ArrowRight data-icon="inline-end" />
          </Button>
        ) : (
          <Button asChild size="lg" className="self-start">
            <Link to="/login">
              先登录考试人
              <ArrowRight data-icon="inline-end" />
            </Link>
          </Button>
        )}
        {mutation.isError ? (
          <EmptyState
            tone="error"
            chapter="CHAPTER 99 · OOPS"
            title="开始考试失败。"
            description={errorMessage}
            action={
              existingAttemptId
                ? {
                    label: "继续考试",
                    onClick: () =>
                      navigate(`/exams/${examId}/taking?attemptId=${existingAttemptId}`),
                  }
                : undefined
            }
            secondaryAction={{ label: "重试", onClick: () => mutation.reset() }}
            className="items-start py-4 text-left"
            role="alert"
          />
        ) : null}
      </div>
    </div>
  );
}
