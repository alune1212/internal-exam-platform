export const candidatePageCopy = {
  login: "邮箱登录",
  learning: "学习",
  practice: "练习",
  exams: "受邀考试",
  examRules: "考试说明",
  result: "考试结果",
  review: "答题回顾",
  notLoggedIn: "未登录",
  notStarted: "未开始",
  submitted: "已交卷",
  empty: "空状态",
  error: "异常状态",
} as const;

export const candidatePageText = {
  login: {
    title: "邮箱登录",
    description: "输入邮箱获取验证码。首次登录时，验证邮箱并填写姓名即可创建账号。",
    permissionNote: "登录后可进行学习、练习和错题复习；正式考试仅对受邀的应考人员开放。",
    error: "请求失败，请稍后重试。如问题持续，请联系管理员。",
    otpSent: (maskedEmail: string, validityMinutes = 10) =>
      `验证码已发送至 ${maskedEmail}，${validityMinutes} 分钟内有效。请查看收件箱和垃圾邮件；倒计时结束后可重新发送。`,
    otpError: "验证码无效或已过期，请重新获取后再试。",
    accountUnavailable: "该账号暂不可用，请联系管理员重新激活后再登录。",
    registrationTitle: "完成账号注册",
    registrationDescription: "验证邮箱后，请确认姓名即可创建账号。",
    profileTitle: "账号资料",
    profileDescription: "更新用户显示姓名；邮箱是账号的只读身份。",
  },
  exams: {
    title: "受邀考试",
    description: "已发布且受邀的考试会立即显示；开始前请确认开放时间和规则。",
    emptyTitle: "暂无受邀考试。",
    emptyDescription: "正式考试仅对受邀的应考人员开放；学习、练习和错题复习可随时使用。",
    errorTitle: "考试列表加载失败。",
    errorDescription: "请稍后重试，或联系管理员确认受邀考试状态。",
    invited: "已受邀",
    upcoming: "尚未开放",
    unavailable: "暂不可进入",
    available: "可以开始",
  },
  learning: {
    title: "视频学习",
    description: "观看管理员发布的学习视频，完成度达到 90% 后标记为已完成。",
    emptyTitle: "暂无学习视频。",
    emptyDescription: "管理员发布视频后会显示在这里。",
    errorTitle: "学习视频加载失败。",
    errorDescription: "请稍后重试，或联系管理员确认视频是否已发布。",
    detailErrorTitle: "视频加载失败。",
    detailErrorDescription: "请返回学习列表重新进入，或联系管理员确认视频状态。",
    completed: "已完成",
    inProgress: "学习中",
    notStarted: "未开始",
  },
  examRules: {
    title: "阅读规则，开始作答",
    description: "开始后生成题目快照并启动倒计时。",
  },
  result: {
    title: "本次答卷",
    description: "展示得分、通过状态与答题记录。",
    emptyTitle: "暂无答卷记录。",
    emptyDescription: "交卷后，这里会显示得分、答案与解析。",
    errorTitle: "答卷加载失败。",
    errorDescription: "请稍后重试，或从考试列表重新进入结果页。",
  },
  practice: {
    title: "日常练习",
    description: "不计入正式成绩，提交后立即查看正确答案与解析；重新作答会保留每次记录。",
    emptyTitle: "暂无可练习题目",
    emptyDescription: "管理员导入并启用题目后会显示。",
    errorTitle: "练习暂不可用。",
    errorDescription: "请稍后重试，或联系管理员确认题库状态。",
    loginTitle: "请先登录。",
    loginDescription: "登录后可进入练习，并保留本题记录。",
  },
} as const;

export const adminPageCopy = {
  login: "登录",
  overview: "仪表盘",
  exams: "考试",
  participants: "应考人员",
  roster: "应考名单",
  library: "题库",
  questionImport: "题库导入",
  reports: "报表",
  learning: "视频学习",
  empty: "空状态",
  error: "异常状态",
} as const;

