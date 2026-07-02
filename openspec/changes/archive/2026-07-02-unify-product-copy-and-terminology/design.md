## Context

The frontend is Chinese-first but uses English eyebrow labels, compact table headers, and code-like status names in several places. `frontend/src/lib/pageCopy.ts` currently centralizes only a small set of page eyebrow strings, while visible copy for candidate flows, admin tables, imports, reports, and layout navigation remains spread across pages and components.

The requested change is cross-cutting across public login pages, candidate workflows, admin navigation, admin list/detail pages, and report pages. It should improve consistency without changing backend API contracts, persistence, auth, exam delivery, scoring, or import/report business behavior.

## Goals / Non-Goals

**Goals:**

- Establish a canonical Chinese-English glossary for repeated product concepts.
- Keep Chinese and English display strings synchronized when both appear in the UI.
- Convert raw API enum/code values into user-facing labels at the render boundary.
- Align critical candidate actions such as answer saving, returning to exam lists, and exam submission.
- Align admin terminology for question bank, exam roster, participants, imports, reports, table headers, loading states, empty states, and error states.
- Align backend-generated report workbooks, import templates, failure-report workbooks, and download filenames with the same glossary.
- Preserve existing Academic Editorial design primitives and page structure.

**Non-Goals:**

- No runtime language switcher or full localization framework.
- No backend API, database schema, auth, scoring, snapshot, import-limit, or report SQL changes.
- No new product surface, LMS feature, complex RBAC, queue, Word import, or anti-cheat feature.
- No broad visual redesign beyond copy and terminology consistency.

## Decisions

1. Treat the UI as Chinese-first bilingual copy, not generic i18n.

   Repeated bilingual labels should be authored as paired product copy such as `QUESTION BANK · 题库` or another canonical pairing, not assembled by unrelated English and Chinese fragments. A full i18n library is unnecessary because the product is not switching locales; the immediate problem is terminology drift.

2. Centralize reusable product terminology and status mappings in typed frontend helpers.

   Expand `frontend/src/lib/pageCopy.ts` or add a nearby copy helper module for canonical page labels, role terms, report column labels, import labels, question type labels, exam status labels, attempt status labels, and availability labels. One-off explanatory paragraphs can remain near the page if they use the same canonical terms.

3. Keep backend/API codes unchanged and format only at display boundaries.

   Types such as `draft`, `active`, `archived`, `single`, `multiple`, `judge`, `not_started`, `in_progress`, and `submitted` remain API values. Components and pages should pass those values through display helpers before rendering them. This avoids DTO mutation and keeps frontend API code aligned with backend contracts.

   Backend-generated Excel artifacts are also display boundaries. They may use product-facing sheet names, column headers, status labels, and filenames, while persisted values, response schemas, and JSON keys such as `row_number` and `reason` remain unchanged.

4. Use role terms by product context.

   Candidate-facing login/current-user copy should use `考试人` with a synchronized English label such as `EXAM TAKER`. Admin-facing individual records should use `应考人员` with a synchronized English label such as `PARTICIPANT`. Exam-scoped lists should use `应考名单` with a synchronized English label such as `ROSTER`. UI copy should avoid visible `候选人` unless it is intentionally referring to a technical API concept in code or tests.

5. Use action labels that describe the actual consequence.

   Candidate navigation that returns to `/exams` should say `返回考试列表`, not `退出考试`, unless it actually ends a session or submits an exam. Answer persistence should use `保存答案`, `正在保存`, `已保存`, and `保存失败`. Exam completion should use `交卷`, `正在交卷`, and `交卷失败`, with any confirmation copy making the consequence explicit.

6. Make tests assert the shared copy contract at high-risk points.

   Unit tests should cover the copy/status helpers. Existing page tests should be updated where they intentionally lock user-facing headings, buttons, table headers, status pills, empty states, and error states. Tests should not assert unstable decorative wording unless that wording is part of the shared product contract.

7. Treat backend exports as administrator-facing product surfaces.

   Report export sheets should use `个人成绩`, `题目正确率`, `错题排行`, and `参考状态`. Export headers should use synchronized compact bilingual labels where that matches the admin report tables. Import templates and failure reports should use `题库导入模板`, `应考名单导入模板`, `失败明细`, and product-facing import type labels, without changing the upload template field keys or import result API fields.

## Risks / Trade-offs

- [Risk] Centralizing too much page-specific text can create a hard-to-read giant copy object. -> Keep reusable terminology/status labels centralized, but allow one-off explanatory paragraphs to stay local while using canonical terms.
- [Risk] English labels such as `CANDIDATE`, `PARTICIPANT`, and `EXAM TAKER` can be interpreted differently. -> Lock the chosen glossary in copy helpers and tests before replacing page text.
- [Risk] Tests may become brittle if they assert every sentence. -> Focus tests on critical actions, status labels, role terms, table headers, and page-level copy that users rely on.
- [Risk] Some backend errors may include older terms such as `考生`. -> Do not rewrite backend messages in this change; handle only frontend-authored fallback/error copy unless an existing frontend mapping can safely normalize a known message.
- [Risk] English compact table headers can save space but reduce clarity. -> Prefer canonical paired or Chinese-primary labels where space allows; use compact English labels only when synchronized with mobile labels and table context.
