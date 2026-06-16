# 导入模板下载功能 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在题库导入和应考人员页面各增加"下载模板"按钮，后端动态生成含表头和示例数据的 Excel 模板文件。

**Architecture:** 后端新增 `template_service.py` 使用 openpyxl 生成模板 Excel，`imports.py` 替换存根端点为两个 StreamingResponse 下载端点。前端在对应页面添加下载按钮，通过 fetch + blob 触发浏览器下载。

**Tech Stack:** openpyxl, FastAPI StreamingResponse, React, TypeScript

---

## 文件清单

| 操作 | 文件 | 职责 |
|------|------|------|
| 创建 | `backend/app/services/template_service.py` | 模板生成逻辑 |
| 创建 | `backend/app/tests/test_template_service.py` | 模板生成测试 |
| 修改 | `backend/app/api/imports.py` | 替换存根端点为下载端点 |
| 修改 | `frontend/src/api/imports.ts` | 新增 downloadImportTemplate 函数 |
| 修改 | `frontend/src/pages/admin/QuestionImportPage.tsx` | 添加下载模板按钮 |
| 修改 | `frontend/src/pages/admin/ExamCandidatesPage.tsx` | 添加下载人员模板按钮 |

---

### Task 1: 后端模板生成 Service + 测试

**Files:**
- Create: `backend/app/tests/test_template_service.py`
- Create: `backend/app/services/template_service.py`

- [ ] **Step 1: 写失败测试**

创建 `backend/app/tests/test_template_service.py`：

```python
from io import BytesIO

from openpyxl import load_workbook

from app.services.template_service import (
    generate_candidate_template,
    generate_question_template,
)


def test_question_template_has_correct_headers() -> None:
    wb = load_workbook(generate_question_template())
    ws = wb.active
    headers = [cell.value for cell in ws[1]]
    assert headers == [
        "category_1",
        "category_2",
        "question_type",
        "stem",
        "option_a",
        "option_b",
        "option_c",
        "option_d",
        "option_e",
        "option_f",
        "correct_answer",
        "analysis",
        "difficulty",
        "score",
        "status",
        "source",
        "source_no",
        "remark",
    ]


def test_question_template_has_two_example_rows() -> None:
    wb = load_workbook(generate_question_template())
    ws = wb.active
    assert ws.max_row == 3  # 1 header + 2 examples
    # first example: single choice
    assert ws.cell(2, 3).value == "single"  # question_type
    assert ws.cell(2, 11).value == "A"  # correct_answer
    # second example: multiple choice
    assert ws.cell(3, 3).value == "multiple"
    assert ws.cell(3, 11).value == "A,B,C,D"


def test_candidate_template_has_correct_headers() -> None:
    wb = load_workbook(generate_candidate_template())
    ws = wb.active
    headers = [cell.value for cell in ws[1]]
    assert headers == [
        "name",
        "employee_no",
        "department",
        "position",
        "phone_suffix",
        "email",
        "exam_group",
        "should_attend",
        "status",
        "remark",
    ]


def test_candidate_template_has_one_example_row() -> None:
    wb = load_workbook(generate_candidate_template())
    ws = wb.active
    assert ws.max_row == 2  # 1 header + 1 example
    assert ws.cell(2, 1).value == "张三"
    assert ws.cell(2, 2).value == "E1001"


def test_question_template_returns_bytesio() -> None:
    result = generate_question_template()
    assert isinstance(result, BytesIO)
    assert result.tell() == 0  # read position at start


def test_candidate_template_returns_bytesio() -> None:
    result = generate_candidate_template()
    assert isinstance(result, BytesIO)
    assert result.tell() == 0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest app/tests/test_template_service.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: 实现 template_service.py**

创建 `backend/app/services/template_service.py`：

```python
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

QUESTION_HEADERS = [
    "category_1",
    "category_2",
    "question_type",
    "stem",
    "option_a",
    "option_b",
    "option_c",
    "option_d",
    "option_e",
    "option_f",
    "correct_answer",
    "analysis",
    "difficulty",
    "score",
    "status",
    "source",
    "source_no",
    "remark",
]

QUESTION_EXAMPLES = [
    [
        "安全知识",
        "消防",
        "single",
        "灭火器的有效射程是多少米？",
        "3-5",
        "5-8",
        "8-10",
        "10-15",
        None,
        None,
        "A",
        "灭火器有效射程一般为3-5米",
        "简单",
        2,
        "active",
        None,
        None,
        None,
    ],
    [
        "安全知识",
        "消防",
        "multiple",
        "以下哪些属于灭火的基本方法？",
        "隔离法",
        "窒息法",
        "冷却法",
        "抑制法",
        None,
        None,
        "A,B,C,D",
        "四种均为灭火基本方法",
        "中等",
        2,
        "active",
        None,
        None,
        None,
    ],
]

CANDIDATE_HEADERS = [
    "name",
    "employee_no",
    "department",
    "position",
    "phone_suffix",
    "email",
    "exam_group",
    "should_attend",
    "status",
    "remark",
]

CANDIDATE_EXAMPLES = [
    [
        "张三",
        "E1001",
        "综合管理部",
        "工程师",
        "1234",
        "zhangsan@example.com",
        "A组",
        "true",
        "active",
        None,
    ],
]

HEADER_FONT = Font(bold=True)


