import type { Page, Route } from "@playwright/test";

import {
  VISUAL_SYSTEM_VIEWPORTS,
  type VisualBrowserState,
  type VisualScenario,
} from "./route-state-inventory";

export type { VisualScenario } from "./route-state-inventory";
export {
  VISUAL_REPRESENTATIVE_GROUPS,
  VISUAL_REPRESENTATIVE_VIEWPORTS,
} from "./route-state-inventory";

export const CANDIDATE_URL = process.env.E2E_CANDIDATE_URL ?? "http://127.0.0.1:18080";
export const OPERATOR_URL = process.env.E2E_OPERATOR_URL ?? "http://127.0.0.1:18081";

export const VISUAL_NOW = "2098-01-15T09:00:00.000Z";
export const VISUAL_CANDIDATE_ID = 7;
export const VISUAL_EXAM_ID = 11;
export const VISUAL_ATTEMPT_ID = 10;
export const VISUAL_DRAFT_EXAM_ID = 12;
export const VISUAL_VIDEO_ID = 21;
export const VISUAL_QUESTION_ID = 101;
export const VISUAL_ATTEMPT_CREDENTIAL = "visual-attempt-credential";
export const VISUAL_CANDIDATE_TOKEN = "visual-candidate-token";
export const VISUAL_ADMIN_TOKEN = "visual-admin-token";

export const VISUAL_STORAGE_KEYS = {
  candidate: "internal-exam-candidate",
  admin: "internal-exam-admin-token",
  registration: "internal-exam-registration-flow",
  attemptSession: `internal-exam-attempt-session:${VISUAL_CANDIDATE_ID}:${VISUAL_ATTEMPT_ID}`,
  attemptDraft: `internal-exam-attempt-draft:${VISUAL_CANDIDATE_ID}:${VISUAL_ATTEMPT_ID}`,
} as const;

export const VISUAL_VIEWPORTS = VISUAL_SYSTEM_VIEWPORTS;
export const VISUAL_LANDSCAPE_VIEWPORTS = VISUAL_SYSTEM_VIEWPORTS.filter(
  ({ name }) => name === "landscape-phone" || name === "landscape-tablet",
);

export type VisualState = VisualBrowserState;
export type VisualAttemptStatus = "in_progress" | "submitted" | "auto_submitted";
export type VisualRouteState = VisualState | "default";

export type VisualAuthOptions = {
  candidate?: boolean;
  admin?: boolean;
  registration?: boolean;
  attempt?: boolean;
  draft?: boolean;
  answers?: Record<number, string>;
  longContent?: boolean;
};

export type VisualRouteOptions = {
  state?: VisualRouteState;
  attemptStatus?: VisualAttemptStatus;
  scenario?: VisualScenario;
  resultAnswersReleased?: boolean;
};

export type VisualRouteHandle = {
  unexpectedApiRequests: string[];
  failedRequests: string[];
  dispose: () => Promise<void>;
};

type JsonValue = Record<string, unknown> | readonly unknown[];

const candidate = {
  id: VISUAL_CANDIDATE_ID,
  email: "visual.candidate@example.test",
  display_name: "视觉验收候选人",
  status: "active" as const,
};

export const VISUAL_LONG_IDENTIFIER =
  "VISUAL_UNBROKEN_IDENTIFIER_20260814_ABCDEFGHIJKLMNOPQRSTUVWXYZ_0123456789";
export const VISUAL_LONG_CHINESE =
  "这是一段用于代表性渲染验收的较长中文内容，检查标题、说明、表格单元格和操作区域在窄屏、放大和横屏条件下是否能够自然换行。";

const longCandidate = {
  ...candidate,
  email: `${VISUAL_LONG_IDENTIFIER.toLowerCase()}@example.test`,
  display_name: `视觉验收候选人${VISUAL_LONG_CHINESE}`,
};

const questionOptions = [
  { label: "A", content: "保持题干和选项的可读间距。", sort_order: 1 },
  { label: "B", content: "把关键信息藏在装饰中。", sort_order: 2 },
  { label: "C", content: "让操作状态只靠颜色表达。", sort_order: 3 },
];