export const adminPageText = {
  login: {
    title: "进入管理后台",
    description: "登录后可访问题库、考试编排与报表。",
  },
  questionBank: {
    title: "题库档案",
    description: "管理题目、状态与分类。",
  },
  questionImport: {
    title: "导入题目",
    description: "上传标准 Excel，系统会校验并保存可用题目。",
  },
  exams: {
    title: "考试编排",
    description: "创建、发布与维护考试规则。",
    errorTitle: "考试编排加载失败。",
  },
  roster: {
    title: "名单与授权",
    description: "管理本场考试的应考名单与补考授权。",
    importTitle: "导入名单",
    importDescription: "上传应考名单 Excel，写入当前考试。",
    errorTitle: "名单加载失败。",
  },
  reports: {
    score: {
      title: "成绩册",
      description: "按考试查看交卷结果。",
    },
    questionAccuracy: {
      title: "题目表现",
      description: "查看题目在本场考试中的答对比例。",
    },
    wrongQuestions: {
      title: "错题回看",
      description: "复盘高频错误题目。",
    },
    attendance: {
      title: "参考状态",
      description: "按未开始、进行中、已交卷拆分应考人员状态。",
    },
  },
  learning: {
    title: "视频学习",
    description: "上传学习视频并查看用户的观看完成情况。",
    reportTitle: "学习报表",
    reportDescription: "按视频和完成状态查看学习进度。",
  },
} as const;

/**
 * Canonical product vocabulary used by visible copy and contract tests.
 * `用户` names the authenticated person in general learning/practice flows;
 * `应考人员` names an exam-scoped roster or authorization record.
 */
export const productGlossary = {
  user: "用户",
  examTaker: "应考人员",
  participant: "应考人员",
  roster: "应考名单",
  questionBank: "题库",
  questionBankImport: "题库导入",
  saveAnswer: "保存答案",
  submitExam: "交卷",
  stayInExam: "留在考试",
  leaveExam: "离开考试",
  returnExamList: "返回考试列表",
} as const;

/**
 * The only English terms permitted in ordinary visible product copy.
 * Product names may remain bilingual; operational terms must add meaning.
 */
export const englishAllowlist = {
  productNames: ["Internal Exam Platform"] as const,
  operationalTerms: ["Excel", "ID", "OTP"] as const,
} as const;

export function formatAdminExamEditTitle(examId?: string | null) {
  return `编排考试 #${examId ?? "-"}`;
}

export const candidateActionCopy = {
  returnExamList: "返回考试列表",
  saveAnswer: "保存答案",
  savingAnswer: "正在保存答案",
  savePending: "待保存",
  savedAnswer: "答案已保存",
  saveOffline: "网络中断，答案待同步",
  saveConflict: "答案版本冲突，请重新接管",
  saveFailed: "保存失败",
  retrySave: "重试保存",
  resolveSaveConflict: "重新登录并接管",
  submitExam: "交卷",
  submittingExam: "正在交卷",
  submitFailed: "交卷失败",
  stayInExam: "留在考试",
  leaveExam: "离开考试",
  leaveExamWarning: "离开考试可能丢失最近的作答。",
  confirmLeaveExam: "仍要离开",
} as const;

export const candidateSaveAnnouncementCopy = {
  pending: "答案已记录，等待同步。",
  saving: "正在保存答案。",
  saved: "答案已保存。",
  offline: "当前离线，答案已保留在本页，待恢复网络后同步。",
  conflict: "答案版本冲突，请重新接管考试。",
  error: "答案保存失败，请重试。",
} as const;

const invitationErrorClassCopy: Record<string, string> = {
  transient: "邮件服务暂时不可用",
  permanent: "邮件地址或投递策略拒绝发送",
  smtp: "邮件服务连接失败",
  delivery_error: "邀请邮件投递失败",
};

