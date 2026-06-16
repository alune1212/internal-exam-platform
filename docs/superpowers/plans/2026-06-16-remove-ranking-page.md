# 移除排名页面 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 移除候选人端排名页面及所有相关代码，保留考试提交后的打分/结果页面。

**Architecture:** 从前端到后端逐层清除排名功能：页面组件 → 路由 → 导航 → API 客户端 → 类型 → 后端端点 → Schema → Service → 测试。结果页面（ExamResultPage）保持不变，仅移除其中的"查看排名"链接。数据库 `show_ranking` 列保留不动（不生成迁移）。

**Tech Stack:** React, TypeScript, FastAPI, SQLAlchemy, Pydantic

---

## 文件清单

| 操作 | 文件 | 职责 |
|------|------|------|
| 删除 | `frontend/src/pages/RankingPage.tsx` | 排名页面组件 |
| 修改 | `frontend/src/app/router.tsx` | 移除排名路由 |
| 修改 | `frontend/src/components/layout/TopNav.tsx` | 移除"排名"导航项及 activeExamId 逻辑 |
| 修改 | `frontend/src/components/layout/CandidateLayout.tsx` | 移除 activeExamId 计算和传递 |
| 修改 | `frontend/src/pages/ExamResultPage.tsx` | 移除"查看排名"按钮 |
| 修改 | `frontend/src/api/exams.ts` | 移除 getExamRanking 函数 |
| 修改 | `frontend/src/types/exam.ts` | 移除 RankingRow 类型和 show_ranking 字段 |
| 修改 | `frontend/src/types/attempt.ts` | 移除 show_ranking 字段 |
| 修改 | `backend/app/api/exams.py` | 移除 ranking 端点 |
| 修改 | `backend/app/schemas/exam.py` | 移除 RankingRow schema 和 show_ranking 字段 |
| 修改 | `backend/app/services/exam_service.py` | 移除 get_ranking 函数 |
| 修改 | `frontend/src/pages/P0Pages.test.tsx` | 移除排名相关测试和 mock |
| 修改 | `frontend/src/components/layout/__tests__/TopNav.test.tsx` | 移除排名相关测试 |
| 修改 | `backend/app/tests/test_exam_service.py` | 移除 ranking 测试 |

---

### Task 1: 删除 RankingPage 并移除路由

**Files:**
- Delete: `frontend/src/pages/RankingPage.tsx`
- Modify: `frontend/src/app/router.tsx:11,36`

- [ ] **Step 1: 删除 RankingPage 组件文件**

```bash
rm frontend/src/pages/RankingPage.tsx
```

- [ ] **Step 2: 移除路由中的排名页面**

在 `frontend/src/app/router.tsx` 中：
- 删除第 11 行的 `import { RankingPage } from "@/pages/RankingPage";`
- 删除第 36 行的 `{ path: "exams/:examId/ranking", element: <RankingPage /> },`

修改后 CandidateLayout children 应为：
```tsx
children: [
  { index: true, element: <Navigate to="/login" replace /> },
  { path: "login", element: <LoginPage /> },
  { path: "practice", element: <PracticePage /> },
  { path: "exams", element: <ExamListPage /> },
  { path: "exams/:examId/start", element: <ExamStartPage /> },
  { path: "exams/:examId/taking", element: <ExamTakingPage /> },
  { path: "exams/:examId/result", element: <ExamResultPage /> },
],
```

- [ ] **Step 3: 验证构建通过**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 无错误

- [ ] **Step 4: 提交**

```bash
git add frontend/src/app/router.tsx
git rm frontend/src/pages/RankingPage.tsx
git commit -m "feat: 删除排名页面组件和路由"
```

---

### Task 2: 移除 TopNav 中的排名导航项

**Files:**
- Modify: `frontend/src/components/layout/TopNav.tsx`
- Modify: `frontend/src/components/layout/CandidateLayout.tsx`

- [ ] **Step 1: 清理 TopNav 中的排名相关代码**

在 `frontend/src/components/layout/TopNav.tsx` 中：

1. 删除 `TopNavProps` 中的 `activeExamId` 属性（第 31 行）
2. 删除 `rankingPath` 变量（第 80 行）
3. 从 `navItems` 数组中移除排名项（第 84-89 行），只保留练习和考试两项
4. 删除函数参数中的 `activeExamId` 解构（第 75 行）