const longQuestionOptions = [
  {
    label: "A",
    content: `${VISUAL_LONG_CHINESE}${VISUAL_LONG_IDENTIFIER}`,
    sort_order: 1,
  },
  {
    label: "B",
    content: `保持答案、保存状态和下一步操作可见。${VISUAL_LONG_IDENTIFIER}`,
    sort_order: 2,
  },
  {
    label: "C",
    content: `使用原生语义并保留键盘箭头流转。${VISUAL_LONG_IDENTIFIER}`,
    sort_order: 3,
  },
];

const attemptQuestions = [
  {
    id: VISUAL_QUESTION_ID,
    question_type: "single",
    stem_snapshot: "视觉系统验收时，哪项信号最应该保持可见？",
    options_snapshot: questionOptions,
    score: 10,
    sort_order: 1,
    selected_answer: null,
  },
  {
    id: VISUAL_QUESTION_ID + 1,
    question_type: "multiple",
    stem_snapshot: "请选择所有稳定的验收条件。",
    options_snapshot: [
      { label: "A", content: "键盘焦点可见", sort_order: 1 },
      { label: "B", content: "根节点溢出被隐藏", sort_order: 2 },
      { label: "C", content: "操作按钮可达", sort_order: 3 },
    ],
    score: 10,
    sort_order: 2,
    selected_answer: null,
  },
];

const openExam = {
  id: VISUAL_EXAM_ID,
  title: "视觉系统验收考试",
  description: "用于验证候选人列表、开始页、答题页与结果页。",
  duration_minutes: 45,
  question_rule: { question_count: 2, total_score: 20, pass_score: 12 },
  status: "active",
  show_answer_after_submit: true,
  available_from: VISUAL_NOW,
  available_until: "2098-01-15T11:00:00.000Z",
  result_details_released_at: VISUAL_NOW,
  latest_attempt_id: null,
  latest_attempt_status: null,
  has_unused_retake_grant: false,
  question_pool_count: 2,
  availability_status: "open" as const,
};

const upcomingExam = {
  ...openExam,
  id: VISUAL_DRAFT_EXAM_ID,
  title: "即将开放的视觉复核",
  status: "published",
  available_from: "2098-01-15T12:00:00.000Z",
  available_until: "2098-01-15T14:00:00.000Z",
  availability_status: "not_started" as const,
};

const draftExam = {
  ...openExam,
  id: VISUAL_DRAFT_EXAM_ID,
  title: "草稿考试 · 配置态",
  status: "draft",
  latest_attempt_id: null,
  latest_attempt_status: null,
  availability_status: "not_started" as const,
};

const attempt = {
  id: VISUAL_ATTEMPT_ID,
  exam_id: VISUAL_EXAM_ID,
  candidate_id: VISUAL_CANDIDATE_ID,
  status: "in_progress",
  started_at: VISUAL_NOW,
  duration_minutes: 45,
  ends_at: "2098-01-15T09:45:00.000Z",
  server_now: VISUAL_NOW,
  submitted_at: null,
  score: 0,
  total_score: 20,
  correct_count: 0,
  wrong_count: 0,
  attempt_session_generation: 1,
  answer_revision: 0,
  questions: attemptQuestions,
};

const attemptResult = {
  attempt_id: VISUAL_ATTEMPT_ID,
  score: 10,
  total_score: 20,
  pass_score: 12,
  is_passed: false,
  show_answer_after_submit: true,
  correct_count: 1,
  wrong_count: 1,
  questions: [
    {
      attempt_question_id: VISUAL_QUESTION_ID,
      stem_snapshot: attemptQuestions[0].stem_snapshot,
      selected_answer: "A",
      correct_answer_snapshot: "A",
      analysis_snapshot: "焦点、状态和操作都需要被看见。",
      is_correct: true,
      score_awarded: 10,
      score: 10,
    },
    {
      attempt_question_id: VISUAL_QUESTION_ID + 1,
      stem_snapshot: attemptQuestions[1].stem_snapshot,
      selected_answer: "B",
      correct_answer_snapshot: "AC",
      analysis_snapshot: "根节点剪裁不能代替溢出检查。",
      is_correct: false,
      score_awarded: 0,
      score: 10,
    },
  ],
};

