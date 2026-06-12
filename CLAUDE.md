# CLAUDE.md

公司内部轻量级临时考试与刷题平台。第一阶段核心功能已全部实现，含题库导入、考试快照、判分、排名、报表、自动提交。

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
npm run build        # 生产构建
npm run lint         # ESLint 检查
npm run lint:fix     # ESLint 自动修复
npm run format       # Prettier 格式化
npm run format:check # Prettier 格式检查
npx tsc --noEmit     # 类型检查
```

Docker：

```bash
docker-compose up -d --build   # 启动全部服务
docker-compose config           # 验证配置
curl http://localhost:8080/api/health  # 通过 Nginx 健康检查
```

## 环境变量

后端通过 `.env` 文件加载配置（参考 `backend/app/core/config.py`）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | `postgresql+psycopg://exam:exam@db:5432/internal_exam` | 数据库连接串 |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:8080` | 逗号分隔的前端域名 |
| `ADMIN_USERNAME` | `admin` | 管理员登录用户名 |
| `ADMIN_PASSWORD` | `change-me` | 管理员登录密码 |
| `TOKEN_SECRET` | `change-me-in-production` | 会话 token 密钥（≥8 字符） |

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

领域异常体系：所有业务异常继承 `app.core.exceptions.DomainError`（含 `status_code` 属性），API 路由层通过 `main.py` 的统一异常处理器映射为 HTTP 响应。新增异常时在 service 层定义，无需在路由层逐一捕获。

## 硬边界

- 不引入 Redis、Celery、微服务或复杂 RBAC
- 不实现 Word 解析，只支持标准 Excel 导入
- 后端业务逻辑放 `services/`，路由保持薄层
- 所有请求/响应使用 `schemas/` 中的 Pydantic 模型
- 考试快照语义不可破坏：历史答题记录必须使用保存的题目、选项、答案、解析、分值和顺序快照
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

第一阶段核心功能已全部实现。详细交接文档见 `docs/handoff.md`。

## Commit 规范

- commit 描述使用简体中文
- 格式：`<type>: <描述>`
- type 使用英文（feat / fix / refactor / docs / chore / test）
- 示例：`feat: 实现题库 Excel 导入入库`
