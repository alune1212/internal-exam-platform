# Import Templates

## 题库 Excel

第一阶段只支持标准 Excel 导入，不支持 Word 直接解析。

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
- 有 `employee_no` 时优先使用 `employee_no` 作为唯一识别字段。
- 没有 `employee_no` 时，第一版按姓名唯一校验。
- `should_attend` 默认为 true。
- `status` 建议使用 `active` 或 `inactive`。

未参加人员计算：

```text
未参加人员 = 应参加人员 - 已提交考试人员
```