const learningVideos = [
  {
    id: VISUAL_VIDEO_ID,
    title: "考试前的界面检查",
    description: "用一段短视频熟悉答题和保存状态。",
    original_filename: "visual-check.mp4",
    storage_key: "visual-check.mp4",
    content_type: "video/mp4",
    file_size_bytes: 1024,
    duration_seconds: 180,
    completion_threshold_percent: 90,
    status: "published" as const,
    uploaded_at: VISUAL_NOW,
    created_at: VISUAL_NOW,
    updated_at: VISUAL_NOW,
    playback_url: "/assets/visual-check.mp4",
    progress: {
      last_position_seconds: 60,
      watched_seconds: 60,
      completion_percent: 33,
      completed_at: null,
      last_heartbeat_at: VISUAL_NOW,
    },
  },
];

const practiceQuestion = {
  id: VISUAL_QUESTION_ID,
  question_type: "single",
  stem: "练习题：哪个状态应该向用户说明下一步？",
  category_1: "界面验收",
  category_2: "状态语言",
  difficulty: "easy",
  score: 10,
  status: "active",
  source: "visual-fixture",
  source_no: "V-101",
  remark: null,
  options: questionOptions.map(({ label, content, sort_order }) => ({
    id: VISUAL_QUESTION_ID + sort_order,
    label,
    content,
    sort_order,
  })),
};

const wrongQuestion = {
  question_id: VISUAL_QUESTION_ID,
  question_type: "single",
  stem: practiceQuestion.stem,
  category_1: "界面验收",
  category_2: "状态语言",
  status: "active",
  correct_answer: "A",
  analysis: "状态需要文字、语义和恢复动作。",
  incorrect_count: 1,
  total_attempts: 2,
  mastered: false,
  latest_practiced_at: VISUAL_NOW,
  history: [
    {
      practice_answer_id: 301,
      selected_answer: "B",
      is_correct: false,
      practiced_at: VISUAL_NOW,
    },
  ],
  options: questionOptions.map(({ label, content }) => ({
    label,
    content,
    selected: label === "B",
    correct: label === "A",
  })),
};

const adminQuestion = {
  id: VISUAL_QUESTION_ID,
  question_type: "single",
  stem: practiceQuestion.stem,
  analysis: "每种状态都要有清晰反馈。",
  category_1: "界面验收",
  category_2: "状态语言",
  difficulty: "easy",
  score: 10,
  status: "active",
  source: "visual-fixture",
  source_no: "V-101",
  remark: null,
  options: questionOptions.map((option, index) => ({
    id: VISUAL_QUESTION_ID + index,
    ...option,
    is_correct: index === 0,
  })),
};

const rosterRow = {
  scope_id: 201,
  candidate_id: VISUAL_CANDIDATE_ID,
  roster_email: candidate.email,
  roster_name: candidate.display_name,
  department: "产品设计",
  position: "体验研究",
  exam_group: "视觉系统",
  roster_remark: "稳定 fixture",
  account_status: "active",
  invitation_status: "sent",
  invitation_error_class: null,
  last_invitation_attempt_at: VISUAL_NOW,
  invitation_sent_at: VISUAL_NOW,
  invitation_claimed_at: VISUAL_NOW,
  latest_attempt_id: VISUAL_ATTEMPT_ID,
  latest_attempt_status: "in_progress",
  latest_score: null,
  latest_total_score: 20,
  latest_submitted_at: null,
  attempt_no: 1,
  attempt_kind: "formal",
  has_unused_retake_grant: false,
};

const readiness = {
  exam_id: VISUAL_EXAM_ID,
  ready: true,
  prospective_pool_count: 2,
  roster_count: 1,
  blockers: [],
  warnings: [],
  fingerprint: "visual-readiness-v1",
};

const workspace = {
  observed_at: VISUAL_NOW,
  exam: openExam,
  readiness,
  roster_summary: { total_count: 1, active_count: 1, pending_count: 0, inactive_count: 0 },
  invitation_summary: { not_sent_count: 0, sent_count: 1, failed_count: 0, in_flight_count: 0 },
  attendance_summary: { not_started_count: 0, in_progress_count: 1, submitted_count: 0 },
  attempt_summary: {
    in_progress_count: 1,
    submitted_count: 0,
    auto_submitted_count: 0,
    voided_count: 0,
  },
  incident_summary: { voided_count: 0, unused_retake_count: 0 },
  next_action: "monitor_exam",
  next_action_reason: "考试正在进行，继续关注答题进度。",
};