修改后 `navItems` 应为：
```tsx
const navItems: NavItem[] = [
  { to: "/practice", label: "练习", mark: "I." },
  { to: "/exams", label: "考试", mark: "II.", end: true },
];
```

修改后函数签名应为：
```tsx
export function TopNav({ candidate, onLogout }: TopNavProps) {
```

修改后类型应为：
```tsx
type TopNavProps = {
  candidate: Candidate | null;
  onLogout: () => void;
};
```

- [ ] **Step 2: 清理 CandidateLayout 中的 activeExamId**

在 `frontend/src/components/layout/CandidateLayout.tsx` 中：

1. 删除第 24-25 行的 `activeExams` query 和 `activeExamId` 变量
2. 从 `<TopNav>` 调用中删除 `activeExamId` prop（第 40 行）
3. 如果 `getActiveExams` 没有其他使用者，删除其 import（第 5 行）

修改后 `<TopNav>` 调用应为：
```tsx
<TopNav candidate={candidate} onLogout={logoutCandidate} />
```

- [ ] **Step 3: 验证构建通过**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 无错误

- [ ] **Step 4: 提交**

```bash
git add frontend/src/components/layout/TopNav.tsx frontend/src/components/layout/CandidateLayout.tsx
git commit -m "feat: 移除导航栏排名入口和 activeExamId 逻辑"
```

---

### Task 3: 移除 ExamResultPage 中的"查看排名"链接

**Files:**
- Modify: `frontend/src/pages/ExamResultPage.tsx:94-99`

- [ ] **Step 1: 删除"查看排名"按钮**

在 `frontend/src/pages/ExamResultPage.tsx` 中，删除第 94-99 行的"查看排名"按钮：

```tsx
// 删除这段
<Button asChild className="w-full bg-canvas text-ink hover:bg-canvas-warm">
  <Link to={`/exams/${examId}/ranking`}>
    查看排名
    <ChevronRight data-icon="inline-end" />
  </Link>
</Button>
```

同时检查文件顶部是否还有 `ChevronRight` 的 import，如无其他使用者则一并删除。

- [ ] **Step 2: 验证构建通过**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 无错误

- [ ] **Step 3: 提交**

```bash
git add frontend/src/pages/ExamResultPage.tsx
git commit -m "feat: 移除结果页的查看排名链接"
```

---

### Task 4: 移除前端排名相关 API 函数和类型

**Files:**
- Modify: `frontend/src/api/exams.ts`
- Modify: `frontend/src/types/exam.ts`
- Modify: `frontend/src/types/attempt.ts`

- [ ] **Step 1: 移除 getExamRanking 函数**

在 `frontend/src/api/exams.ts` 中：
1. 删除 `getExamRanking` 函数（第 28-30 行）
2. 从 import 中删除 `RankingRow`（第 3 行）

- [ ] **Step 2: 移除 RankingRow 类型和 show_ranking**

在 `frontend/src/types/exam.ts` 中：
1. 删除 `RankingRow` 类型定义（第 15-22 行）
2. 删除 `show_ranking` 字段（第 9 行）

- [ ] **Step 3: 移除 attempt.ts 中的 show_ranking**

在 `frontend/src/types/attempt.ts` 中，删除 `show_ranking: boolean` 字段（第 56 行附近，在 `ExamStartResponse` 的嵌套 `exam` 对象中）。

- [ ] **Step 4: 验证构建通过**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 无错误

- [ ] **Step 5: 提交**

```bash
git add frontend/src/api/exams.ts frontend/src/types/exam.ts frontend/src/types/attempt.ts
git commit -m "feat: 移除前端排名 API 函数和 RankingRow 类型"
```

---

### Task 5: 移除后端排名端点、Schema 和 Service

**Files:**
- Modify: `backend/app/api/exams.py`
- Modify: `backend/app/schemas/exam.py`
- Modify: `backend/app/services/exam_service.py`

- [ ] **Step 1: 移除 ranking API 端点**

在 `backend/app/api/exams.py` 中：
1. 删除 `get_ranking` 路由函数（第 40-44 行）
2. 从 import 中删除 `RankingRow`（第 13 行）

- [ ] **Step 2: 移除 RankingRow schema 和 show_ranking 字段**

