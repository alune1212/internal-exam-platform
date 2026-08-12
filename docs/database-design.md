# Database Design

## 设计原则

- PostgreSQL 作为第一阶段唯一关系数据库。
- 时间字段使用 timezone-aware datetime。
- 历史考试结果必须基于考试题目快照，不受题库后续修改影响。
- `question_rule` 使用 JSON 字段保存抽题规则和固定试卷来源；不新增抽题规则表。

## 核心表

### candidate（平台账号兼容表）

该表保留 `candidate` 名称和既有 `candidate_id` 外键，以兼容 attempt、练习、学习和审计历史；公开语义是平台账号，而不是全局考试名单。

关键字段：`id`、`name`（公开为 `display_name`）、`email`、`status`、`created_at`、`updated_at`。

约束和索引：

- `email` 必填、trim + lowercase 规范化、大小写不敏感唯一；不做 plus-address、点号或供应商别名折叠。
- `status` 只能是 `pending`、`active`、`inactive`；`pending` 可无显示名称，`active`/`inactive` 必须有非空显示名称。
- `name`、`email`、`status` 建索引；账号目录按规范化邮箱、显示名称和状态搜索。
- 显示名称可由用户自助编辑；规范化邮箱只读，不提供改邮箱、密码或物理删除。inactive 账号保持邮箱唯一并保留历史。
- 旧的全局人员/组织/出席字段已从当前 schema、API 和报表合同移除；只可在不可变历史迁移或显式迁移预检 fixture 中出现。

### candidate_login_challenge

邮箱 OTP 登录/注册 challenge 表。challenge 绑定规范化邮箱，可选关联已存在账号；未知邮箱不再依赖 sentinel 行。

关键字段：`id`、`email`、可选 `candidate_id`、`delivery_channel`、`otp_hash`、`expires_at`、`consumed_at`、`attempt_count`、`request_ip_hash`、短时注册完成凭据 verifier、`created_at`、`updated_at`。

约束和索引：

- `email` 保存规范化值；按 `email`、`expires_at`、`(email, consumed_at)` 建索引，供同邮箱未消费 challenge 失效、过期清理和验证。
- OTP 为六位数字，十分钟有效、单次使用、最多五次校验；重新申请会让同邮箱未消费 challenge 失效，发送冷却 60 秒。
- 注册完成凭据仅保存 hash，短时有效且单次使用；challenge、凭据、token、SMTP secret 不写日志。
- 发送限制同时按规范化邮箱、请求来源 hash 和全局窗口计算；进程重启不能绕过限制。

说明：

- active 账号验证后直接返回签名四小时 token；pending 或新邮箱验证后只返回注册完成凭据，填写显示名称后才激活并签发 token；inactive 账号验证后返回账号不可用，不可借此创建替代账号。

### question

题目主表。

关键字段：`id`、`question_type`、`stem`、`analysis`、`category_1`、`category_2`、`difficulty`、`score`、`status`、`source`、`source_no`、`remark`、`created_at`、`updated_at`。

索引：

- `question_type`
- `status`
- `(question_type, status)`
- `(category_1, category_2)`

### question_option

题目选项表。

关键字段：`id`、`question_id`、`label`、`content`、`is_correct`、`sort_order`、`created_at`、`updated_at`。

约束：

- `(question_id, label)` 唯一。
- 删除题目时级联删除选项。

### exam

考试配置表。

关键字段：`id`、`title`、`description`、`duration_minutes`、`question_rule`、`status`、`show_answer_after_submit`、`show_ranking`、`available_from`、`available_until`、`created_at`、`updated_at`。

`question_rule` 当前支持固定 50 题试卷规则：

```json
{
  "question_count": 50,
  "total_score": 100,
  "pass_score": 60,
  "mode": "fixed_paper",
  "type_counts": { "single": 30, "multiple": 10, "judge": 10 }
}
```

说明：

- 固定试卷按 `question_count`、`type_counts` 和 active 题库抽取题干去重的等价试卷。
- 固定试卷规则必须显式提供正整数 `question_count`、正整数 `total_score`，且 `type_counts.single`、`type_counts.multiple`、`type_counts.judge` 为非负整数并合计等于 `question_count`。
- 固定试卷分值按 `total_score / question_count` 均分为整数；不能整除时余数按试卷顺序分配到前若干题。
- 空 `{}` 保留旧行为：开始考试时抽取全部 active 题目。
- `available_from` / `available_until` 只限制新开考；已有 `in_progress` attempt 仍按 `started_at + duration_minutes` 恢复和到时提交。
- draft 切换 active 时冻结该考试题池；active 后 `duration_minutes` 和 `question_rule` 不允许修改。
- 已生成的 attempt 仍以 `exam_attempt_question` 快照为准，不受后续 `question_rule` 或题库修改影响。

### exam_question_pool

考试发布后的冻结题池表。

关键字段：`id`、`exam_id`、`question_id`、`sort_order`、`created_at`。

说明：

- 考试从 draft 发布到 active 时，从当时 active 题库写入本表。
- 正式开始考试时先从本表取题，再按 `question_rule` 抽取等价试卷。
- 保留 `exam_attempt_question` 快照机制；历史 attempt 仍以快照为准。

### exam_attempt

考试记录主表。

关键字段：`id`、`exam_id`、`candidate_id`、`status`、`started_at`、`submitted_at`、`submit_type`、`score`、`total_score`、`correct_count`、`wrong_count`、`duration_seconds`、`attempt_no`、`attempt_kind`、`paper_seed`、`created_at`、`updated_at`。

状态建议：

- `in_progress`
- `submitted`
- `auto_submitted`

说明：