const scoreRow = {
  candidate_id: VISUAL_CANDIDATE_ID,
  roster_name: candidate.display_name,
  roster_email: candidate.email,
  department: "产品设计",
  position: "体验研究",
  exam_group: "视觉系统",
  roster_remark: null,
  exam_id: VISUAL_EXAM_ID,
  exam_title: openExam.title,
  score: 10,
  total_score: 20,
  submitted_at: VISUAL_NOW,
};

const absentRow = {
  candidate_id: VISUAL_CANDIDATE_ID,
  exam_id: VISUAL_EXAM_ID,
  exam_title: openExam.title,
  roster_name: candidate.display_name,
  roster_email: candidate.email,
  department: "产品设计",
  position: "体验研究",
  exam_group: "视觉系统",
  roster_remark: null,
  attendance_status: "not_started" as const,
};

const learningReportRow = {
  candidate_id: VISUAL_CANDIDATE_ID,
  account_email: candidate.email,
  display_name: candidate.display_name,
  account_status: "active",
  video_id: VISUAL_VIDEO_ID,
  video_title: learningVideos[0].title,
  video_status: "published" as const,
  duration_seconds: 180,
  completion_percent: 33,
  completion_status: "in_progress" as const,
  last_heartbeat_at: VISUAL_NOW,
  completed_at: null,
};

const operationsSnapshot = {
  checked_at: VISUAL_NOW,
  version: { status: "current", summary: "版本正常", checked_at: VISUAL_NOW, details: {} },
  migration: { status: "current", summary: "迁移正常", checked_at: VISUAL_NOW, details: {} },
  service_health: { status: "current", summary: "服务正常", checked_at: VISUAL_NOW, details: {} },
  worker_health: {
    status: "current",
    summary: "后台任务正常",
    checked_at: VISUAL_NOW,
    details: {},
  },
  operational_lock: { status: "current", summary: "无操作锁", checked_at: VISUAL_NOW, details: {} },
  disk_reserve: { status: "current", summary: "磁盘充足", checked_at: VISUAL_NOW, details: {} },
  backup: { status: "current", summary: "备份正常", checked_at: VISUAL_NOW, details: {} },
  second_copy: { status: "current", summary: "第二副本正常", checked_at: VISUAL_NOW, details: {} },
  restore_drill: {
    status: "current",
    summary: "恢复演练正常",
    checked_at: VISUAL_NOW,
    details: {},
  },
  retention: { status: "current", summary: "保留策略正常", checked_at: VISUAL_NOW, details: {} },
  security_scan: {
    status: "current",
    summary: "安全扫描正常",
    checked_at: VISUAL_NOW,
    details: {},
  },
};

type VisualFixtureDataOptions = {
  longContent: boolean;
  resultAnswersReleased: boolean;
};

function fixtureCandidate({ longContent }: VisualFixtureDataOptions) {
  return longContent ? longCandidate : candidate;
}

function fixtureQuestionOptions({ longContent }: VisualFixtureDataOptions) {
  return longContent ? longQuestionOptions : questionOptions;
}

function fixtureAttemptQuestions({ longContent }: VisualFixtureDataOptions) {
  const options = fixtureQuestionOptions({ longContent, resultAnswersReleased: true });
  return attemptQuestions.map((question, index) => ({
    ...question,
    stem_snapshot: longContent
      ? `${question.stem_snapshot}${VISUAL_LONG_CHINESE}`
      : question.stem_snapshot,
    options_snapshot:
      index === 0
        ? options
        : longContent
          ? options.map((option) => ({
              ...option,
              content: `${option.content}${VISUAL_LONG_IDENTIFIER}`,
            }))
          : question.options_snapshot,
  }));
}

function fixtureExam({ longContent }: VisualFixtureDataOptions) {
  return longContent
    ? {
        ...openExam,
        title: `视觉系统验收考试 · ${VISUAL_LONG_CHINESE}`,
        description: `${openExam.description}${VISUAL_LONG_IDENTIFIER}`,
      }
    : openExam;
}

function fixtureAttempt(
  { longContent }: VisualFixtureDataOptions,
  attemptStatus: VisualAttemptStatus,
) {
  return {
    ...attempt,
    status: attemptStatus,
    submitted_at: attemptStatus === "in_progress" ? null : VISUAL_NOW,
    questions: fixtureAttemptQuestions({ longContent, resultAnswersReleased: true }),
  };
}

