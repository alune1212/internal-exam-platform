export type LearningVideoStatus = "draft" | "published" | "archived";
export type LearningCompletionStatus = "not_started" | "in_progress" | "completed";

export type LearningVideoProgress = {
  last_position_seconds: number;
  watched_seconds: number;
  completion_percent: number;
  completed_at?: string | null;
  last_heartbeat_at?: string | null;
};

export type LearningVideo = {
  id: number;
  title: string;
  description?: string | null;
  original_filename: string;
  storage_key: string;
  content_type: string;
  file_size_bytes: number;
  duration_seconds: number;
  completion_threshold_percent: number;
  status: LearningVideoStatus;
  uploaded_at: string;
  created_at: string;
  updated_at: string;
  playback_url: string;
};

export type CandidateLearningVideo = LearningVideo & {
  progress: LearningVideoProgress;
};

export type LearningProgressPayload = {
  current_position_seconds: number;
  watched_start_seconds: number;
  watched_end_seconds: number;
};

export type LearningVideoUpdatePayload = {
  title?: string;
  description?: string | null;
};

export type LearningVideoUploadPayload = {
  title: string;
  description?: string | null;
  duration_seconds: number;
  file: File;
};

export type LearningReportRow = {
  candidate_id: number;
  account_email: string;
  display_name: string;
  account_status: "pending" | "active" | "inactive" | string;
  video_id: number;
  video_title: string;
  video_status: LearningVideoStatus;
  duration_seconds: number;
  completion_percent: number;
  completion_status: LearningCompletionStatus;
  last_heartbeat_at?: string | null;
  completed_at?: string | null;
};
