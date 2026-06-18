# CLAUDE.md

公司内部轻量级临时考试与刷题平台。第一阶段核心功能已实现，含题库导入、考试名单 scope、固定 50 题考试快照、均分判分、及格状态、排名、报表查询/导出、自动提交和 Academic Editorial 前端 redesign。

## 命令

后端：

```bash
cd backend
uv sync                              # 安装依赖
uv run pytest                        # 运行测试
uv run ruff check .                  # lint 检查
uv run ruff check --fix .            # lint 自动修复
uv run ruff format .                 # 代码格式化
uv run ty check                      # 类型检查
uv run alembic upgrade head          # 执行迁移
uv run alembic revision --autogenerate -m "描述"  # 生成迁移
uv run uvicorn app.main:app --reload # 启动开发服务器 (localhost:8000)
```

前端：

```bash
cd frontend
npm install
npm run dev          # 开发服务器 (localhost:5173)
npm run build        # 生产构建（先 tsc --noEmit 再 vite build）
npm run lint         # ESLint 检查
npm run lint:fix     # ESLint 自动修复
npm run format       # Prettier 格式化（prettier --write）
npm run format:check # Prettier 格式检查
npm run test         # Vitest 单次运行
npm run test:watch   # Vitest watch 模式
npx tsc --noEmit     # 类型检查（build 已包含）
```

测试栈：Vitest + @testing-library/react + jsdom，单测覆盖 `components/editorial/`、`components/exam/`、`components/layout/`、`lib/adminSession`、`api/client` 和 `pages/P0Pages.test.tsx`。

> **Node.js v26 注意**：jsdom 的 `window.localStorage` 在 Node.js v26 下可能为 `undefined`。测试中如需操作 localStorage，需在测试文件顶部安装 in-memory mock（参考 `lib/adminSession.test.ts`）。

## 代码质量 Hooks

- **Claude Code Hooks** (`.claude/settings.json`)：Write/Edit 后自动 ruff/prettier/eslint --fix
- **Git Hooks** (`.pre-commit-config.yaml`)：commit 时 ruff + prettier + eslint 全量检查
- **CI**：建议使用 `pre-commit run --all-files` 兜底

```bash
# 安装 git hook（在仓库根目录，配置 .pre-commit-config.yaml 所在位置）
pre-commit install
# 手动运行
pre-commit run --all-files
# 跳过 hook（紧急情况）
git commit --no-verify
```

Docker：

```bash
docker-compose up -d --build   # 启动全部服务
docker-compose config           # 验证配置
curl http://localhost:8080/api/health  # 通过 Nginx 健康检查
```

## 环境变量

后端通过 `backend/.env` 文件加载配置（参考 `backend/app/core/config.py`）。首次启动前先复制模板：

```bash
cp backend/.env.example backend/.env
```

可配置项：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ENVIRONMENT` | `development` | 运行环境；`production` 会启用默认密钥和 CORS 安全校验 |
| `DATABASE_URL` | `postgresql+psycopg://exam:exam@db:5432/internal_exam` | 数据库连接串 |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:8080` | 逗号分隔的前端域名 |
| `ADMIN_USERNAME` | `admin` | 管理员登录用户名 |
| `ADMIN_PASSWORD` | `change-me` | 管理员登录密码 |
| `TOKEN_SECRET` | `change-me-in-production` | 会话 token 密钥（≥8 字符） |
| `IMPORT_MAX_UPLOAD_BYTES` | `5242880` | Excel 导入文件大小上限 |
| `IMPORT_MAX_ROWS` | `5000` | Excel 导入数据行上限 |
| `IMPORT_MAX_SHEETS` | `1` | Excel 导入工作表数量上限 |

## 关键文件

| 用途 | 路径 |
|------|------|
| FastAPI 入口 | `backend/app/main.py` |
| 数据库引擎 | `backend/app/core/database.py` |
| 应用配置 | `backend/app/core/config.py` |
| 领域异常基类 | `backend/app/core/exceptions.py` |
| 后台定时任务 | `backend/app/core/scheduler.py` |
| 路由注册 | `backend/app/api/router.py` |

## 架构

monorepo 结构，前后端分离，Docker Compose 编排。

- `backend/` — FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL + openpyxl
- `frontend/` — React + TypeScript + Vite + Tailwind CSS + shadcn/ui 兼容组件
- `nginx/default.conf` — 反向代理，前端 `/`，后端 `/api`
- `docs/` — 需求、数据库设计、API 设计、导入模板、交接文档

后端分层：`api/`（路由薄层）→ `services/`（业务逻辑）→ `models/`（ORM）→ `schemas/`（Pydantic）。路由文件不要写业务逻辑。

前端分层：`api/`（请求封装）→ `pages/`（页面组件）→ `components/`（UI 组件）→ `types/`（类型定义）。页面不要手写 fetch。