function fixtureAttemptResult({ longContent, resultAnswersReleased }: VisualFixtureDataOptions) {
  const questions = longContent
    ? attemptResult.questions.map((question) => ({
        ...question,
        stem_snapshot: `${question.stem_snapshot}${VISUAL_LONG_CHINESE}`,
      }))
    : attemptResult.questions;
  return {
    ...attemptResult,
    show_answer_after_submit: resultAnswersReleased,
    questions: questions.map((question) => ({
      ...question,
      correct_answer_snapshot: resultAnswersReleased ? question.correct_answer_snapshot : null,
      analysis_snapshot: resultAnswersReleased ? question.analysis_snapshot : null,
    })),
  };
}

function fixtureAdminQuestion({ longContent }: VisualFixtureDataOptions) {
  return longContent
    ? {
        ...adminQuestion,
        stem: `${adminQuestion.stem}${VISUAL_LONG_CHINESE}`,
        analysis: `${adminQuestion.analysis}${VISUAL_LONG_IDENTIFIER}`,
        source: VISUAL_LONG_IDENTIFIER,
        source_no: `${VISUAL_LONG_IDENTIFIER}-SOURCE`,
        options: longQuestionOptions.map((option, index) => ({
          id: VISUAL_QUESTION_ID + index,
          ...option,
          is_correct: index === 0,
        })),
      }
    : adminQuestion;
}

function fixtureLearningVideos({ longContent }: VisualFixtureDataOptions) {
  return longContent
    ? learningVideos.map((video) => ({
        ...video,
        title: `${video.title} · ${VISUAL_LONG_CHINESE}`,
        description: `${video.description}${VISUAL_LONG_IDENTIFIER}`,
        original_filename: `${VISUAL_LONG_IDENTIFIER}.mp4`,
      }))
    : learningVideos;
}

function fixtureScoreRow({ longContent }: VisualFixtureDataOptions) {
  return longContent
    ? {
        ...scoreRow,
        roster_name: longCandidate.display_name,
        roster_email: longCandidate.email,
        department: `${scoreRow.department}${VISUAL_LONG_IDENTIFIER}`,
        position: `${scoreRow.position}${VISUAL_LONG_CHINESE}`,
        exam_title: `${scoreRow.exam_title}${VISUAL_LONG_IDENTIFIER}`,
      }
    : scoreRow;
}

function fixtureAbsentRow({ longContent }: VisualFixtureDataOptions) {
  return longContent
    ? {
        ...absentRow,
        roster_name: longCandidate.display_name,
        roster_email: longCandidate.email,
        exam_title: `${absentRow.exam_title}${VISUAL_LONG_IDENTIFIER}`,
      }
    : absentRow;
}

function fixtureLearningReportRow({ longContent }: VisualFixtureDataOptions) {
  return longContent
    ? {
        ...learningReportRow,
        account_email: longCandidate.email,
        display_name: longCandidate.display_name,
        video_title: `${learningReportRow.video_title}${VISUAL_LONG_CHINESE}`,
      }
    : learningReportRow;
}

export function responseEnvelope(data: JsonValue | unknown, message = "ok") {
  return JSON.stringify({ success: true, data, message });
}

export function candidateStorageValue(longContent = false) {
  const storageCandidate = longContent ? longCandidate : candidate;
  return JSON.stringify({
    ...storageCandidate,
    token: VISUAL_CANDIDATE_TOKEN,
    token_expires_at: "2099-01-01T00:00:00.000Z",
  });
}

export function adminStorageValue() {
  return VISUAL_ADMIN_TOKEN;
}

export function attemptSessionStorageValue() {
  return JSON.stringify({
    candidateId: VISUAL_CANDIDATE_ID,
    attemptId: VISUAL_ATTEMPT_ID,
    credential: VISUAL_ATTEMPT_CREDENTIAL,
    generation: 1,
    answerRevision: 0,
  });
}

export function attemptDraftStorageValue(answers: Record<number, string> = {}) {
  return JSON.stringify({
    candidateId: VISUAL_CANDIDATE_ID,
    attemptId: VISUAL_ATTEMPT_ID,
    generation: 1,
    baseRevision: 0,
    answers,
    updatedAt: VISUAL_NOW,
  });
}

