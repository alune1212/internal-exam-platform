export const candidatePageCopy = {
  login: "CANDIDATE · 登录",
  practice: "PRACTICE · 练习",
  exams: "EXAMS · 考试",
  examRules: "EXAM RULES · 考试说明",
  result: "RESULT · 成绩结果",
  review: "REVIEW · 答题回顾",
  notLoggedIn: "STATE · 未登录",
  notStarted: "STATE · 未开始",
  submitted: "STATE · 已提交",
  empty: "STATE · 空状态",
  error: "STATE · 异常状态",
} as const;

export function formatQuestionEyebrow(index: number, typeLabel: string, score: number) {
  return `QUESTION ${String(index).padStart(2, "0")} · ${typeLabel} · ${score} 分`;
}
