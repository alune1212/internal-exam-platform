export type QuestionType = "single" | "multiple" | "judge";

export type QuestionOption = {
  id: number;
  label: string;
  content: string;
  is_correct: boolean;
  sort_order: number;
};

export type Question = {
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

export type PracticeAnswerResult = {
  question_id: number;
  selected_answer: string;
  correct_answer: string;
  is_correct: boolean;
  score_awarded: number;
  score: number;
  analysis?: string | null;
};
