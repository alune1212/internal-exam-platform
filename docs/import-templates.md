# Import Templates

## 题库 Excel

第一阶段只支持标准 Excel 导入，不支持 Word 直接解析。

导入预算：

- 默认单个上传文件不超过 5 MiB（`IMPORT_MAX_UPLOAD_BYTES=5242880`）。
- 默认单次导入不超过 5000 行数据（不含表头）。
- 默认只读取第 1 个工作表；包含更多工作表会被拒绝。
- 这些限制同样适用于题库、应参人员和单场考试名单导入。

模板下载：

- 题库模板：`GET /api/admin/imports/templates/questions`
- 应参人员模板：`GET /api/admin/imports/templates/candidates`
- 模板接口返回带表头和示例行的 Excel 文件，并使用 `filename*` 兼容中文文件名。

建议字段：

```text
category_1
category_2
question_type
stem
option_a
option_b
option_c
option_d
option_e
option_f
correct_answer
analysis
difficulty
score
status
source
source_no
remark
```

校验规则：

- 题型不能为空。
- 题干不能为空。
- `question_type` 只能是 `single`、`multiple`、`judge`。
- 单选题只能有一个正确答案。
- 多选题至少两个正确答案。
- 判断题答案只能是 `true` 或 `false`。
- 正确答案必须存在于选项中。
- 分值必须是数字。
- `status` 只能是 `active` 或 `inactive`。

导入结果：

```json
{
  "batch_id": 12,
  "success_count": 10,
  "failed_count": 1,
  "failures": [
    {
      "row_number": 7,
      "reason": "正确答案必须存在于选项中"
    }
  ]
}
```

失败报告：

- 题库导入、应参人员导入、单场考试名单导入都会写入 `import_batch`。
- 可通过管理端导入结果入口或 `GET /api/admin/imports/{batch_id}/failure-report` 下载 Excel。
- 工作簿包含 `导入批次` 和 `失败明细` 两个 sheet。
- `导入批次` 包含导入类型、文件名、总数、成功数、失败数、生成时间。
- `失败明细` 包含 `row_number` 和 `reason`；没有失败行时保留表头。

## 应参人员 Excel

建议字段：

```text
name
employee_no
department
position
phone_suffix
email
exam_group
should_attend
status
remark
```

校验规则：

- `name` 必填。
- `phone_suffix` 用于候选人登录校验，正式名单应填写手机号后四位。
- 有 `employee_no` 时优先使用 `employee_no` 作为唯一识别字段。
- 没有 `employee_no` 时，按“无员工号 + 姓名”识别已有人员。
- 单场考试导入时，已存在人员会被复用并加入当前考试名单，不会因为其他考试已导入同名人员而失败。
- `should_attend` 默认为 true。
- `status` 建议使用 `active` 或 `inactive`。

未参加人员计算：

```text
未参加人员 = 当前考试应考名单 - 已提交考试人员
```
