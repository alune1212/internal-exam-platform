export type AttemptQuestion = {
  id: number;
  question_type: string;
  stem_snapshot: string;
  options_snapshot: Array<Record<string, unknown>>;
  score: number;
  sort_order: number;
  selected_answer?: string | null;
};

export type Attempt = {
  id: number;
  exam_id: number;
  candidate_id: number;
  status: string;
  started_at: string;
  submitted_at?: string | null;
  score: number;
  total_score: number;
  correct_count: number;
  wrong_count: number;
  questions: AttemptQuestion[];
};

export type AttemptResult = {
  attempt_id: number;
  score: number;
  total_score: number;
  correct_count: number;
  wrong_count: number;
  questions: Array<{
    attempt_question_id: number;
    stem_snapshot: string;
    selected_answer?: string | null;
    correct_answer_snapshot: string;
    analysis_snapshot?: string | null;
    is_correct: boolean;
    score_awarded: number;
    score: number;
  }>;
};
