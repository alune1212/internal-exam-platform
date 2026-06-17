export type QuestionType = "single" | "multiple" | "judge";

export type QuestionOption = {
  id: number;
  label: string;
  content: string;
  is_correct: boolean;
  sort_order: number;
};

export type QuestionOptionPayload = Omit<QuestionOption, "id">;

export type AdminQuestion = {
  id: number;
  question_type: QuestionType | string;
  stem: string;
  analysis?: string | null;
  category_1?: string | null;
  category_2?: string | null;
  difficulty?: string | null;
  score: number;
  status: string;
  source?: string | null;
  source_no?: string | null;
  remark?: string | null;
  options: QuestionOption[];
};

export type PracticeQuestionOption = Omit<QuestionOption, "is_correct">;

export type PracticeQuestion = Omit<AdminQuestion, "analysis" | "options"> & {
  options: PracticeQuestionOption[];
};

export type Question = AdminQuestion;

export type QuestionPayload = Omit<AdminQuestion, "id" | "options"> & {
  options: QuestionOptionPayload[];
};

export type PracticeAnswerResult = {
  question_id: number;
  selected_answer: string;
  correct_answer: string;
  is_correct: boolean;
  score_awarded: number;
  score: number;
  analysis?: string | null;
};