export async function installVisualAuth(page: Page, options: VisualAuthOptions = {}) {
  const authCandidate = options.longContent ? longCandidate : candidate;
  const registration = {
    registration_credential: "visual-registration-credential",
    email: authCandidate.email,
    suggested_display_name: "视觉验收候选人",
    returnTo: "/exams",
    expires_at: "2099-01-01T00:00:00.000Z",
  };
  await page.addInitScript(
    ({ admin, attempt, candidateValue, registrationValue, attemptValue, draftValue }) => {
      window.sessionStorage.clear();
      if (candidateValue) window.sessionStorage.setItem("internal-exam-candidate", candidateValue);
      if (admin) window.sessionStorage.setItem("internal-exam-admin-token", admin);
      if (registrationValue) {
        window.sessionStorage.setItem("internal-exam-registration-flow", registrationValue);
      }
      if (attempt && attemptValue) {
        window.sessionStorage.setItem("internal-exam-attempt-session:7:10", attemptValue);
        if (draftValue) {
          window.sessionStorage.setItem("internal-exam-attempt-draft:7:10", draftValue);
        }
      }
    },
    {
      admin: options.admin ? adminStorageValue() : null,
      attempt: options.attempt ?? false,
      candidateValue: options.candidate ? candidateStorageValue(options.longContent) : null,
      registrationValue: options.registration ? JSON.stringify(registration) : null,
      attemptValue: options.attempt ? attemptSessionStorageValue() : null,
      draftValue:
        options.attempt && options.draft !== false
          ? attemptDraftStorageValue(options.answers)
          : null,
    },
  );
}

export async function setVisualOffline(page: Page, offline = true) {
  await page.context().setOffline(offline);
  await page.evaluate((isOffline) => {
    window.dispatchEvent(new Event(isOffline ? "offline" : "online"));
  }, offline);
}

function apiError(route: Route, status: number, detail: string) {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify({ detail }),
  });
}

function xlsxResponse(route: Route) {
  return route.fulfill({
    status: 200,
    contentType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    body: Buffer.from("visual-system-report"),
  });
}

function requestKey(route: Route) {
  const request = route.request();
  const url = new URL(request.url());
  return `${request.method()} ${url.pathname}${url.search}`;
}

function isGet(route: Route) {
  return route.request().method().toUpperCase() === "GET";
}

function shouldStale(
  key: string,
  state: VisualRouteState,
  requestCounts: Map<string, number>,
  isGetRequest: boolean,
) {
  if (state !== "stale" || !isGetRequest) return false;
  const count = requestCounts.get(key) ?? 0;
  requestCounts.set(key, count + 1);
  return count > 0;
}

