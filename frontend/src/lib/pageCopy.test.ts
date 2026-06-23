import { describe, expect, it } from "vitest";

import { adminPageCopy, candidatePageCopy, formatQuestionEyebrow } from "./pageCopy";

describe("pageCopy", () => {
  it("keeps candidate and admin page-level copy free of chapter numbers", () => {
    const pageLevelCopy = [...Object.values(candidatePageCopy), ...Object.values(adminPageCopy)];

    expect(pageLevelCopy).not.toContain("CHAPTER");
    expect(pageLevelCopy.every((label) => !label.includes("CHAPTER"))).toBe(true);
  });

  it("defines admin page-level copy with semantic module labels", () => {
    expect(adminPageCopy).toMatchObject({
      login: "ADMIN · 登录",
      overview: "OVERVIEW · 仪表盘",
      exams: "EXAMS · 考试",
      candidates: "CANDIDATES · 应考人员",
      library: "LIBRARY · 题库",
      reports: "REPORTS · 报表",
      empty: "STATE · 空状态",
      error: "STATE · 异常状态",
    });
  });

  it("keeps real question numbering in question-level copy", () => {
    expect(formatQuestionEyebrow(3, "单选", 2)).toBe("QUESTION 03 · 单选 · 2 分");
  });
});
