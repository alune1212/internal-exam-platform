# Database Design

## 设计原则

- PostgreSQL 作为第一阶段唯一关系数据库。
- 时间字段使用 timezone-aware datetime。
- 历史考试结果必须基于考试题目快照，不受题库后续修改影响。
- `question_rule` 使用 JSON 字段保存抽题规则和固定试卷来源；不新增抽题规则表。

## 核心表

### candidate

考试人和应考人员表。

关键字段：`id`、`name`、`employee_no`、`department`、`position`、`phone_suffix`、`email`、`exam_group`、`should_attend`、`status`、`remark`、`created_at`、`updated_at`。

约束和索引：

- `employee_no` 唯一，可空。
- `name`、`exam_group`、`status` 建索引。
- 没有员工号时的姓名唯一校验由 service 层处理。
- 严格考试人登录使用 `name` + `email` + 可选 `employee_no` 创建邮件 OTP challenge；新导入名单必须提供可用 `email`，`phone_suffix` 仅作为保留资料字段。
- `is_login_sentinel`（NOT NULL，默认 `false`）标识考试人登录 sentinel 行；该列建索引，数据库里**必须有且仅有一行** `is_login_sentinel = true`，由迁移 `202607030002_candidate_login_sentinel` 安装。Sentinel 行 `name` 为 `__candidate_login_sentinel__`、`status='inactive'`、`email IS NULL`、`should_attend=false`，**禁止**被加入 `exam_candidate_scope`、被 exam-candidate 导入复用、也**禁止**被操作员删除或重命名——它是未知身份登录请求的兜底 challenge 目标。verify 阶段会拒绝指向 sentinel 的 challenge，因此即使有人猜中 OTP 也无法签发 candidate token。

### candidate_login_challenge

考试人邮件 OTP 登录 challenge 表。

关键字段：`id`、`candidate_id`、`delivery_channel`、`otp_hash`、`expires_at`、`consumed_at`、`attempt_count`、`request_ip_hash`、`created_at`、`updated_at`。

约束和索引：

- `candidate_id` 外键关联 `candidate.id`，删除考试人时级联删除 challenge。
- `candidate_id`、`expires_at`、`(candidate_id, consumed_at)` 建索引，供未消费 challenge 失效、过期清理和登录验证使用。

说明：

- `otp_hash` 只保存验证码 verifier，不保存明文 OTP。
- challenge 短期有效、单次使用，并记录验证码尝试次数。
- 重新请求验证码会让同一考试人的未消费 challenge 失效，再创建新的 challenge。

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
- 报表和名单页以考试人在该考试中交卷时间最靠后的已交卷 attempt 作为当前参考状态。

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

- 练习提交通过 `X-Candidate-Token` 解析当前考试人，不接受请求体里的 `candidate_id`。
- 练习题列表和提交响应都不返回正确答案、解析、对错或判分结果；判分结果只保存在服务端记录中。

### learning_video

学习视频元数据表；视频文件本体保存在本地媒体目录，不写入数据库。

关键字段：`id`、`title`、`description`、`original_filename`、`storage_key`、`content_type`、`file_size_bytes`、`duration_seconds`、`completion_threshold_percent`、`status`、`uploaded_at`、`created_at`、`updated_at`。

约束和索引：

- `storage_key` 唯一；服务端生成不透明 key，不能直接使用用户上传文件名作为路径。
- `status` 建索引，状态为 `draft`、`published`、`archived`。
- 默认完成阈值为 90。

说明：

- 只有 `published` 视频会展示给考试人。
- `archived` 视频不再出现在考试人学习列表，但管理员报表仍可统计其历史学习记录。
- 本地媒体目录应与 PostgreSQL 数据库一起备份，否则恢复后元数据和视频文件会不一致。

### learning_video_progress

考试人的视频学习进度表。

关键字段：`id`、`video_id`、`candidate_id`、`last_position_seconds`、`watched_seconds`、`completion_percent`、`watched_intervals`、`completed_at`、`last_heartbeat_at`、`created_at`、`updated_at`。

约束和索引：

- `(video_id, candidate_id)` 唯一，每个考试人对每个视频只有一条进度记录。
- `video_id` 删除时级联删除对应进度。
- `candidate_id`、`video_id`、`completed_at` 和 `last_heartbeat_at` 建索引，供学习报表使用。

说明：

- `watched_intervals` 使用 JSON 保存去重后的观看区间，例如 `[{"start": 0, "end": 30}]`。
- 服务端合并重叠区间，并限制单次心跳可计入长度，避免拖动跳转或重复心跳虚增完成度。
- 学习进度独立于 `exam_attempt`、`practice_answer` 和考试报表；完成视频不改变考试资格、成绩或排名。

### import_batch

导入批次表。

关键字段：`id`、`import_type`、`file_name`、`total_count`、`success_count`、`failed_count`、`status`、`error_report`、`created_at`。

说明：

- 题库导入、人员导入、单场考试名单导入均写入本表。
- 失败报告下载基于本表生成 Excel，包含导入类型、文件名、总数、成功数、失败数、生成时间和逐行失败原因。

### exam_candidate_scope

考试应考名单范围表。

关键字段：`id`、`exam_id`、`candidate_id`、`created_at`、`updated_at`。

约束：

- `(exam_id, candidate_id)` 唯一。
- 仅名单内 active 且应考人员可以开始对应考试。

### exam_retake_grant

补考授权表。

关键字段：`id`、`exam_id`、`candidate_id`、`used_attempt_id`、`used_at`、`created_at`、`updated_at`。

说明：

- 管理员可为单场考试内的应考人员创建补考授权。
- 未使用授权会让已交卷人员重新出现在可参加考试列表；开始补考时写入 `used_attempt_id` 和 `used_at`。
- 补考 attempt 仍从发布时冻结题池按 `question_rule` 生成等价试卷，并继续使用题目快照。
