import { useMutation, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link, useOutletContext } from "react-router-dom";

import { getPracticeQuestions, submitPracticeAnswer } from "@/api/questions";
import {
  buildQuestionNavItems,
  getQuestionTypeLabel,
  QuestionNavigator,
} from "@/components/QuestionNavigator";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { CandidateSessionContext } from "@/components/layout/CandidateLayout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn, splitAnswer, toggleMultipleAnswer } from "@/lib/utils";
import type { PracticeAnswerResult, Question } from "@/types/question";

export function PracticePage() {
  const { candidate } = useOutletContext<CandidateSessionContext>();
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [results, setResults] = useState<Record<number, PracticeAnswerResult>>({});
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
  const [activeQuestionId, setActiveQuestionId] = useState<number | null>(null);
  const navItems = useMemo(
    () =>
      buildQuestionNavItems({
        questions: data,
        answers,
        getSubmittedResult: (question) => {
          const result = results[question.id];
          return result ? (result.is_correct ? "correct" : "wrong") : undefined;
        },
        getTargetId: (question) => `practice-question-${question.id}`,
      }),
    [answers, data, results],
  );

  function handleJump(targetId: string, itemId: number) {
    setActiveQuestionId(itemId);
    document.getElementById(targetId)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function handleSingleChange(questionId: number, label: string) {
    setAnswers((current) => ({ ...current, [questionId]: label }));
  }

  function handleMultipleChange(questionId: number, label: string, checked: boolean) {
    setAnswers((current) => ({
      ...current,
      [questionId]: toggleMultipleAnswer(current[questionId], label, checked),
    }));
  }

  function handleSubmit(question: Question) {
    if (!candidate) {
      return;
    }
    mutation.mutate({
      candidate_id: candidate.id,
      question_id: question.id,
      selected_answer: answers[question.id] ?? "",
    });
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-2xl font-semibold">练习模式</h2>
        <p className="text-muted-foreground">刷全部 active 题目，练习结果不计入正式成绩。</p>
      </div>
      {!candidate ? (
        <Card>
          <CardHeader>
            <CardTitle>请先登录考试人</CardTitle>
            <CardDescription>登录后可提交练习答案并记录练习结果。</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild>
              <Link to="/login">去登录</Link>
            </Button>
          </CardContent>
        </Card>
      ) : null}
      <div className="grid gap-4 lg:grid-cols-[1fr_300px]">
        <div className="flex flex-col gap-4">
          <div className="lg:hidden">
            <QuestionNavigator items={navItems} activeId={activeQuestionId} onJump={handleJump} />
          </div>
          <Card>
            <CardHeader>
              <CardTitle>题目列表</CardTitle>
              <CardDescription>
                {isLoading ? "正在加载题目" : `当前 ${data.length} 道题`}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              {data.length ? (
                data.map((question, index) => {
                  const result = results[question.id];
                  return (
                    <div
                      key={question.id}
                      id={`practice-question-${question.id}`}
                      className={cn(
                        "scroll-mt-24 rounded-md border p-4",
                        activeQuestionId === question.id && "ring-2 ring-ring ring-offset-2",
                      )}
                    >
                      <div className="mb-2 flex items-center gap-2">
                        <Badge variant="outline">
                          {getQuestionTypeLabel(question.question_type)}
                        </Badge>
                        <span className="text-sm text-muted-foreground">{question.score} 分</span>
                      </div>
                      <p className="font-medium">
                        {index + 1}. {question.stem}
                      </p>
                      <div className="mt-3 grid gap-2">
                        {question.options.map((option) => {
                          const isMultiple = question.question_type === "multiple";
                          const checked = isMultiple
                            ? splitAnswer(answers[question.id]).includes(option.label)
                            : answers[question.id] === option.label;
                          return (
                            <label
                              key={option.id}
                              className="flex items-center gap-2 rounded-md border p-3 text-sm"
                            >
                              <input
                                type={isMultiple ? "checkbox" : "radio"}
                                name={`practice-question-${question.id}`}
                                checked={checked}
                                onChange={(event) =>
                                  isMultiple
                                    ? handleMultipleChange(
                                        question.id,
                                        option.label,
                                        event.target.checked,
                                      )
                                    : handleSingleChange(question.id, option.label)
                                }
                              />
                              <span>
                                {option.label}. {option.content}
                              </span>
                            </label>
                          );
                        })}
                      </div>
                      <div className="mt-3 flex flex-wrap items-center gap-3">
                        <Button
                          type="button"
                          variant="outline"
                          disabled={!candidate || !answers[question.id] || mutation.isPending}
                          onClick={() => handleSubmit(question)}
                        >
                          提交本题
                        </Button>
                        {result ? (
                          <span
                            className={
                              result.is_correct
                                ? `text-sm text-emerald-700`
                                : `text-sm text-destructive`
                            }
                          >
                            {result.is_correct ? "回答正确" : "回答错误"}，正确答案：
                            {result.correct_answer}
                          </span>
                        ) : (
                          <span className="text-sm text-muted-foreground">
                            提交后显示正确答案和解析。
                          </span>
                        )}
                      </div>
                      {result?.analysis ? (
                        <p className="mt-2 text-sm text-muted-foreground">
                          解析：{result.analysis}
                        </p>
                      ) : null}
                    </div>
                  );
                })
              ) : (
                <p className="text-sm text-muted-foreground">
                  暂无题目，管理员导入题库后会显示在这里。
                </p>
              )}
            </CardContent>
          </Card>
        </div>
        <aside className="hidden lg:block">
          <div className="sticky top-4">
            <QuestionNavigator items={navItems} activeId={activeQuestionId} onJump={handleJump} />
          </div>
        </aside>
      </div>
    </div>
  );
}
