export type QuestionNavItem = {
  id: number;
  /** 1-based index within the question's own type group (单选 01, 多选 01, ...). */
  displayIndex: number;
  type: string;
  answered: boolean;
  submittedResult?: "correct" | "wrong";
  targetId: string;
};

type BuildQuestionNavItemsParams<TQuestion extends { id: number; question_type: string }> = {
  questions: TQuestion[];
  answers: Record<number, string>;
  getSubmittedResult?: (question: TQuestion) => QuestionNavItem["submittedResult"];
  getTargetId: (question: TQuestion) => string;
};

export function getQuestionTypeLabel(questionType: string): string {
  const labels: Record<string, string> = {
    single: "单选",
    multiple: "多选",
    judge: "判断",
  };
  return labels[questionType] ?? questionType;
}

export function buildQuestionNavItems<TQuestion extends { id: number; question_type: string }>({
  questions,
  answers,
  getSubmittedResult,
  getTargetId,
}: BuildQuestionNavItemsParams<TQuestion>): QuestionNavItem[] {
  // Per-type counter: ensures navigator shows 单选 01-15, 多选 01-40, 判断 01-05
  // (Chinese-exam convention) instead of inheriting the underlying question
  // pool's natural ordering which interleaves types.
  const typeCounts = new Map<string, number>();
  return questions.map((question) => {
    const next = (typeCounts.get(question.question_type) ?? 0) + 1;
    typeCounts.set(question.question_type, next);
    return {
      id: question.id,
      displayIndex: next,
      type: question.question_type,
      answered: Boolean(answers[question.id]),
      submittedResult: getSubmittedResult?.(question),
      targetId: getTargetId(question),
    };
  });
}

/**
 * Returns the 1-based per-type index for a question within a list.
 * Used by pages that need to render a chapter label matching the navigator's
 * numbering (e.g. "单选 01" instead of "单选 46").
 */
export function perTypeIndexOf<TQuestion extends { id: number; question_type: string }>(
  questions: TQuestion[],
  questionId: number,
): number {
  const target = questions.find((q) => q.id === questionId);
  if (!target) return 0;
  let count = 0;
  for (const question of questions) {
    if (question.question_type === target.question_type) {
      count += 1;
      if (question.id === questionId) {
        return count;
      }
    }
  }
  return 0;
}
