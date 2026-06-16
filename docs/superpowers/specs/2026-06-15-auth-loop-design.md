# 前后端身份认证闭环设计

日期：2026-06-15
状态：待审批

## 问题

前端 API 请求没有统一注入认证 header，导致后端鉴权形同虚设：

1. `AdminLoginPage` 登录成功后不保存 token，直接跳转。
2. `AdminLayout` 无登录态守卫，任何人可直接访问 `/admin/dashboard`。
3. `apiRequest` / `uploadRequest` 不附加 `X-Admin-Token` 或 `X-Candidate-Id`。
4. `startExam` 把 `candidate_id` 放在 body，后端实际从 `X-Candidate-Id` header 读取。
5. API 返回 401 时前端无响应，页面可能卡死。

## 设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| Admin token 来源 | 存用户输入的密码 | `require_admin` 校验的是 `settings.admin_password`，不是 session token。零后端改动。 |
| 401 处理 | 自动清 session + 跳转登录页 | 防止服务重启或 token 失效后页面卡死。 |
| Header 注入位置 | `client.ts` 统一处理 | 调用方无感知，不改函数签名。 |
| Admin 登出 | 不实现（out of scope） | 用户要求"只做身份闭环"，AdminSideRail 无登出按钮，暂不添加。 |

## 方案

### 1. 新建 `frontend/src/lib/adminSession.ts`

三个纯函数，对称于 `candidateSession.ts`：

```
getAdminToken(): string | null     — 读 localStorage "internal-exam-admin-token"
setAdminToken(token: string): void — 写入
clearAdminToken(): void            — 清除
```

存的是用户输入的密码明文。

### 2. 修改 `frontend/src/api/client.ts`

新增内部函数 `resolveAuthHeaders(path: string): Record<string, string>`：

- path 含 `/api/admin/` → `{ "X-Admin-Token": getAdminToken() ?? "" }`
- 否则有 candidate → `{ "X-Candidate-Id": candidate.id.toString() }`
- 否则 → `{}`（公开接口如 `/api/exams/active`）

注入位置：

- `apiRequest`：`{ "Content-Type": "application/json", ...resolveAuthHeaders(path), ...init?.headers }`
- `uploadRequest`：`{ ...resolveAuthHeaders(path) }`

401 处理（在 `!response.ok` 分支内，`throw` 之前）：

- `response.status === 401` 且 path 含 `/api/admin/` → `clearAdminToken()` + `location.href = "/admin/login"`
- `response.status === 401` 且非 admin → `clearCurrentCandidate()` + `location.href = "/login"`

用 `location.href` 而非 `navigate`，因为 `client.ts` 在 React 组件树外。

注意：`loginAdmin` 也走 `/api/admin/login`，此时无 token。该路由不在 `admin_router` 上，不受 `require_admin` 保护，header 为空字符串不影响。✅

### 3. 修改 `frontend/src/pages/admin/AdminLoginPage.tsx`

```typescript
import { setAdminToken } from "@/lib/adminSession";

// mutation onSuccess:
onSuccess: (_data, variables) => {
  setAdminToken(variables.password);
  navigate("/admin/dashboard");
}
```

`variables` 是 `mutation.mutate(values)` 传入的 `{ username, password }`。

### 4. 修改 `frontend/src/components/layout/AdminLayout.tsx`

在组件顶部加登录态守卫：

```typescript
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { getAdminToken } from "@/lib/adminSession";

// 组件内:
const navigate = useNavigate();
useEffect(() => {
  if (!getAdminToken()) {
    navigate("/admin/login", { replace: true });
  }
}, [navigate]);
```

### 5. 修改 `frontend/src/api/exams.ts`

`startExam` 去掉 `candidateId` 参数和 body：

```typescript
// 修改前
export function startExam(examId: string, candidateId: number) {
  return apiRequest<ExamStartResponse>(`/api/exams/${examId}/start`, {
    method: "POST",
    body: JSON.stringify({ candidate_id: candidateId }),
  });
}

// 修改后
export function startExam(examId: string) {
  return apiRequest<ExamStartResponse>(`/api/exams/${examId}/start`, {
    method: "POST",
  });
}
```

后端 `start_exam` 路由无 body 参数，`candidate_id` 完全来自 `X-Candidate-Id` header。

### 6. 调用方更新

- 全局搜索 `startExam(` → 去掉第二个参数 `candidate.id`
- 全局搜索手动传 `X-Admin-Token` / `X-Candidate-Id` 的地方 → 删除，由 `client.ts` 统一管理

### 7. 不改动的文件

| 文件 | 原因 |
|------|------|
| `api/attempts.ts` | 已不传 `candidate_id`，路径自动走 `resolveAuthHeaders` |
| `api/auth.ts` | 登录接口，不需要 auth header |
| `lib/candidateSession.ts` | 已有，无需修改 |
| 所有后端文件 | 不在范围内 |
| `AdminSideRail.tsx` | 不添加登出按钮（out of scope） |

## 测试

### `lib/__tests__/adminSession.test.ts`

- `setAdminToken("pw")` 后 `getAdminToken()` 返回 `"pw"`
- `clearAdminToken()` 后返回 `null`
- 初始状态返回 `null`

### `api/__tests__/client.test.ts`

- `resolveAuthHeaders("/api/admin/exams")` + 有 token → 返回 `{ "X-Admin-Token": "pw" }`
- `resolveAuthHeaders("/api/admin/exams")` + 无 token → 返回 `{}`
- `resolveAuthHeaders("/api/attempts/1")` + 有 candidate → 返回 `{ "X-Candidate-Id": "42" }`
- `resolveAuthHeaders("/api/exams/active")` + 无 candidate → 返回 `{}`
- 401 响应 → 清 session + 跳转

### `pages/admin/__tests__/AdminLoginPage.test.tsx`

- 登录成功后 `localStorage` 有 admin token
- 登录成功后跳转 `/admin/dashboard`

## 验收标准

1. 直接访问 `/admin/dashboard` → 重定向 `/admin/login`
2. 错误密码 → 提示错误，不跳转
3. 正确密码 → 跳转 dashboard，localStorage 有 token
4. 刷新页面 → 仍在 dashboard
5. 候选人登录 → 进入考试列表
6. 开始考试 → 请求 headers 含 `X-Candidate-Id`，body 不含 `candidate_id`
7. 答题保存 / 交卷 → 请求 headers 含 `X-Candidate-Id`
8. `npm test` / `npm run lint` / `npm run build` 通过

## 范围外

- Admin 登出功能
- 候选人登出改进
- 密码加密存储（localStorage 明文）
- 后端 token 校验改造
- 复杂 RBAC
