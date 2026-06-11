export type Exam = {
  id: number;
  title: string;
  description?: string | null;
  duration_minutes: number;
  question_rule: Record<string, unknown>;
  status: string;
  show_answer_after_submit: boolean;
  show_ranking: boolean;
};

export type RankingRow = {
  rank: number;
  candidate_name: string;
  department?: string | null;
  score: number;
  total_score: number;
  submitted_at?: string | null;
};
