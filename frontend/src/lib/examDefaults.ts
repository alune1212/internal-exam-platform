/**
 * Canonical defaults for the fixed-paper exam rule shared by the
 * `createAdminExam` API helper and the `ExamEditPage` form. Keep these in
 * sync with the backend defaults documented in `CLAUDE.md` (50 题 / 100 分 /
 * 及格 60 / 单选 30 / 多选 10 / 判断 10).
 */
export const DEFAULT_FIXED_PAPER_RULE = {
  question_count: 50,
  total_score: 100,
  pass_score: 60,
  mode: "fixed_paper",
  type_counts: { single: 30, multiple: 10, judge: 10 },
} as const;

/**
 * Payload used by `createAdminExam` when an admin clicks the quick "新建考试"
 * button. Mirrors the form's `defaultValues` so the resulting draft is the
 * shape the form would produce on first open.
 */
export const DEFAULT_NEW_EXAM_PAYLOAD = {
  title: "新考试",
  description: null,
  duration_minutes: 60,
  question_rule: DEFAULT_FIXED_PAPER_RULE,
  status: "draft",
  show_answer_after_submit: true,
} as const;

export type FixedPaperRule = typeof DEFAULT_FIXED_PAPER_RULE;
