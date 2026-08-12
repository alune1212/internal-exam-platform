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

## 用户与应考人员端

```text
POST /api/candidates/login
POST /api/candidates/login/verify
POST /api/candidates/register/complete
GET  /api/account/profile
PATCH /api/account/profile
GET  /api/practice/questions
POST /api/practice/answers
GET  /api/practice/wrong-questions?category_1=&category_2=&mastered=

GET  /api/learning/videos
GET  /api/learning/videos/{video_id}
POST /api/learning/videos/{video_id}/progress

GET  /api/exams/active
POST /api/exams/{exam_id}/start
GET  /api/attempts/{attempt_id}
POST /api/attempts/{attempt_id}/answers/save
POST /api/attempts/{attempt_id}/submit
POST /api/attempts/{attempt_id}/takeover
GET  /api/attempts/{attempt_id}/result
```

说明：

- `/api/candidates/login` 只接受规范化 `email`，返回统一 `CandidateLoginChallengeResponse` 信封（`challenge_id` / `expires_at` / `resend_available_at`），不返回 token。任意语法有效邮箱都可申请；active、pending、未知和 inactive 邮箱走同一响应与发送边界，不通过姓名或旧名单字段枚举账号。
- `/api/candidates/login/verify` 需要 `challenge_id` 和六位 `otp`；验证码十分钟有效、单次使用、最多五次尝试。active 账号返回 `outcome=authenticated` 和四小时 token；新邮箱或 pending 账号返回短时、单次 `outcome=registration_required` 凭据，必须调用 `/api/candidates/register/complete` 提交非空 `display_name` 后才创建/激活账号并签发 token；inactive 账号返回稳定 `outcome=account_unavailable`，不能绕过管理员激活。OTP verifier、注册凭据、token 和 SMTP secret 不落盘明文。
- `/api/candidates/register/complete` 只接受注册完成凭据和 `display_name`；凭据过期、重放或空名称返回可操作错误，不创建 token。`GET/PATCH /api/account/profile` 只读规范化 email、编辑 display name，不提供换邮箱、密码、记住我或物理删除。
- `/api/candidates/login`、`/api/candidates/login/verify` 和 `/api/admin/login` 带应用层限流，超过阈值返回 429。
- OTP 发送同时按规范化邮箱、请求来源 hash 和全局窗口限制，默认六位/十分钟/五次/60 秒冷却；进程重启不能清空持久化窗口。四小时 token 只放 session-scoped 浏览器状态。
- `/api/exams/active` 需要 active 账号的 `X-Candidate-Token`，并返回当前账号在 `exam_candidate_scope` 内的已发布考试，即使尚未到 `available_from`；响应包含 scope 冻结的 roster identity、`availability_status` 和 opening time。未受邀用户、inactive/pending 未完成用户不能发现正式考试。
- `/api/exams/active` 返回服务端计算的 `availability_status`，用于前端展示未开始、可进入、已结束状态；已交卷且无未使用补考授权的考试不会出现在该列表。
- `/api/exams/{exam_id}/start` 已根据冻结题池和 `exam.question_rule` 创建正式考试记录和题目快照，后续题库修改不影响该 attempt。空 `question_rule` 保留旧逻辑：抽取冻结题池中的全部题目。
- 新开考从 `available_from` 开始，并在 `available_from + 15 分钟` 或更早的 `available_until` 关闭；已有 `in_progress` attempt 可继续恢复，并按 `started_at + duration_minutes` 到时交卷。
- start 返回不透明 attempt-session credential；attempt 读取、保存和提交除 `X-Candidate-Token` 外还必须提交 `X-Attempt-Session`。服务端只保存 credential hash 与 generation。
- `/api/attempts/{attempt_id}/answers/save` 携带当前 `answer_revision`，成功后修订号单调递增；旧设备或过期修订返回 409 且不得覆盖服务器新答案。暂存不暂停倒计时。
- `/api/attempts/{attempt_id}/takeover` 只接受新鲜 OTP candidate token，轮换 session generation，但不改变题目快照、已保存答案或截止时间。
- 公开 `/api/attempts/{attempt_id}/submit` 只接受 `submit_type = "manual"`；`auto` 仅由后端 scheduler 内部调用 service。
- `/api/attempts/{attempt_id}/result` 仅允许已交卷或自动交卷的 attempt 读取；立即返回分数、`pass_score` 和 `is_passed`，但在操作员一次性发布前省略正确答案和解析。用户与应考人员端没有排名接口。
- 所有练习接口都需要 `X-Candidate-Token` 并验证当前用户仍为 active；请求体不接受或信任 `candidate_id`。
- `/api/practice/questions` 使用提交前专用响应，不返回正确答案或解析。
- `/api/practice/answers` 每次调用都新增一条不可变记录，并返回该次提交的 `is_correct`、标准化 `correct_answer`、`analysis` 和逐选项 `option_comparison`。
- `/api/practice/wrong-questions` 只聚合当前用户的错误历史，支持 `category_1`、`category_2`、`mastered` 筛选；当前掌握状态由该题最后一次练习是否正确得出，历史错误不会删除。
- `/api/learning/videos` 和 `/api/learning/videos/{video_id}` 需要 active 账号的 `X-Candidate-Token`，只返回 `published` 学习视频及当前用户的学习进度。
- `/api/learning/videos/{video_id}/progress` 接收当前播放位置和本次观看区间；服务端会合并区间、去重并限制单次可计入长度，完成度达到 90% 时写入 `completed_at`。
- 视频学习进度不参与考试资格判断，不影响 `/api/exams/active`、考试开始、交卷、评分、排名或练习接口。

