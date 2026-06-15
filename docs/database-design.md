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

关键字段：`id`、`title`、`description`、`duration_minutes`、`question_rule`、`status`、`show_answer_after_submit`、`show_ranking`、`created_at`、`updated_at`。

`question_rule` 当前支持固定 50 题试卷规则：

```json
{
  "question_count": 50,
  "total_score": 100,
  "pass_score": 60,
  "mode": "fixed_paper",
  "type_counts": { "single": 30, "multiple": 10, "judge": 10 },
  "fixed_question_ids": [1, 2, 3]
}
```

说明：

- `fixed_question_ids` 在首次开考时生成，后续考生复用同一批原题生成各自的 attempt snapshot。
- 空 `{}` 保留旧行为：开始考试时抽取全部 active 题目。
- 已生成的 attempt 仍以 `exam_attempt_question` 快照为准，不受后续 `question_rule` 或题库修改影响。

### exam_attempt

考试记录主表。

关键字段：`id`、`exam_id`、`candidate_id`、`status`、`started_at`、`submitted_at`、`submit_type`、`score`、`total_score`、`correct_count`、`wrong_count`、`duration_seconds`、`created_at`、`updated_at`。

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

### import_batch

导入批次表。

关键字段：`id`、`import_type`、`file_name`、`total_count`、`success_count`、`failed_count`、`status`、`error_report`、`created_at`。
