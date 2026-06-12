export type AttemptQuestion = {
  id: number;
  question_type: string;
  stem_snapshot: string;
  options_snapshot: Array<{
    label: string;
    content: string;
    sort_order: number;
  }>;
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

export type ExamStartResponse = {
  attempt_id: number;
  exam: {
    id: number;
    title: string;
    duration_minutes: number;
    show_answer_after_submit: boolean;
    show_ranking: boolean;
  };
  questions: AttemptQuestion[];
  started_at: string;
  ends_at: string;
};

export type AnswerSaveItem = {
  attempt_question_id: number;
  selected_answer?: string | null;
};
