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

- `/api/exams/active` 需要 `X-Candidate-Token`，并只返回当前考生在 `exam_candidate_scope` 内、仍可参加的 `active` 状态考试，按 `id` 排序返回。
- `/api/exams/active` 返回服务端计算的 `availability_status`，用于前端展示未开始、可进入、已结束状态；已提交且无未使用补考授权的考试不会出现在该列表。
- `/api/exams/{exam_id}/start` 已根据冻结题池和 `exam.question_rule` 创建正式考试记录和题目快照，后续题库修改不影响该 attempt。空 `question_rule` 保留旧逻辑：抽取冻结题池中的全部题目。
- `available_from` / `available_until` 只限制新开考；已有 `in_progress` attempt 可继续恢复，并按 `started_at + duration_minutes` 到时提交。
- `/api/attempts/{attempt_id}/answers/save` 已将答案暂存到 `exam_attempt_answer`，暂存不暂停倒计时。
- 公开 `/api/attempts/{attempt_id}/submit` 只接受 `submit_type = "manual"`；`auto` 仅由后端 scheduler 内部调用 service。
- `/api/attempts/{attempt_id}/result` 已从已保存的 attempt、快照题和答案读取成绩结果，不重新提交；结果包含 `pass_score` 和 `is_passed`。
- `/api/practice/questions` 使用练习专用响应，不返回正确答案和解析；`/api/practice/answers` 通过 `X-Candidate-Token` 解析考生，提交后才返回正确答案和解析。

## 管理员端

```text
POST /api/admin/login

POST /api/admin/questions/import
GET  /api/admin/imports/templates/questions
GET  /api/admin/imports/templates/candidates
GET  /api/admin/imports/{batch_id}/failure-report
GET  /api/admin/questions
POST /api/admin/questions
PUT  /api/admin/questions/{question_id}
DELETE /api/admin/questions/{question_id}

POST /api/admin/exams
GET  /api/admin/exams
PUT  /api/admin/exams/{exam_id}

POST /api/admin/exams/{exam_id}/candidates/import

GET /api/admin/reports/scores?exam_id={id}
GET /api/admin/reports/question-accuracy?exam_id={id}
GET /api/admin/reports/wrong-questions?exam_id={id}
GET /api/admin/reports/absent-candidates?exam_id={id}&status=not_started
GET /api/admin/reports/export?exam_id={id}
```

说明：

- 管理员登录返回签名 session token；后续管理端接口通过 `X-Admin-Token` 校验，不是完整 RBAC。
- `/api/admin/exams` 的创建、列表和更新已持久化到 `exam` 表；管理端考试编辑页保存 `question_rule` JSON 和开放时间窗口。列表返回 `question_pool_count` 和 `availability_status`。
- 考试从 draft 切换 active 时冻结 `exam_question_pool`；active 后时长和抽题规则不可修改。
- 题库导入接口执行标准 Excel 行级校验，合法行写入 `question` / `question_option`，并写入 `import_batch` 记录失败行号和原因。
- Excel 导入默认限制为 5 MiB、5000 行数据、1 个工作表；超限会返回 400 级业务错误，限制可通过后端环境变量调整。
- `/api/admin/imports/{batch_id}/failure-report` 返回失败报告 Excel，包含批次元信息和失败明细；缺失批次返回 404，无失败行时仍返回空明细 sheet。
- 模板下载接口返回标准 Excel 模板，`Content-Disposition` 使用 `filename*` 兼容中文文件名。
- 应参人员导入接口按考试写入 `exam_candidate_scope`；有员工号时按员工号复用已有人员，无员工号时按无员工号姓名复用已有人员，缺失身份或非法状态按行记录失败原因。
- 报表统计查询已使用真实 SQL；成绩、题目正确率、错题、参考状态和导出均支持 `exam_id` 过滤。省略 `exam_id` 时保留全局视图。
