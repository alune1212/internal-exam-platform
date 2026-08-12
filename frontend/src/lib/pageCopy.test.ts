import { describe, expect, it } from "vitest";

import {
  adminPageCopy,
  adminPageText,
  adminTableCopy,
  candidateActionCopy,
  candidatePageCopy,
  candidatePageText,
  formatAdminExamEditTitle,
  formatAttemptKind,
  formatAttemptStatus,
  formatExamAvailability,
  formatExamStatus,
  formatQuestionEyebrow,
  formatQuestionStatus,
  formatQuestionTypeLabel,
  importCopy,
} from "./pageCopy";

describe("pageCopy", () => {
  it("keeps candidate and admin page-level copy free of chapter numbers", () => {
    const pageLevelCopy = [...Object.values(candidatePageCopy), ...Object.values(adminPageCopy)];

    expect(pageLevelCopy).not.toContain("CHAPTER");
    expect(pageLevelCopy.every((label) => !label.includes("CHAPTER"))).toBe(true);
  });

  it("defines admin page-level copy with semantic module labels", () => {
    expect(adminPageCopy).toMatchObject({
      login: "ADMIN · 登录",
      overview: "DASHBOARD · 仪表盘",
      exams: "EXAMS · 考试",
      participants: "PARTICIPANTS · 应考人员",
      roster: "ROSTER · 应考名单",
      library: "QUESTION BANK · 题库",
      reports: "REPORTS · 报表",
      empty: "STATE · 空状态",
      error: "STATE · 异常状态",
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

  it("keeps repeated admin table labels synchronized in Chinese and English", () => {
    expect(adminTableCopy).toMatchObject({
      name: "NAME · 姓名",
      employeeNo: "EMP NO · 工号",
      department: "DEPT · 部门",
      score: "SCORE · 得分",
      totalCount: "TOTAL · 总数",
      status: "STATUS · 状态",
    });
  });

  it("maps API enum values to user-facing labels", () => {
    expect(formatExamStatus("active")).toBe("PUBLISHED · 已发布");
    expect(formatExamAvailability("not_started")).toBe("NOT OPEN · 未开放");
    expect(formatExamAvailability()).toBe("UNKNOWN · 未知开放状态");
    expect(formatAttemptStatus("submitted")).toBe("SUBMITTED · 已交卷");
    expect(formatAttemptKind("retake")).toBe("RETAKE · 补考");
    expect(formatQuestionTypeLabel("multiple")).toBe("MULTIPLE · 多选");
    expect(formatQuestionStatus("inactive")).toBe("INACTIVE · 停用");
  });

  it("keeps candidate critical action copy distinct", () => {
    expect(candidateActionCopy).toMatchObject({
      returnExamList: "返回考试列表",
      saveAnswer: "保存答案",
      submitExam: "交卷",
    });
  });

  it("keeps import labels tied to the target object", () => {
    expect(importCopy.uploadQuestionBank).toBe("上传并校验题库");
    expect(importCopy.uploadRoster).toBe("上传应考名单");
  });

  it("keeps real question numbering in question-level copy", () => {
    expect(formatQuestionEyebrow(3, "单选", 2)).toBe("QUESTION 03 · 单选 · 2 分");
  });
});
