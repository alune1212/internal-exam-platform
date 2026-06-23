# Database Design

## 设计原则

- PostgreSQL 作为第一阶段唯一关系数据库。
- 时间字段使用 timezone-aware datetime。
- 历史考试结果必须基于考试题目快照，不受题库后续修改影响。
- `question_rule` 使用 JSON 字段保存抽题规则和固定试卷来源；不新增抽题规则表。

## 核心表

### candidate

考试人和应参人员表。

关键字段：`id`、`name`、`employee_no`、`department`、`position`、`phone_suffix`、`email`、`exam_group`、`should_attend`、`status`、`remark`、`created_at`、`updated_at`。

约束和索引：

- `employee_no` 唯一，可空。
- `name`、`exam_group`、`status` 建索引。
- 没有员工号时的姓名唯一校验由 service 层处理。

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

- 练习提交通过 `X-Candidate-Token` 解析当前考生，不接受请求体里的 `candidate_id`。
- 练习题列表和提交响应都不返回正确答案、解析、对错或判分结果；判分结果只保存在服务端记录中。

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
- 仅名单内 active 且应参加人员可以开始对应考试。

### exam_retake_grant

补考授权表。

关键字段：`id`、`exam_id`、`candidate_id`、`used_attempt_id`、`used_at`、`created_at`、`updated_at`。
