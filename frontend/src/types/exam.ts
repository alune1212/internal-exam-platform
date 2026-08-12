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
  result_details_released_at?: string | null;
  result_details_released_by?: string | null;
  latest_attempt_id?: number | null;
  latest_attempt_status?: string | null;
  has_unused_retake_grant?: boolean;
  question_pool_count?: number;
  availability_status?: "not_started" | "open" | "ended";
};

export type ExamCandidateRow = {
  scope_id?: number;
  candidate_id: number;
  roster_email: string;
  roster_name: string;
  department?: string | null;
  position?: string | null;
  exam_group?: string | null;
  roster_remark?: string | null;
  account_status: "pending" | "active" | "inactive" | string;
  invitation_status: "not_sent" | "sent" | "failed" | string;
  invitation_error_class?: string | null;
  last_invitation_attempt_at?: string | null;
  invitation_sent_at?: string | null;
  invitation_claimed_at?: string | null;
  latest_attempt_id?: number | null;
  latest_attempt_status?: string | null;
  latest_score?: number | null;
  latest_total_score?: number | null;
  latest_submitted_at?: string | null;
  attempt_no?: number | null;
  attempt_kind?: string | null;
  has_unused_retake_grant: boolean;
};

export type ExamRosterPayload = {
  email: string;
  candidate_name: string;
  department?: string | null;
  position?: string | null;
  exam_group?: string | null;
  remark?: string | null;
};

export type InvitationDeliveryStatus = "not_sent" | "sent" | "failed";

export type InvitationScheduleResult = {
  exam_id?: number;
  mode?: string;
  selected_count?: number;
  accepted_count: number;
  rejected_count: number;
  scheduled_count?: number;
};

export type InvitationStatusRead = {
  exam_id: number;
  total_count?: number;
  not_sent_count?: number;
  sent_count?: number;
  failed_count?: number;
  rows: ExamCandidateRow[];
};

export type PublicationReadinessIssue = {
  code: string;
  message: string;
};

export type PublicationReadiness = {
  exam_id: number;
  ready: boolean;
  prospective_pool_count: number;
  roster_count: number;
  blockers: PublicationReadinessIssue[];
  warnings: PublicationReadinessIssue[];
  fingerprint: string;
};

export type ResultDetailsRelease = {
  exam_id: number;
  released_at: string;
  released_by: string;
};

export type AttemptIncident = {
  attempt_id: number;
  exam_id: number;
  candidate_id: number;
  prior_status: string;
  status: "voided";
  voided_at: string;
  voided_by: string;
  reason: string;
  attempt_no: number;
  retake_granted: boolean;
};

export type BulkRetakeRow = {
  candidate_id: number;
  candidate_name?: string | null;
  attempt_id?: number | null;
  prior_status?: string | null;
  outcome: string;
  reason: string;
};

export type BulkRetakePreview = {
  exam_id: number;
  void_existing: boolean;
  eligible_count: number;
  skipped_count: number;
  rows: BulkRetakeRow[];
  fingerprint: string;
};

export type BulkRetakeApply = BulkRetakePreview & {
  granted_count: number;
  voided_count: number;
  applied_at: string;
};