function dataForPath(
  pathname: string,
  search: string,
  attemptStatus: VisualAttemptStatus,
  fixtureOptions: VisualFixtureDataOptions,
): JsonValue | unknown {
  const fixtureCandidateValue = fixtureCandidate(fixtureOptions);
  const fixtureExamValue = fixtureExam(fixtureOptions);
  const fixtureQuestions = fixtureAttemptQuestions(fixtureOptions);
  if (pathname === "/api/candidates/login") {
    return {
      challenge_id: 1,
      expires_at: "2098-01-15T09:10:00.000Z",
      resend_available_at: "2098-01-15T09:01:00.000Z",
    };
  }
  if (
    pathname === "/api/candidates/login/verify" ||
    pathname === "/api/candidates/register/complete"
  ) {
    return {
      outcome: "authenticated",
      account: fixtureCandidateValue,
      token: VISUAL_CANDIDATE_TOKEN,
      token_expires_at: "2099-01-01T00:00:00.000Z",
    };
  }
  if (pathname === "/api/admin/login") return { token: VISUAL_ADMIN_TOKEN, token_type: "bearer" };
  if (pathname === "/api/account/profile") return fixtureCandidateValue;
  if (pathname === "/api/exams/active") return [fixtureExamValue, upcomingExam];
  if (pathname === `/api/exams/${VISUAL_EXAM_ID}/start`) {
    return {
      attempt_id: VISUAL_ATTEMPT_ID,
      exam: {
        id: fixtureExamValue.id,
        title: fixtureExamValue.title,
        duration_minutes: fixtureExamValue.duration_minutes,
        show_answer_after_submit: true,
      },
      questions: fixtureQuestions,
      started_at: VISUAL_NOW,
      ends_at: "2098-01-15T09:45:00.000Z",
      attempt_session_credential: VISUAL_ATTEMPT_CREDENTIAL,
      attempt_session_generation: 1,
      answer_revision: 0,
    };
  }
  if (pathname === `/api/attempts/${VISUAL_ATTEMPT_ID}/result`)
    return fixtureAttemptResult(fixtureOptions);
  if (pathname === `/api/attempts/${VISUAL_ATTEMPT_ID}`) {
    return fixtureAttempt(fixtureOptions, attemptStatus);
  }
  if (pathname === "/api/practice/questions") return [practiceQuestion];
  if (pathname === "/api/practice/wrong-questions") return [wrongQuestion];
  if (pathname === "/api/learning/videos") return fixtureLearningVideos(fixtureOptions);
  if (pathname.startsWith("/api/learning/videos/")) return fixtureLearningVideos(fixtureOptions)[0];
  if (pathname === "/api/admin/exams") return [fixtureExamValue, draftExam];
  if (pathname === `/api/admin/exams/${VISUAL_EXAM_ID}/workspace`) return workspace;
  if (pathname === `/api/admin/exams/${VISUAL_EXAM_ID}/publication-readiness`) return readiness;
  if (pathname === `/api/admin/exams/${VISUAL_EXAM_ID}/candidates`) return [rosterRow];
  if (pathname === `/api/admin/exams/${VISUAL_EXAM_ID}/invitations`)
    return {
      ...readiness,
      rows: [rosterRow],
      total_count: 1,
      not_sent_count: 0,
      sent_count: 1,
      failed_count: 0,
    };
  if (pathname === `/api/admin/exams/${VISUAL_EXAM_ID}/incidents`) return [];
  if (pathname === "/api/admin/questions") return [fixtureAdminQuestion(fixtureOptions)];
  if (pathname === "/api/admin/accounts")
    return [
      {
        id: 301,
        email: fixtureCandidateValue.email,
        display_name: fixtureCandidateValue.display_name,
        status: "active",
        created_at: VISUAL_NOW,
        updated_at: VISUAL_NOW,
      },
    ];
  if (pathname === "/api/admin/learning/videos")
    return fixtureLearningVideos(fixtureOptions).map(({ progress, ...video }) => {
      void progress;
      return video;
    });
  if (pathname.startsWith("/api/admin/learning/videos/"))
    return fixtureLearningVideos(fixtureOptions)[0];
  if (pathname === "/api/admin/learning/reports") return [fixtureLearningReportRow(fixtureOptions)];
  if (pathname === "/api/admin/reports/scores") return [fixtureScoreRow(fixtureOptions)];
  if (pathname === "/api/admin/reports/rankings")
    return [{ ...fixtureScoreRow(fixtureOptions), rank: 1 }];
  if (pathname === "/api/admin/reports/question-accuracy")
    return [
      {
        question_id: VISUAL_QUESTION_ID,
        stem: practiceQuestion.stem,
        correct_count: 1,
        total_count: 2,
        accuracy_rate: 0.5,
      },
    ];
  if (pathname === "/api/admin/reports/wrong-questions")
    return [
      {
        question_id: VISUAL_QUESTION_ID,
        stem: practiceQuestion.stem,
        wrong_count: 1,
        category_1: "界面验收",
        category_2: "状态语言",
      },
    ];
  if (pathname === "/api/admin/reports/absent-candidates")
    return [fixtureAbsentRow(fixtureOptions)];
  if (pathname === "/api/admin/operations/snapshot") return operationsSnapshot;
  if (
    pathname === "/api/admin/imports/templates/questions" ||
    pathname === "/api/admin/imports/templates/exam-roster"
  )
    return [];
  if (pathname.startsWith("/api/admin/imports/") && pathname.endsWith("/failure-report")) return [];
  if (
    pathname.startsWith("/api/admin/reports/export") ||
    pathname.startsWith("/api/admin/learning/reports/export")
  )
    return [];
  void search;
  return [];
}