export function formatInvitationErrorClass(errorClass?: string | null) {
  return errorClass
    ? (invitationErrorClassCopy[errorClass] ?? "邀请邮件投递失败")
    : "邀请邮件投递失败";
}

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
  id: "编号",
  candidateId: "人员编号",
  questionId: "题目编号",
  title: "名称",
  name: "姓名",
  employeeNo: "工号",
  department: "部门",
  exam: "考试",
  duration: "时长",
  status: "状态",
  video: "视频",
  videoStatus: "视频状态",
  progress: "完成度",
  completedAt: "完成时间",
  lastSeen: "最近学习",
  openWindow: "开放时间",
  questionPool: "题池",
  questionType: "题型",
  stem: "题干",
  score: "得分",
  totalScore: "总分",
  totalCount: "总数",
  correct: "正确",
  wrong: "错误",
  rate: "正确率",
  category1: "一级分类",
  category2: "二级分类",
  group: "分组",
  attempt: "作答",
  action: "操作",
} as const;

const examStatusCopy: Record<string, string> = {
  draft: "草稿",
  active: "已发布",
  live: "已发布",
  published: "已发布",
  archived: "已结束",
  ended: "已结束",
};

const examAvailabilityCopy: Record<string, string> = {
  not_started: "未开放",
  open: "可进入",
  ended: "已结束",
};

const attemptStatusCopy: Record<string, string> = {
  not_started: "未开始",
  in_progress: "进行中",
  submitted: "已交卷",
  auto_submitted: "自动交卷",
};

const attemptKindCopy: Record<string, string> = {
  initial: "首次考试",
  retake: "补考",
};

const questionTypeCopy: Record<string, { label: string; shortLabel: string }> = {
  single: { label: "单选", shortLabel: "单选" },
  multiple: { label: "多选", shortLabel: "多选" },
  judge: { label: "判断", shortLabel: "判断" },
};

const questionStatusCopy: Record<string, string> = {
  active: "启用",
  inactive: "停用",
};

const learningVideoStatusCopy: Record<string, string> = {
  draft: "草稿",
  published: "已发布",
  archived: "已归档",
};

const learningCompletionCopy: Record<string, string> = {
  not_started: "未开始",
  in_progress: "学习中",
  completed: "已完成",
};

export function formatExamStatus(status?: string | null) {
  return status ? (examStatusCopy[status] ?? "未知状态") : "未知状态";
}

/**
 * Map an exam.status string to the editorial pill variant. `active` and the
 * legacy aliases (`live`, `published`) read as in-flight; `archived` and
 * its closing aliases (`ended`, `closed`) read as warning.
 */
export function examStatusVariant(status: string): "success" | "warning" | "default" {
  if (status === "active" || status === "live" || status === "published") return "success";
  if (status === "archived" || status === "ended" || status === "closed") return "warning";
  return "default";
}

export function formatExamAvailability(status?: string | null) {
  return status ? (examAvailabilityCopy[status] ?? "未知开放状态") : "未知开放状态";
}

/**
 * Format an ISO timestamp with the zh-CN locale; falls back to the raw value
 * when the input is not a valid date (mirrors how admin dashboards display
 * sentinel strings like `"-"`).
 */
export function formatObservedAt(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN");
}

export function formatAttemptStatus(status?: string | null) {
  return status ? (attemptStatusCopy[status] ?? "未知作答状态") : attemptStatusCopy.not_started;
}

export function formatAttemptKind(kind?: string | null) {
  return kind ? (attemptKindCopy[kind] ?? "未知考试类型") : "未知考试类型";
}

export function formatQuestionTypeLabel(questionType?: string | null) {
  return questionType ? (questionTypeCopy[questionType]?.label ?? "未知题型") : "未知题型";
}

export function formatQuestionTypeShortLabel(questionType?: string | null) {
  return questionType ? (questionTypeCopy[questionType]?.shortLabel ?? "未知题型") : "未知题型";
}

export function formatQuestionStatus(status?: string | null) {
  return status ? (questionStatusCopy[status] ?? "未知状态") : "未知状态";
}

export function formatLearningVideoStatus(status?: string | null) {
  return status ? (learningVideoStatusCopy[status] ?? "未知视频状态") : "未知视频状态";
}

export function formatLearningCompletion(status?: string | null) {
  return status
    ? (learningCompletionCopy[status] ?? "未知学习状态")
    : learningCompletionCopy.not_started;
}

export function formatQuestionEyebrow(index: number, typeLabel: string, score: number) {
  return `第 ${String(index).padStart(2, "0")} 题 · ${typeLabel} · ${score} 分`;
}
