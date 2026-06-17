export type Exam = {
  id: number;
  title: string;
  description?: string | null;
  duration_minutes: number;
  question_rule: Record<string, unknown>;
  status: string;
  show_answer_after_submit: boolean;
  available_from?: string | null;
  available_until?: string | null;
  latest_attempt_id?: number | null;
  latest_attempt_status?: string | null;
  has_unused_retake_grant?: boolean;
};

export type ExamCandidateRow = {
  candidate_id: number;
  candidate_name: string;
  employee_no?: string | null;
  department?: string | null;
  exam_group?: string | null;
  should_attend: boolean;
  candidate_status: string;
  latest_attempt_id?: number | null;
  latest_attempt_status?: string | null;
  latest_score?: number | null;
  latest_total_score?: number | null;
  latest_submitted_at?: string | null;
  attempt_no?: number | null;
  attempt_kind?: string | null;
  has_unused_retake_grant: boolean;
};