export async function installVisualRoutes(
  page: Page,
  options: VisualRouteOptions = {},
): Promise<VisualRouteHandle> {
  const apiPattern = /^https?:\/\/[^/]+\/api(?:\/|$)/;
  const state = options.state ?? "ready";
  const scenario = options.scenario ?? "baseline";
  const fixtureOptions: VisualFixtureDataOptions = {
    longContent:
      scenario === "long-content" ||
      scenario === "long-options" ||
      scenario === "question-form-open" ||
      scenario === "learning-video-controls",
    resultAnswersReleased: options.resultAnswersReleased ?? scenario !== "result-unreleased",
  };
  const attemptStatus =
    options.attemptStatus ??
    (state === "submitted"
      ? "submitted"
      : state === "auto-submitted"
        ? "auto_submitted"
        : "in_progress");
  const unexpectedApiRequests: string[] = [];
  const failedRequests: string[] = [];
  const requestCounts = new Map<string, number>();
  const handler = async (route: Route) => {
    const request = route.request();
    const url = new URL(request.url());
    const key = requestKey(route);
    const pathname = url.pathname;
    if (
      pathname.startsWith("/api/admin/") &&
      (pathname.includes("/export") || pathname.includes("/templates/"))
    ) {
      await xlsxResponse(route);
      return;
    }
    if (state === "loading") return;
    if (state === "error" && isGet(route)) {
      failedRequests.push(key);
      await apiError(route, 503, "视觉系统 fixture 暂时不可用");
      return;
    }
    if (state === "saving" && pathname.endsWith("/answers/save")) return;
    if (
      state === "saving" &&
      !isGet(route) &&
      (pathname === "/api/admin/questions" ||
        pathname.startsWith("/api/admin/questions/") ||
        pathname === "/api/admin/learning/videos" ||
        pathname.startsWith("/api/admin/learning/videos/"))
    )
      return;
    if (state === "conflict" && pathname.endsWith("/answers/save")) {
      failedRequests.push(key);
      await apiError(route, 409, "答案版本冲突，请刷新后重试。");
      return;
    }
    if (state === "submit" && pathname.endsWith("/submit")) return;
    if (shouldStale(key, state, requestCounts, isGet(route))) {
      failedRequests.push(key);
      await apiError(route, 503, "汇总已过期，请重试。");
      return;
    }
    if (pathname.endsWith("/answers/save")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: responseEnvelope({ saved_count: 1, saved_at: VISUAL_NOW, answer_revision: 1 }),
      });
      return;
    }
    if (pathname.endsWith("/submit")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: responseEnvelope(fixtureAttemptResult(fixtureOptions)),
      });
      return;
    }
    if (
      request.method().toUpperCase() === "GET" ||
      request.method().toUpperCase() === "POST" ||
      request.method().toUpperCase() === "PATCH" ||
      request.method().toUpperCase() === "PUT"
    ) {
      const known =
        [
          "/api/candidates/login",
          "/api/candidates/login/verify",
          "/api/candidates/register/complete",
          "/api/admin/login",
          "/api/account/profile",
          "/api/exams/active",
          "/api/practice/questions",
          "/api/practice/wrong-questions",
          "/api/learning/videos",
          "/api/admin/exams",
          "/api/admin/questions",
          "/api/admin/accounts",
          "/api/admin/learning/videos",
          "/api/admin/learning/reports",
          "/api/admin/reports/scores",
          "/api/admin/reports/rankings",
          "/api/admin/reports/question-accuracy",
          "/api/admin/reports/wrong-questions",
          "/api/admin/reports/absent-candidates",
          "/api/admin/operations/snapshot",
        ].includes(pathname) ||
        pathname.startsWith(`/api/exams/${VISUAL_EXAM_ID}/`) ||
        pathname.startsWith(`/api/attempts/${VISUAL_ATTEMPT_ID}`) ||
        pathname.startsWith(`/api/admin/exams/${VISUAL_EXAM_ID}/`) ||
        pathname.startsWith("/api/admin/questions/") ||
        pathname.startsWith("/api/admin/learning/videos/") ||
        pathname.startsWith("/api/admin/imports/") ||
        pathname.startsWith("/api/admin/reports/export") ||
        pathname.startsWith("/api/admin/learning/reports/export");
      if (!known) unexpectedApiRequests.push(key);
      const data = dataForPath(pathname, url.search, attemptStatus, fixtureOptions);
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: responseEnvelope(data),
      });
      return;
    }
    unexpectedApiRequests.push(key);
    await route.abort("blockedbyclient");
  };
  await page.route(apiPattern, handler);
  return {
    unexpectedApiRequests,
    failedRequests,
    dispose: () => page.unroute(apiPattern, handler),
  };
}

export function visualFixture(options: VisualRouteOptions = {}) {
  return { options, candidate, openExam, upcomingExam, draftExam, attempt, attemptResult };
}