在 `backend/app/schemas/exam.py` 中：
1. 删除 `RankingRow` 类定义（第 53-59 行）
2. 从 `ExamBase` 中删除 `show_ranking` 字段（第 17 行）
3. 从 `ExamUpdate` 中删除 `show_ranking` 字段（第 31 行）

- [ ] **Step 3: 移除 get_ranking service 函数**

在 `backend/app/services/exam_service.py` 中：
1. 删除 `get_ranking` 函数（第 1010-1050 行附近）
2. 从 import 中删除 `RankingRow`（第 38 行）

- [ ] **Step 4: 运行后端测试**

```bash
cd backend && uv run pytest
```

Expected: 排名相关测试失败（尚未删除），其余通过

- [ ] **Step 5: 提交**

```bash
git add backend/app/api/exams.py backend/app/schemas/exam.py backend/app/services/exam_service.py
git commit -m "feat: 移除后端排名 API 端点、Schema 和 Service"
```

---

### Task 6: 清理所有排名相关测试

**Files:**
- Modify: `frontend/src/pages/P0Pages.test.tsx`
- Modify: `frontend/src/components/layout/__tests__/TopNav.test.tsx`
- Modify: `backend/app/tests/test_exam_service.py`

- [ ] **Step 1: 清理 P0Pages.test.tsx**

在 `frontend/src/pages/P0Pages.test.tsx` 中：
1. 删除 `RankingPage` import（第 19 行）
2. 删除 `getExamRanking` import（第 10 行）
3. 删除 `getExamRanking` mock（第 38 行）
4. 删除 `rankingRows` fixture（第 125-147 行）
5. 删除 `vi.mocked(getExamRanking).mockResolvedValue(rankingRows);`（第 196 行）
6. 删除排名测试 "renders ranking summary cards before the detailed ranking table"（第 323-331 行）
7. 从 exam fixture 中删除 `show_ranking: true`（第 116 行）

- [ ] **Step 2: 清理 TopNav.test.tsx**

在 `frontend/src/components/layout/__tests__/TopNav.test.tsx` 中：
1. 删除 `activeExamId` prop 从 `renderTopNav` 函数（第 35 行）
2. 删除传递 `activeExamId` 的调用（第 44 行）
3. 删除测试 "renders all three primary nav items" 中的排名断言（第 61 行），改为断言两项
4. 删除测试 "links ranking to the current active exam"（第 64-67 行）
5. 删除测试 "keeps ranking active without also highlighting the exam list item"（第 79-84 行）
6. 删除测试 "does not highlight ranking when there is no active exam and path is /exams"（第 86-91 行）

- [ ] **Step 3: 清理 test_exam_service.py**

在 `backend/app/tests/test_exam_service.py` 中：
1. 删除整个 ranking 测试段（第 701-767 行），包含：
   - `test_get_ranking_orders_by_score_desc`
   - `test_get_ranking_excludes_in_progress`
   - `test_get_ranking_empty_for_no_attempts`

- [ ] **Step 4: 运行全部测试**

```bash
cd frontend && npm run test -- --run
cd backend && uv run pytest
```

Expected: 全部通过

- [ ] **Step 5: 提交**

```bash
git add frontend/src/pages/P0Pages.test.tsx frontend/src/components/layout/__tests__/TopNav.test.tsx backend/app/tests/test_exam_service.py
git commit -m "test: 清理排名相关测试用例和 mock"
```

---

### Task 7: 最终验证

- [ ] **Step 1: 运行前端 lint 和类型检查**

```bash
cd frontend && npm run lint && npx tsc --noEmit
```

Expected: 无新增错误

- [ ] **Step 2: 运行后端 lint 和类型检查**

```bash
cd backend && uv run ruff check . && uv run ty check
```

Expected: 无新增错误

- [ ] **Step 3: 确认无残留排名引用**

```bash
grep -rn "ranking\|排名\|RankingRow\|getExamRanking\|get_ranking\|show_ranking" frontend/src/ backend/app/ --include="*.py" --include="*.ts" --include="*.tsx" | grep -v __pycache__ | grep -v node_modules
```

Expected: 无输出（所有排名引用已清除）

- [ ] **Step 4: 确认结果页面仍然正常**

手动验证 `ExamResultPage.tsx` 仍然完整保留打分、及格状态、答案解析等功能。
