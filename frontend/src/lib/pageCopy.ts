export const candidatePageCopy = {
  login: "EXAM TAKER · 登录",
  practice: "PRACTICE · 练习",
  exams: "EXAMS · 考试",
  examRules: "EXAM RULES · 考试说明",
  result: "EXAM RESULT · 考试结果",
  review: "REVIEW · 答题回顾",
  notLoggedIn: "STATE · 未登录",
  notStarted: "STATE · 未开始",
  submitted: "STATE · 已交卷",
  empty: "STATE · 空状态",
  error: "STATE · 异常状态",
} as const;

export const adminPageCopy = {
  login: "ADMIN · 登录",
  overview: "DASHBOARD · 仪表盘",
  exams: "EXAMS · 考试",
  participants: "PARTICIPANTS · 应考人员",
  roster: "ROSTER · 应考名单",
  library: "QUESTION BANK · 题库",
  questionImport: "QUESTION IMPORT · 题库导入",
  reports: "REPORTS · 报表",
  empty: "STATE · 空状态",
  error: "STATE · 异常状态",
} as const;

export const productTerms = {
  examTaker: "考试人",
  participant: "应考人员",
  roster: "应考名单",
  questionBank: "题库",
  questionBankImport: "题库导入",
} as const;

export const candidateActionCopy = {
  returnExamList: "返回考试列表",
  saveAnswer: "保存答案",
  savingAnswer: "正在保存",
  savePending: "待保存",
  savedAnswer: "已保存",
  saveFailed: "保存失败",
  retrySave: "重试保存",
  submitExam: "交卷",
  submittingExam: "正在交卷",
  submitFailed: "交卷失败",
} as const;

export const importCopy = {
  selectExcelFile: "选择 Excel 文件",
  noFileSelected: "未选择文件",
  excelFormat: "Excel .xlsx / .xls",
  importing: "正在导入",
  questionTemplate: "下载题库导入模板",
  rosterTemplate: "下载应考名单导入模板",
  uploadQuestionBank: "上传并校验题库",
  uploadRoster: "上传应考名单",
  questionImportComplete: "题库导入完成。",
  questionImportFailed: "题库导入失败",
  rosterImportComplete: "应考名单导入完成。",
  rosterImportFailed: "应考名单导入失败",
  failureReportStarted: "失败明细已开始下载。",
  failureReportFailed: "失败明细下载失败",
} as const;

export const adminTableCopy = {
  id: "ID",
  candidateId: "CID · 人员ID",
  questionId: "QID · 题目ID",
  title: "TITLE · 名称",
  name: "NAME · 姓名",
  employeeNo: "EMP NO · 工号",
  department: "DEPT · 部门",
  exam: "EXAM · 考试",
  duration: "DURATION · 时长",
  status: "STATUS · 状态",
  openWindow: "WINDOW · 开放时间",
  questionPool: "POOL · 题池",
  questionType: "TYPE · 题型",
  stem: "STEM · 题干",
  score: "SCORE · 得分",
  totalScore: "TOTAL · 总分",
  totalCount: "TOTAL · 总数",
  correct: "CORRECT · 正确",
  wrong: "WRONG · 错误",
  rate: "RATE · 正确率",
  category1: "CAT 1 · 一级分类",
  category2: "CAT 2 · 二级分类",
  group: "GROUP · 分组",
  attempt: "ATTEMPT · 作答",
  action: "ACTION · 操作",
} as const;

const examStatusCopy: Record<string, string> = {
  draft: "DRAFT · 草稿",
  active: "PUBLISHED · 已发布",
  live: "PUBLISHED · 已发布",
  published: "PUBLISHED · 已发布",
  archived: "ENDED · 已结束",
  ended: "ENDED · 已结束",
};

const examAvailabilityCopy: Record<string, string> = {
  not_started: "NOT OPEN · 未开放",
  open: "OPEN · 可进入",
  ended: "ENDED · 已结束",
};

const attemptStatusCopy: Record<string, string> = {
  not_started: "NOT STARTED · 未开始",
  in_progress: "IN PROGRESS · 进行中",
  submitted: "SUBMITTED · 已交卷",
  auto_submitted: "AUTO SUBMITTED · 自动交卷",
};

const attemptKindCopy: Record<string, string> = {
  initial: "INITIAL · 首次考试",
  retake: "RETAKE · 补考",
};

const questionTypeCopy: Record<string, { label: string; shortLabel: string }> = {
  single: { label: "SINGLE · 单选", shortLabel: "单选" },
  multiple: { label: "MULTIPLE · 多选", shortLabel: "多选" },
  judge: { label: "JUDGE · 判断", shortLabel: "判断" },
};

const questionStatusCopy: Record<string, string> = {
  active: "ACTIVE · 启用",
  inactive: "INACTIVE · 停用",
};

export function formatExamStatus(status?: string | null) {
  return status ? (examStatusCopy[status] ?? "UNKNOWN · 未知状态") : "UNKNOWN · 未知状态";
}

export function formatExamAvailability(status?: string | null) {
  return status
    ? (examAvailabilityCopy[status] ?? "UNKNOWN · 未知开放状态")
    : "UNKNOWN · 未知开放状态";
}

export function formatAttemptStatus(status?: string | null) {
  return status
    ? (attemptStatusCopy[status] ?? "UNKNOWN · 未知作答状态")
    : attemptStatusCopy.not_started;
}

export function formatAttemptStatusShort(status?: string | null) {
  const label = formatAttemptStatus(status);
  return label.includes(" · ") ? label.split(" · ")[1] : label;
}

export function formatAttemptKind(kind?: string | null) {
  return kind ? (attemptKindCopy[kind] ?? "UNKNOWN · 未知考试类型") : "UNKNOWN · 未知考试类型";
}

export function formatQuestionTypeLabel(questionType?: string | null) {
  return questionType
    ? (questionTypeCopy[questionType]?.label ?? "UNKNOWN · 未知题型")
    : "UNKNOWN · 未知题型";
}

export function formatQuestionTypeShortLabel(questionType?: string | null) {
  return questionType ? (questionTypeCopy[questionType]?.shortLabel ?? "未知题型") : "未知题型";
}

export function formatQuestionStatus(status?: string | null) {
  return status ? (questionStatusCopy[status] ?? "UNKNOWN · 未知状态") : "UNKNOWN · 未知状态";
}

export function formatQuestionEyebrow(index: number, typeLabel: string, score: number) {
  return `QUESTION ${String(index).padStart(2, "0")} · ${typeLabel} · ${score} 分`;
}