## 管理员端

```text
POST /api/admin/login

POST /api/admin/questions/import
GET  /api/admin/imports/templates/questions
GET  /api/admin/imports/{batch_id}/failure-report
GET  /api/admin/questions
POST /api/admin/questions
PUT  /api/admin/questions/{question_id}
DELETE /api/admin/questions/{question_id}

POST /api/admin/exams
GET  /api/admin/exams
PUT  /api/admin/exams/{exam_id}
GET  /api/admin/exams/{exam_id}/publication-readiness
POST /api/admin/exams/{exam_id}/publish

POST /api/admin/exams/{exam_id}/candidates/import
GET  /api/admin/exams/{exam_id}/candidates/template
GET  /api/admin/exams/{exam_id}/candidates
DELETE /api/admin/exams/{exam_id}/candidates/{candidate_id}
POST /api/admin/exams/{exam_id}/candidates/invitations/send
POST /api/admin/exams/{exam_id}/candidates/invitations/resend-failed
POST /api/admin/exams/{exam_id}/candidates/{candidate_id}/retake-grants
POST /api/admin/exams/{exam_id}/result-details/release
POST /api/admin/exams/{exam_id}/attempts/{attempt_id}/void
GET  /api/admin/exams/{exam_id}/incidents
POST /api/admin/exams/{exam_id}/retakes/preview
POST /api/admin/exams/{exam_id}/retakes/apply
POST /api/admin/exams/{exam_id}/evidence-bundle

GET  /api/admin/accounts?search=&status=&limit=&offset=
PATCH /api/admin/accounts/{candidate_id}/status
POST /api/admin/accounts/{candidate_id}/activate
POST /api/admin/accounts/{candidate_id}/deactivate

GET  /api/admin/operations/snapshot
GET  /api/admin/operations/session-closure-readiness
GET  /api/admin/operations/retention/preview
POST /api/admin/operations/retention/archive
POST /api/admin/operations/retention/delete

GET /api/admin/reports/scores?exam_id={id}
GET /api/admin/reports/question-accuracy?exam_id={id}
GET /api/admin/reports/wrong-questions?exam_id={id}
GET /api/admin/reports/absent-candidates?exam_id={id}&status=not_started
GET /api/admin/reports/export?exam_id={id}

POST /api/admin/learning/videos
GET  /api/admin/learning/videos
PUT  /api/admin/learning/videos/{video_id}
POST /api/admin/learning/videos/{video_id}/publish
POST /api/admin/learning/videos/{video_id}/archive
GET  /api/admin/learning/reports?video_id={id}&status=completed
GET  /api/admin/learning/reports/export?video_id={id}&status=completed
```

说明：

