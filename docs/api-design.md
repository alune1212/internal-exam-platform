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

- `/api/exams/{exam_id}/start` 的目标语义是创建正式考试记录和题目快照；第一阶段已保留 route/schema/service 边界，持久化逻辑后续补齐。
- `/api/attempts/{attempt_id}/answers/save` 的目标语义是自动暂存答案，不暂停倒计时。
- `/api/attempts/{attempt_id}/submit` 的目标语义是支持提前交卷和自动提交，通过 `submit_type` 区分。

## 管理员端

```text
POST /api/admin/login

POST /api/admin/questions/import
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

- 第一阶段管理员登录是简单口令占位，不是完整权限系统。
- 题库导入接口执行标准 Excel 行级校验，合法行写入 `question` / `question_option`，并写入 `import_batch` 记录失败行号和原因。
- 应参人员导入接口执行标准 Excel 行级校验，合法行写入 `candidate`，并写入 `import_batch` 记录失败行号和原因。
- 报表导出和统计查询第一阶段保留路由和 schema，后续补真实 SQL 查询和文件输出。
