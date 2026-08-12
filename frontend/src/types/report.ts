export type ScoreReportRow = {
  candidate_id: number;
  roster_name: string;
  roster_email: string;
  department?: string | null;
  position?: string | null;
  exam_group?: string | null;
  roster_remark?: string | null;
  exam_id: number;
  exam_title: string;
  score: number;
  total_score: number;
  submitted_at?: string | null;
};

export type RankingRow = {
  rank: number;
  candidate_id: number;
  roster_name: string;
  roster_email: string;
  department?: string | null;
  position?: string | null;
  exam_group?: string | null;
  roster_remark?: string | null;
  exam_id: number;
  exam_title: string;
  score: number;
  total_score: number;
  submitted_at?: string | null;
};

export type QuestionAccuracyRow = {
  question_id: number;
  stem: string;
  correct_count: number;
  total_count: number;
  accuracy_rate: number;
};

export type WrongQuestionRow = {
  question_id: number;
  stem: string;
  wrong_count: number;
  category_1?: string | null;
  category_2?: string | null;
};

export type AbsentCandidateRow = {
  candidate_id: number;
  exam_id: number;
  exam_title?: string | null;
  roster_name: string;
  roster_email: string;
  department?: string | null;
  position?: string | null;
  exam_group?: string | null;
  roster_remark?: string | null;
  attendance_status: "not_started" | "in_progress" | "submitted";
};