前端身份认证：`api/client.ts` 的 `apiRequest`/`uploadRequest` 根据路径自动注入认证 header——`/api/admin/**` 带 `X-Admin-Token`（`AdminLoginPage` 保存后端返回的签名 session token），其余带 `X-Candidate-Token`（从 `lib/candidateSession.ts` 读取签名 candidate token）。401 时自动清 session 并跳转登录页。后端 `require_admin` 使用 `TOKEN_SECRET` 校验签名 admin token，`get_current_candidate_id` 从 `X-Candidate-Token` header 校验并提取候选人 ID。

前端设计系统：`frontend/src/index.css` 定义 CSS 变量，`frontend/tailwind.config.ts` 映射 Tailwind token，`frontend/src/lib/design-tokens.ts` 仅在需要原始值时使用。优先复用本地 UI primitives 和 `components/editorial/`，不要重新引入旧 shadcn HSL token 或页面级临时样式。完整设计规范见 `frontend/DESIGN.md`（含 token 表、组件清单、章节样式），所有 PR 改动若触及视觉需先读它。

领域异常体系：所有业务异常继承 `app.core.exceptions.DomainError`（含 `status_code` 属性），API 路由层通过 `main.py` 的统一异常处理器映射为 HTTP 响应。新增异常时在 service 层定义，无需在路由层逐一捕获。

考试抽题：非空 `exam.question_rule` 且包含 `question_count` 时走固定试卷逻辑。默认规则为 50 题、总分 100、及格线 60，题型配比 `single: 30`、`multiple: 10`、`judge: 10`；每次开考按规则抽一份 active、题干去重的等价试卷，并按 `total_score / question_count` 均分为整数分值（如 50 题 100 分即每题 2 分）。空 `{}` 保留旧的全量 active 入卷行为。所有正式考试仍以 `exam_attempt_question` 快照为准。

## 硬边界

- 不引入 Redis、Celery、微服务或复杂 RBAC
- 不实现 Word 解析，只支持标准 Excel 导入
- 后端业务逻辑放 `services/`，路由保持薄层
- 所有请求/响应使用 `schemas/` 中的 Pydantic 模型
- 考试快照语义不可破坏：历史答题记录必须使用保存的题目、选项、答案、解析、分值和顺序快照
- 固定试卷语义不可破坏：固定试卷必须按 `question_rule` 的题量、题型配比、题干去重和整数均分规则生成 attempt snapshots
- 多选题判分按集合比较，不按字符串比较
- 前端 API 调用放 `api/`，页面不手写 fetch

## 代码风格

Python：
- 使用 Python 3.12+ 语法（`str | None`、`type X = ...`）
- 类型注解完整，不使用 `Any` 除非必要
- 时间字段统一使用 `datetime` + `timezone=True`
- 测试用 `pytest`，放在 `backend/app/tests/`

TypeScript：
- 严格模式，所有类型显式声明
- 组件使用函数式声明（`function Foo()` 而非箭头函数赋值）
- 列表页用 TanStack Table，表单用 React Hook Form + Zod
- 请求用 TanStack Query，类型放 `types/`

## 数据库迁移

```bash
cd backend
uv run alembic revision --autogenerate -m "add_question_table"
uv run alembic upgrade head
uv run alembic downgrade -1  # 回滚一步
```

迁移文件在 `backend/alembic/versions/`。模型在 `backend/app/models/`。

## 当前阶段

第一阶段核心业务闭环已实现，前端 Academic Editorial redesign（含 Phase 1-7：tokens、primitives、layouts、P0/P1/P2 页面、状态与精修）已合并。考试默认使用固定 50 题等价试卷，结果页显示及格线和通过状态。前后端身份认证闭环已实现（签名 admin token、签名 candidate token、401 自动跳转、AdminLayout 路由守卫）。考试与应参人员范围通过 `exam_candidate_scope` 关联，导入失败报告可下载，报表导出返回单个多 Sheet Excel。当前安全加固包括导入大小/行数/sheet 限制、Excel 公式转义、生产默认密钥/CORS 拒绝、以及保存/提交时锁定 attempt 读取。详细交接文档见 `docs/handoff.md`。

## 与 AGENTS.md 的关系

仓库根目录同时存在 `AGENTS.md`，作为跨代理精简协作指南；本文件（`CLAUDE.md`）保留更详细的 Claude 协作约定。若两者冲突，优先按 live code 与 `docs/handoff.md` 核验，并在同一轮变更中收敛两处说明。

## Commit 规范

- commit 描述使用简体中文
- 格式：`<type>: <描述>`
- type 使用英文（feat / fix / refactor / docs / chore / test）
- 示例：`feat: 实现题库 Excel 导入入库`
