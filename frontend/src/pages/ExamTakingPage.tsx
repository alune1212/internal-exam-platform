import { useMutation, useQuery } from "@tanstack/react-query";
import { Clock, Save, Send } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { getAttempt, saveAttemptAnswers, submitAttempt } from "@/api/attempts";
import { getActiveExams } from "@/api/exams";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { splitAnswer, toggleMultipleAnswer } from "@/lib/utils";
import type { AttemptQuestion } from "@/types/attempt";

export function ExamTakingPage() {
  const { examId = "1" } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const attemptId = searchParams.get("attemptId");
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [now, setNow] = useState(() => Date.now());
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
    mutationFn: async () => {
      if (!attempt) {
        return null;
      }
      const items = attempt.questions.map((question) => ({
        attempt_question_id: question.id,
        selected_answer: answers[question.id] ?? "",
      }));
      await saveAttemptAnswers(String(attempt.id), items);
      return submitAttempt(String(attempt.id), "manual");
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
  const remainingText = useMemo(() => {
    if (!attempt || !durationMinutes) {
      return "--:--";
    }
    const endsAt = new Date(attempt.started_at).getTime() + durationMinutes * 60 * 1000;
    const remainingSeconds = Math.max(0, Math.floor((endsAt - now) / 1000));
    const minutes = Math.floor(remainingSeconds / 60);
    const seconds = remainingSeconds % 60;
    return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  }, [attempt, durationMinutes, now]);

  function handleAnswerChange(question: AttemptQuestion, value: string) {
    setAnswers((current) => ({ ...current, [question.id]: value }));
    saveMutation.mutate([{ attempt_question_id: question.id, selected_answer: value }]);
  }

  function handleMultipleChange(question: AttemptQuestion, label: string, checked: boolean) {
    handleAnswerChange(question, toggleMultipleAnswer(answers[question.id], label, checked));
  }

  function handleSaveAll() {
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

  if (!attemptId) {
    return (
      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>未开始考试</CardTitle>
        </CardHeader>
        <CardContent>
          <Button asChild>
            <Link to={`/exams/${examId}/start`}>返回考试说明</Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_280px]">
      <Card>
        <CardHeader>
          <CardTitle>答题区</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {isLoading ? <p className="text-sm text-muted-foreground">正在加载题目</p> : null}
          {attempt?.questions.map((question, index) => (
            <div key={question.id} className="rounded-md border p-4">
              <p className="mb-3 font-medium">
                {index + 1}. {question.stem_snapshot}
              </p>
              <div className="grid gap-2">
                {question.options_snapshot.map((option) => {
                  const isMultiple = question.question_type === "multiple";
                  const checked = isMultiple
                    ? splitAnswer(answers[question.id]).includes(option.label)
                    : answers[question.id] === option.label;
                  return (
                    <label
                      key={option.label}
                      className="flex items-center gap-2 rounded-md border p-3 text-sm"
                    >
                      <input
                        type={isMultiple ? "checkbox" : "radio"}
                        name={`question-${question.id}`}
                        checked={checked}
                        onChange={(event) =>
                          isMultiple
                            ? handleMultipleChange(question, option.label, event.target.checked)
                            : handleAnswerChange(question, option.label)
                        }
                      />
                      <span>
                        {option.label}. {option.content}
                      </span>
                    </label>
                  );
                })}
              </div>
            </div>
          ))}
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="outline"
              disabled={!attempt || saveMutation.isPending}
              onClick={handleSaveAll}
            >
              <Save data-icon="inline-start" />
              {saveMutation.isPending ? "正在暂存" : "暂存答案"}
            </Button>
            <Button
              type="button"
              disabled={!attempt || submitMutation.isPending}
              onClick={() => submitMutation.mutate()}
            >
              <Send data-icon="inline-start" />
              {submitMutation.isPending ? "正在交卷" : "提前交卷"}
            </Button>
          </div>
          {saveMutation.isError ? (
            <p className="text-sm text-destructive">暂存失败，请稍后重试。</p>
          ) : null}
          {submitMutation.isError ? (
            <p className="text-sm text-destructive">交卷失败，请确认考试仍在进行中。</p>
          ) : null}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock data-icon="inline-start" />
            倒计时
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-3xl font-semibold">{remainingText}</p>
          <p className="mt-2 text-sm text-muted-foreground">
            暂存不会暂停倒计时，到时间后自动提交。
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
