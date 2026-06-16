# 导入模板下载功能设计

## 目标

在题库导入页面和应考人员页面各增加"下载模板"按钮，点击后下载包含表头和示例数据的 Excel 模板文件，帮助用户正确填写导入数据。

## 架构

后端新增 `template_service.py`，使用 openpyxl 动态生成 Excel 模板。替换现有 `GET /api/admin/imports/templates` 存根端点为两个下载端点。前端在对应导入页面添加下载按钮，通过 blob 下载触发浏览器保存。

## 后端

### 新增文件：`backend/app/services/template_service.py`

两个公开函数：

- `generate_question_template() -> BytesIO` — 生成题库模板
- `generate_candidate_template() -> BytesIO` — 生成人员模板

每个函数：
1. 创建 Workbook，设置 sheet 名称
2. 写入列头行（加粗样式）
3. 写入 1-2 行示例数据
4. 自动调整列宽（基于内容长度）
5. 返回 BytesIO 流

列定义与 `import_service.py` 的验证逻辑保持一致。

#### 题库模板列

| 列头 | 示例数据（单选） | 示例数据（多选） |
|------|-----------------|-----------------|
| category_1 | 安全知识 | 安全知识 |
| category_2 | 消防 | 消防 |
| question_type | single | multiple |
| stem | 灭火器的有效射程是多少米？ | 以下哪些属于灭火的基本方法？ |
| option_a | 3-5 | 隔离法 |
| option_b | 5-8 | 窒息法 |
| option_c | 8-10 | 冷却法 |
| option_d | 10-15 | 抑制法 |
| option_e | | |
| option_f | | |
| correct_answer | A | A,B,C,D |
| analysis | 灭火器有效射程一般为3-5米 | 四种均为灭火基本方法 |
| difficulty | 简单 | 中等 |
| score | 2 | 2 |
| status | active | active |
| source | | |
| source_no | | |
| remark | | |

#### 人员模板列

| 列头 | 示例数据 |
|------|---------|
| name | 张三 |
| employee_no | E1001 |
| department | 综合管理部 |
| position | 工程师 |
| phone_suffix | 1234 |
| email | zhangsan@example.com |
| exam_group | A组 |
| should_attend | true |
| status | active |
| remark | |

### 修改文件：`backend/app/api/imports.py`

替换存根端点为两个下载端点：

```python
@router.get("/templates/questions")
def download_question_template():
    stream = template_service.generate_question_template()
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="题库导入模板.xlsx"'},
    )

@router.get("/templates/candidates")
def download_candidate_template():
    stream = template_service.generate_candidate_template()
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="应考人员模板.xlsx"'},
    )
```

路径：
- `GET /api/admin/imports/templates/questions`
- `GET /api/admin/imports/templates/candidates`

需要 admin 认证（通过 router 级别的 `require_admin` 依赖）。

### 删除

- 删除 `list_import_templates` 存根函数

## 前端

### 修改文件：`frontend/src/api/imports.ts`

新增函数：

```typescript
export async function downloadImportTemplate(type: "questions" | "candidates"): Promise<void> {
  const response = await fetch(`/api/admin/imports/templates/${type}`, {
    headers: { "X-Admin-Token": getAdminToken() ?? "" },
  });
  if (!response.ok) throw new Error("下载失败");
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = type === "questions" ? "题库导入模板.xlsx" : "应考人员模板.xlsx";
  a.click();
  URL.revokeObjectURL(url);
}
```

### 修改文件：`frontend/src/pages/admin/QuestionImportPage.tsx`

在文件上传区域上方增加下载模板按钮：

```tsx
<Button variant="outline" size="sm" onClick={() => downloadImportTemplate("questions")}>
  <Download data-icon="inline-start" />
  下载模板
</Button>
```

### 修改文件：`frontend/src/pages/admin/ExamCandidatesPage.tsx`

在文件上传区域增加下载人员模板按钮（仅在 draft 状态时显示，与上传按钮并排）：

```tsx
<Button variant="outline" size="sm" onClick={() => downloadImportTemplate("candidates")}>
  <Download data-icon="inline-start" />
  下载人员模板
</Button>
```

## 测试

### 后端

`backend/app/tests/test_template_service.py`：
- 验证题库模板生成的 workbook 包含正确列头
- 验证人员模板生成的 workbook 包含正确列头
- 验证示例数据行数和内容正确
- 验证 question_type 示例值合法（single/multiple）
- 验证 correct_answer 格式正确

### 前端

在 `P0Pages.test.tsx` 中：
- 题库导入页面渲染"下载模板"按钮
- 应考人员页面渲染"下载人员模板"按钮