def _build_workbook(
    sheet_name: str,
    headers: list[str],
    examples: list[list],
) -> BytesIO:
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name

    # header row
    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(1, col_idx, header)
        cell.font = HEADER_FONT

    # example rows
    for row_idx, row_data in enumerate(examples, start=2):
        for col_idx, value in enumerate(row_data, start=1):
            if value is not None:
                ws.cell(row_idx, col_idx, value)

    # auto column width
    for col_idx, header in enumerate(headers, start=1):
        max_len = len(header)
        for row_idx in range(2, len(examples) + 2):
            cell_value = ws.cell(row_idx, col_idx).value
            if cell_value is not None:
                max_len = max(max_len, len(str(cell_value)))
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 4, 40)

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    return stream


def generate_question_template() -> BytesIO:
    return _build_workbook("题库模板", QUESTION_HEADERS, QUESTION_EXAMPLES)


def generate_candidate_template() -> BytesIO:
    return _build_workbook("人员模板", CANDIDATE_HEADERS, CANDIDATE_EXAMPLES)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && uv run pytest app/tests/test_template_service.py -v`
Expected: 6 passed

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/template_service.py backend/app/tests/test_template_service.py
git commit -m "feat: 新增模板生成 service，支持题库和人员 Excel 模板"
```

---

### Task 2: 后端 API 端点替换存根

**Files:**
- Modify: `backend/app/api/imports.py`

- [ ] **Step 1: 替换 imports.py 中的存根端点**

将 `backend/app/api/imports.py` 全部内容替换为：

```python
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.services import template_service

router = APIRouter(prefix="/admin/imports", tags=["admin-imports"])


@router.get("/templates/questions")
def download_question_template() -> StreamingResponse:
    stream = template_service.generate_question_template()
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="题库导入模板.xlsx"'},
    )


@router.get("/templates/candidates")
def download_candidate_template() -> StreamingResponse:
    stream = template_service.generate_candidate_template()
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="应考人员模板.xlsx"'},
    )
```

- [ ] **Step 2: 运行后端测试**

Run: `cd backend && uv run pytest`
Expected: 全部通过

- [ ] **Step 3: 提交**

```bash
git add backend/app/api/imports.py
git commit -m "feat: 替换模板存根端点为 Excel 下载接口"
```

---

### Task 3: 前端下载函数

**Files:**
- Modify: `frontend/src/api/imports.ts`

- [ ] **Step 1: 新增 downloadImportTemplate 函数**

在 `frontend/src/api/imports.ts` 末尾追加：

```typescript
export async function downloadImportTemplate(type: "questions" | "candidates"): Promise<void> {
  const { getAdminToken } = await import("@/lib/adminSession");
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

- [ ] **Step 2: 验证类型检查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 3: 提交**

```bash
git add frontend/src/api/imports.ts
git commit -m "feat: 新增 downloadImportTemplate 前端下载函数"
```

---

### Task 4: 题库导入页面添加下载按钮

**Files:**
- Modify: `frontend/src/pages/admin/QuestionImportPage.tsx`

- [ ] **Step 1: 添加下载按钮**

在 `QuestionImportPage.tsx` 中：

1. 在 lucide-react import 中加入 `Download`：`import { Download, FileUp } from "lucide-react";`
2. 在 imports 中加入 `import { downloadImportTemplate } from "@/api/imports";`
3. 在文件上传区域（`<section>` 开头）的 `<Input>` 之前添加下载按钮：

```tsx
<div className="flex items-center gap-3">
  <Button
    type="button"
    variant="outline"
    size="sm"
    onClick={() => void downloadImportTemplate("questions")}
  >
    <Download data-icon="inline-start" />
    下载模板
  </Button>
  <span className="text-caption text-muted">
    模板格式见 docs/import-templates.md
  </span>
</div>
```

4. 删除原来的 `<p className="text-caption italic text-muted">` 模板提示文字（被上面的按钮行替代）

- [ ] **Step 2: 运行前端测试**

Run: `cd frontend && npm run test -- --run`
Expected: 全部通过

- [ ] **Step 3: 验证类型检查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 4: 提交**

```bash
git add frontend/src/pages/admin/QuestionImportPage.tsx
git commit -m "feat: 题库导入页面添加下载模板按钮"
```

---

### Task 5: 应考人员页面添加下载按钮

**Files:**
- Modify: `frontend/src/pages/admin/ExamCandidatesPage.tsx`

- [ ] **Step 1: 添加下载按钮**

在 `ExamCandidatesPage.tsx` 中：

1. 在 lucide-react import 中加入 `Download`：`import { Download, FileUp, RotateCcw, Trash2 } from "lucide-react";`
2. 在 imports 中加入 `import { downloadImportTemplate } from "@/api/imports";`
3. 在上传按钮右侧添加下载按钮（第 89 行附近的 `<div className="flex flex-col gap-3 md:flex-row md:items-center">` 内部，`<Input>` 之后、上传 `<Button>` 之后）：

```tsx
<Button
  type="button"
  variant="outline"
  size="sm"
  onClick={() => void downloadImportTemplate("candidates")}
>
  <Download data-icon="inline-start" />
  下载人员模板
</Button>
```

- [ ] **Step 2: 运行前端测试**

Run: `cd frontend && npm run test -- --run`
Expected: 全部通过

- [ ] **Step 3: 验证类型检查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 4: 提交**

```bash
git add frontend/src/pages/admin/ExamCandidatesPage.tsx
git commit -m "feat: 应考人员页面添加下载模板按钮"
```

---

### Task 6: 最终验证

- [ ] **Step 1: 运行全部测试**

```bash
cd frontend && npm run test -- --run
cd backend && uv run pytest
```

Expected: 全部通过

- [ ] **Step 2: 运行 lint 和类型检查**

```bash
cd frontend && npm run lint && npx tsc --noEmit
cd backend && uv run ruff check .
```

Expected: 无新增错误
