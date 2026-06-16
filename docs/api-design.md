# API Design

## 通用规则

- 所有后端路径统一以 `/api` 开头。
- 响应使用统一结构：

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

- 复杂业务逻辑放在 `services/`，路由层只做参数接收和响应组装。

## 系统接口

```text
GET /api/health
```

返回服务健康状态。

## 考试人端

```text
POST /api/candidates/login
GET  /api/practice/questions
POST /api/practice/answers

GET  /api/exams/active
POST /api/exams/{exam_id}/start
GET  /api/attempts/{attempt_id}
POST /api/attempts/{attempt_id}/answers/save
POST /api/attempts/{attempt_id}/submit
GET  /api/attempts/{attempt_id}/result
GET  /api/exams/{exam_id}/ranking
```

说明：

- `/api/exams/active` 已从 `exam` 表读取 `active` 状态考试，按 `id` 排序返回。
- `/api/exams/{exam_id}/start` 已根据 `exam.question_rule` 创建正式考试记录和题目快照，后续题库修改不影响该 attempt。空 `question_rule` 保留旧逻辑：抽取全部 active 题目。
- `/api/attempts/{attempt_id}/answers/save` 已将答案暂存到 `exam_attempt_answer`，暂存不暂停倒计时。
- `/api/attempts/{attempt_id}/submit` 已支持按题目快照自动判分，通过 `submit_type` 区分提前交卷和自动提交。
- `/api/attempts/{attempt_id}/result` 已从已保存的 attempt、快照题和答案读取成绩结果，不重新提交；结果包含 `pass_score` 和 `is_passed`。

## 管理员端

```text
POST /api/admin/login

POST /api/admin/questions/import
GET  /api/admin/imports/templates/questions
GET  /api/admin/imports/templates/candidates
GET  /api/admin/questions
POST /api/admin/questions
PUT  /api/admin/questions/{question_id}
DELETE /api/admin/questions/{question_id}

POST /api/admin/exams
GET  /api/admin/exams
PUT  /api/admin/exams/{exam_id}

POST /api/admin/exams/{exam_id}/candidates/import

GET /api/admin/reports/scores
GET /api/admin/reports/question-accuracy
GET /api/admin/reports/wrong-questions
GET /api/admin/reports/absent-candidates
GET /api/admin/reports/export
```

说明：

- 管理员登录返回签名 session token；后续管理端接口通过 `X-Admin-Token` 校验，不是完整 RBAC。
- `/api/admin/exams` 的创建、列表和更新已持久化到 `exam` 表；管理端考试编辑页直接保存 `question_rule` JSON。
- 题库导入接口执行标准 Excel 行级校验，合法行写入 `question` / `question_option`，并写入 `import_batch` 记录失败行号和原因。
- 模板下载接口返回标准 Excel 模板，`Content-Disposition` 使用 `filename*` 兼容中文文件名。
- 应参人员导入接口按考试写入 `exam_candidate_scope`；有员工号时按员工号复用已有人员，无员工号时按无员工号姓名复用已有人员，缺失身份或非法状态按行记录失败原因。
- 报表统计查询已使用真实 SQL；`/api/admin/reports/export` 返回 Excel 工作簿，包含成绩报表、题目正确率、错题统计、缺考人员四个 sheet。