- `attempt_no` 和 `attempt_kind` 区分首次考试与补考；默认首次 attempt 使用 `initial`，补考授权消耗后创建 `retake` attempt。
- 报表和名单页以该考试 scope 内交卷时间最靠后的有效 attempt 作为当前参考状态；作废 attempt 不计入正常聚合，但保留 incident 证据。

### exam_attempt_question

考试题目快照表。

关键字段：`id`、`attempt_id`、`original_question_id`、`question_type`、`stem_snapshot`、`options_snapshot`、`correct_answer_snapshot`、`analysis_snapshot`、`score`、`sort_order`、`created_at`、`updated_at`。

快照原因：

- 后续题库修改不能影响历史考试结果。
- 成绩复核必须能还原当时题干、选项、答案、解析和分值。

### exam_attempt_answer

考试答案表。

关键字段：`id`、`attempt_question_id`、`selected_answer`、`is_correct`、`score_awarded`、`answered_at`、`updated_at`。

约束：

- `attempt_question_id` 唯一，每道快照题只有一条当前答案。

### practice_answer

练习记录表。

关键字段：`id`、`candidate_id`、`question_id`、`selected_answer`、`is_correct`、`practiced_at`。

说明：

- 练习提交通过 `X-Candidate-Token` 解析当前 active 用户，不接受请求体里的 `candidate_id`。
- 练习题列表在提交前不返回正确答案或解析；提交响应只向当前已认证用户返回该次作答的对错、正确答案、解析和选项对比。
- 每次提交都插入新的不可变记录；重做不会更新或删除旧记录。错题复习按用户账号和题目聚合这些记录，最后一次答对时显示“已掌握”。

### learning_video

学习视频元数据表；视频文件本体保存在本地媒体目录，不写入数据库。

关键字段：`id`、`title`、`description`、`original_filename`、`storage_key`、`content_type`、`file_size_bytes`、`duration_seconds`、`completion_threshold_percent`、`status`、`uploaded_at`、`created_at`、`updated_at`。

约束和索引：

- `storage_key` 唯一；服务端生成不透明 key，不能直接使用用户上传文件名作为路径。
- `status` 建索引，状态为 `draft`、`published`、`archived`。
- 默认完成阈值为 90。

说明：

- 只有 `published` 视频会展示给 active 用户。
- `archived` 视频不再出现在用户学习列表，但管理员报表仍可统计其历史学习记录。
- 本地媒体目录应与 PostgreSQL 数据库一起备份，否则恢复后元数据和视频文件会不一致。

### learning_video_progress

用户的视频学习进度表。

关键字段：`id`、`video_id`、`candidate_id`、`last_position_seconds`、`watched_seconds`、`completion_percent`、`watched_intervals`、`completed_at`、`last_heartbeat_at`、`created_at`、`updated_at`。

约束和索引：

- `(video_id, candidate_id)` 唯一，每个用户对每个视频只有一条进度记录。
- `video_id` 删除时级联删除对应进度。
- `candidate_id`、`video_id`、`completed_at` 和 `last_heartbeat_at` 建索引，供学习报表使用。

说明：

- `watched_intervals` 使用 JSON 保存去重后的观看区间，例如 `[{"start": 0, "end": 30}]`。
- 服务端合并重叠区间，并限制单次心跳可计入长度，避免拖动跳转或重复心跳虚增完成度。
- 学习进度独立于 `exam_attempt`、`practice_answer` 和正式考试报表；完成视频不改变考试 scope、成绩或排名。

### import_batch

导入批次表。

关键字段：`id`、`import_type`、`file_name`、`total_count`、`success_count`、`failed_count`、`status`、`error_report`、`created_at`。

说明：

- 题库导入和单场考试名单导入均写入本表；不再存在独立的全局账号/人员导入批次。
- 失败报告下载基于本表生成 Excel，包含导入类型、文件名、总数、成功数、失败数、生成时间和逐行失败原因。

### exam_candidate_scope

考试应考名单范围表。

关键字段：`id`、`exam_id`、`candidate_id`、`roster_email`、`roster_name`、`department`、`position`、`exam_group`、`roster_remark`、`invitation_status`、`last_invitation_attempt_at`、`invitation_sent_at`、`invitation_error_class`、`invitation_claimed_at`、`invitation_claim_owner`、`created_at`、`updated_at`。

约束：

- `(exam_id, candidate_id)` 和 `(exam_id, roster_email)` 唯一；`roster_email` trim + lowercase 且 `roster_name` 非空。
- 只有 scope 内关联的 active 账号才能发现、开始、恢复或读取对应正式考试；pending scope 可在完成注册后使用，inactive 账号必须由管理员重新激活。
- 发布前名单可编辑；发布事务同时冻结 roster snapshot 和 exam question pool，之后不允许增删改 scope identity。
- `invitation_status` 只能为 `not_sent`、`sent`、`failed`。发布不会自动发送邮件，管理员必须显式执行 initial send；resend 只接受 `failed`。

说明：

- `roster_name`、`roster_email` 和组织字段是正式报表、出席、排名、incident、retake 和 Excel 导出的冻结身份；账号显示名称变化不会改写它们。
- 邀请链接只包含同源考试回跳路径，不含 token、OTP、邀请码、scope id 或其他授权凭据。

### exam_retake_grant

补考授权表。

关键字段：`id`、`exam_id`、`candidate_id`、`used_attempt_id`、`used_at`、`created_at`、`updated_at`。

说明：

- 管理员可为单场考试内的应考人员创建补考授权。
- 未使用授权会让已交卷人员重新出现在可参加考试列表；开始补考时写入 `used_attempt_id` 和 `used_at`。
- 补考 attempt 仍从发布时冻结题池按 `question_rule` 生成等价试卷，并继续使用题目快照。
