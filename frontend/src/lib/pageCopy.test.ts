import { describe, expect, it } from "vitest";

import {
  adminPageCopy,
  adminPageText,
  adminTableCopy,
  candidateActionCopy,
  candidatePageCopy,
  candidatePageText,
  englishAllowlist,
  formatAdminExamEditTitle,
  formatAttemptKind,
  formatAttemptStatus,
  formatExamAvailability,
  formatExamStatus,
  formatInvitationErrorClass,
  formatQuestionEyebrow,
  formatQuestionStatus,
  formatQuestionTypeLabel,
  importCopy,
  productGlossary,
} from "./pageCopy";

function flattenStrings(value: unknown): string[] {
  if (typeof value === "string") return [value];
  if (Array.isArray(value)) return value.flatMap(flattenStrings);
  if (value && typeof value === "object") return Object.values(value).flatMap(flattenStrings);
  return [];
}

describe("pageCopy", () => {
  it("keeps candidate and admin page-level copy Chinese-first", () => {
    const pageLevelCopy = [...Object.values(candidatePageCopy), ...Object.values(adminPageCopy)];

    expect(pageLevelCopy).not.toContain("CHAPTER");
    expect(pageLevelCopy.every((label) => !/[A-Z][A-Z\s]+\s·\s/.test(label))).toBe(true);
  });

  it("defines admin page-level copy with Chinese task labels", () => {
    expect(adminPageCopy).toMatchObject({
      login: "登录",
      overview: "仪表盘",
      exams: "考试",
      participants: "应考人员",
      roster: "应考名单",
      library: "题库",
      reports: "报表",
      empty: "空状态",
      error: "异常状态",
    });
  });

  it("defines restrained page titles separately from domain labels", () => {
    expect(candidatePageText).toMatchObject({
      login: { title: "邮箱登录" },
      exams: { title: "受邀考试" },
      examRules: { title: "阅读规则，开始作答" },
      result: { title: "本次答卷" },
      practice: { title: "日常练习", emptyTitle: "暂无可练习题目" },
    });
    expect(adminPageText).toMatchObject({
      questionBank: { title: "题库档案" },
      questionImport: { title: "导入题目" },
      exams: { title: "考试编排" },
      roster: { title: "名单与授权", importTitle: "导入名单" },
      reports: {
        score: { title: "成绩册" },
        questionAccuracy: { title: "题目表现" },
        wrongQuestions: { title: "错题回看" },
        attendance: { title: "参考状态" },
      },
    });
    expect(formatAdminExamEditTitle("12")).toBe("编排考试 #12");
  });

  it("keeps repeated admin table labels Chinese-first", () => {
    expect(adminTableCopy).toMatchObject({
      name: "姓名",
      employeeNo: "工号",
      department: "部门",
      score: "得分",
      totalCount: "总数",
      status: "状态",
    });
    expect(Object.values(adminTableCopy).every((label) => !label.includes(" · "))).toBe(true);
  });

  it("maps API enum values to user-facing labels", () => {
    expect(formatExamStatus("active")).toBe("已发布");
    expect(formatExamAvailability("not_started")).toBe("未开放");
    expect(formatExamAvailability()).toBe("未知开放状态");
    expect(formatAttemptStatus("submitted")).toBe("已交卷");
    expect(formatAttemptKind("retake")).toBe("补考");
    expect(formatQuestionTypeLabel("multiple")).toBe("多选");
    expect(formatQuestionStatus("inactive")).toBe("停用");
    expect(formatInvitationErrorClass("transient")).toBe("邮件服务暂时不可用");
    expect(formatInvitationErrorClass("internal_code")).toBe("邀请邮件投递失败");
  });

  it("keeps candidate critical action copy distinct", () => {
    expect(candidateActionCopy).toMatchObject({
      returnExamList: "返回考试列表",
      saveAnswer: "保存答案",
      savedAnswer: "答案已保存",
      saveOffline: "网络中断，答案待同步",
      saveConflict: "答案版本冲突，请重新接管",
      resolveSaveConflict: "重新登录并接管",
      submitExam: "交卷",
      stayInExam: "留在考试",
      leaveExam: "离开考试",
      confirmLeaveExam: "仍要离开",
    });
    expect(candidateActionCopy.saveAnswer).not.toBe(candidateActionCopy.submitExam);
    expect(candidateActionCopy.stayInExam).not.toBe(candidateActionCopy.leaveExam);
  });

  it("keeps the glossary and English allowlist narrow", () => {
    expect(productGlossary).toMatchObject({
      user: "用户",
      examTaker: "应考人员",
      saveAnswer: "保存答案",
      submitExam: "交卷",
      stayInExam: "留在考试",
      leaveExam: "离开考试",
    });
    expect(englishAllowlist.productNames).toEqual(["Internal Exam Platform"]);
    expect(englishAllowlist.operationalTerms).toEqual(["Excel", "ID", "OTP"]);
  });

  it("does not ship decorative bilingual labels in centralized copy", () => {
    const strings = flattenStrings({
      candidatePageCopy,
      candidatePageText,
      adminPageCopy,
      adminPageText,
      adminTableCopy,
      candidateActionCopy,
      importCopy,
    });

    expect(strings.filter((label) => /[A-Z][A-Z\s]+\s·\s/.test(label))).toEqual([]);
  });

  it("keeps import labels tied to the target object", () => {
    expect(importCopy.uploadQuestionBank).toBe("上传并校验题库");
    expect(importCopy.uploadRoster).toBe("上传应考名单");
  });

  it("keeps real question numbering in question-level copy", () => {
    expect(formatQuestionEyebrow(3, "单选", 2)).toBe("第 03 题 · 单选 · 2 分");
  });
});