- 主/备具名操作员登录返回四小时签名 session token；后续管理端接口通过 `X-Admin-Token` 校验。两者权限相同、备份账号默认禁用，不是完整 RBAC。
- 发布前先读取 authoritative publication readiness；发布请求必须精确确认考试标题，服务在同一事务内重跑阻断项后才冻结题池。
- 解析发布要求全部 attempt 已 terminal 和精确确认，只能执行一次且不可撤销。作废保留快照、答案、时间与审计证据，并从普通成绩、排名和参考统计中排除。
- 批量补考必须先 preview，再携带 scope participant ID、preview fingerprint、影响选项、理由和精确标题 apply；每位应考人员至多保留一个未使用授权。
- operations snapshot 只供 loopback 管理入口读取，汇总版本、迁移、服务/worker、锁、磁盘、备份、第二副本、恢复、保留和安全扫描状态。
- 保留删除采用 preview -> archive -> verified paired backup -> explicit IDs/confirmation 的两阶段门禁，不允许直接数据库删除。
- `/api/admin/exams` 的创建、列表和更新已持久化到 `exam` 表；管理端考试编辑页保存 `question_rule` JSON 和开放时间窗口。列表返回 `question_pool_count` 和 `availability_status`。
- 考试从 draft 切换 active 时冻结 `exam_question_pool`；active 后时长和抽题规则不可修改。
- 题库导入接口执行标准 Excel 行级校验，合法行写入 `question` / `question_option`，并写入 `import_batch` 记录失败行号和原因。
- Excel 导入默认限制为 5 MiB、5000 行数据、1 个工作表；超限会返回 400 级业务错误，限制可通过后端环境变量调整。
- `/api/admin/imports/{batch_id}/failure-report` 返回失败报告 Excel，包含批次元信息和失败明细；缺失批次返回 404，无失败行时仍返回空明细 sheet。
- 模板下载接口返回标准 Excel 模板，`Content-Disposition` 使用 `filename*` 兼容中文文件名。
- 单场应考名单导入只接受规范化 `email`、`candidate_name` 和可选 department/position/exam_group/remark；按邮箱复用 active/pending 账号或创建不能登录的 pending 账号，所有身份只写入当前 exam scope。独立全局账号/人员导入与模板已移除。
- 缺失/非法/重复邮箱、inactive 账号、旧字段行和无法补齐冻结身份的行按行失败，不按姓名合并、不部分授予权限；导入仍受 5 MiB、5000 行、1 sheet 限制并生成 failure report。
- 单场考试名单列表返回冻结 roster identity、当前参考 attempt、成绩、`has_unused_retake_grant` 与 `invitation_status`，供管理端展示。发布事务同时冻结 roster 和题池；发布后不能编辑或删除 scope。
- 发布后邀请必须由管理员显式调用 initial-send；每行记录 `not_sent|sent|failed` 和非敏感错误分类。failed-only resend 只选择 `failed`，不会重发或降级 `sent`；邀请链接只带同源 `returnTo`，没有 token/OTP/invite code/scope id。
- 单场考试名单删除接口只移除未发布考试的 draft `exam_candidate_scope` 记录，不删除全局平台账号；已发布名单 immutable。
- 补考授权接口创建一条未使用的 `exam_retake_grant`；已交卷应考人员存在未使用授权时会重新出现在 active exam 列表，开始考试时生成 `attempt_kind = "retake"` 的新 attempt 并消耗授权。
- 报表统计查询已使用真实 SQL；成绩、题目正确率、错题、参考状态、排名和导出均支持 `exam_id` 过滤，省略时保留全局视图。正式行始终从对应 scope 读取冻结 roster name/email/organization，账号 profile/deactivation 不改写历史；旧人员/全局 attendance 字段不出现在 JSON、筛选、表头或 Excel。作废 attempt 排除正常聚合，保留 incident/evidence。
- `/api/admin/learning/videos` 上传接口使用 multipart form，字段为 `title`、可选 `description`、`duration_seconds` 和 `file`；当前允许 `video/mp4` 与 `video/webm`，默认最大 500 MiB。
- 学习视频上传后为 `draft`；发布后 active 用户可见，归档后用户不可见。管理员仍可在列表和学习报表中看到视频状态。
- 学习报表按 active 用户账号和学习视频生成行，可用 `video_id` 与 `status=not_started|in_progress|completed` 过滤，并支持 Excel 导出。
- 本地视频文件通过 Nginx `/media/learning/` 提供播放，API 只返回播放 URL 和元数据，不把原始文件名作为存储路径。
