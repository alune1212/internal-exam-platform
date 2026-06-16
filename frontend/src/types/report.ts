export type ScoreReportRow = {
  candidate_name: string;
  employee_no?: string | null;
  department?: string | null;
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
  name: string;
  employee_no?: string | null;
  department?: string | null;
  exam_group?: string | null;
  attendance_status: "not_started" | "in_progress" | "submitted";
};
