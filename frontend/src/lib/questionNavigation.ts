export type QuestionNavItem = {
  id: number;
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
  return questions.map((question, index) => ({
    id: question.id,
    displayIndex: index + 1,
    type: question.question_type,
    answered: Boolean(answers[question.id]),
    submittedResult: getSubmittedResult?.(question),
    targetId: getTargetId(question),
  }));
}
