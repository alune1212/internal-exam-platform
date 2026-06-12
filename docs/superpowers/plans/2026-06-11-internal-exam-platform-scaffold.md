# Internal Exam Platform Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从 0 搭建一个可本地启动、可迁移、可继续迭代的公司内部临时考试平台 monorepo 框架。

**Architecture:** 前后端分离，所有后端接口统一挂载在 `/api`，React 前端通过 Vite dev proxy 或 Nginx 访问后端。后端用 SQLAlchemy 2.0 建模，考试提交以题目快照为准，Excel 导入、抽题、判分、报表逻辑放在 `services/`，路由层只负责参数接收和响应组装。

**Tech Stack:** React, TypeScript, Vite, shadcn/ui-compatible local components, Tailwind CSS, React Router, TanStack Query, TanStack Table, React Hook Form, Zod, FastAPI, Pydantic, SQLAlchemy 2.0, Alembic, PostgreSQL, openpyxl, Docker Compose, Nginx.

---

## Scope Boundaries

### In Scope

- 初始化 monorepo 目录、后端、前端、Docker、文档。
- 创建 SQLAlchemy 模型和 Alembic 初始迁移。
- 创建所有要求的 API 路由，允许部分业务为可运行占位实现。
- 创建所有要求的前端路由和页面骨架，能跳转、能渲染。
- 创建代表性表格、表单、查询调用样例，证明技术栈已经接入。
- 创建健康检查和基础测试。

### Out of Scope

- 不实现 Word 解析。
- 不实现 Redis、Celery、消息队列、微服务。
- 不实现复杂 RBAC。
- 不实现完整生产认证体系。
- 不实现复杂抽题规则编辑器，只保留 `question_rule` JSON 字段和服务边界。
- 不实现完整 Excel 导出格式美化，只预留报表导出接口。

## Assumptions

- 第一阶段管理员登录使用简单配置口令或占位 token，后续再替换为正式认证。
- 考试人登录优先按 `employee_no`，没有时按姓名唯一匹配；第一阶段通过 schema 和 service 注释明确该规则。
- `question_rule` 第一阶段默认为抽取全部 active 题目或按固定数量预留，正式规则后续迭代。
- shadcn/ui 第一阶段使用本地组件文件，保留 `components.json` 和 Tailwind alias，后续可继续用 shadcn CLI 增加组件。
- Docker Compose 的 Nginx 服务作为生产拓扑预留；本地开发也可以直接访问前端和后端端口。

## Success Criteria

- `docker-compose up` 能启动 PostgreSQL、后端、前端、Nginx。
- `GET /api/health` 返回正常状态。
- FastAPI OpenAPI 文档可访问。
- 前端首页可打开并跳转到用户端、管理员端页面。
- Alembic 初始迁移可创建核心表。
- 后端测试至少覆盖健康检查和判分集合比较。
- README 和 docs 能指导新人启动项目。

## File Map

### Repository Root

- `README.md`: 项目简介、技术栈、目录结构、启动方式、环境变量、迁移方式、后续计划。
- `.gitignore`: Python、Node、Docker、本地 env、缓存、构建产物。
- `docker-compose.yml`: PostgreSQL、backend、frontend、nginx 服务。
- `nginx/default.conf`: `/api` 反代后端，其余请求走前端。

### Backend

- `backend/pyproject.toml`: Python 依赖、pytest 配置。
- `backend/Dockerfile`: FastAPI 容器构建。
- `backend/.env.example`: 数据库、CORS、管理员口令、应用配置。
- `backend/alembic.ini`: Alembic 配置。
- `backend/alembic/env.py`: 读取应用 metadata 和数据库 URL。
- `backend/alembic/versions/202606110001_initial_schema.py`: 初始表结构。
- `backend/app/main.py`: FastAPI app、CORS、根路由挂载。
- `backend/app/core/config.py`: Pydantic settings。
- `backend/app/core/database.py`: SQLAlchemy engine、session、Base。
- `backend/app/core/security.py`: 第一阶段 token/hash 占位工具。
- `backend/app/models/*.py`: ORM 模型。
- `backend/app/schemas/*.py`: Pydantic schemas。
- `backend/app/api/*.py`: API 路由。
- `backend/app/services/*.py`: 业务服务。
- `backend/app/tests/*.py`: 基础测试。

### Frontend

- `frontend/package.json`: 前端依赖和脚本。
- `frontend/Dockerfile`: Vite 构建和 Nginx 静态服务。
- `frontend/.env.example`: `VITE_API_BASE_URL`。
- `frontend/index.html`: Vite 入口。
- `frontend/vite.config.ts`: React、alias、dev proxy。
- `frontend/tailwind.config.ts`: Tailwind/shadcn preset。
- `frontend/components.json`: shadcn 配置。
- `frontend/src/main.tsx`: Provider 挂载。
- `frontend/src/app/router.tsx`: 全部路由。
- `frontend/src/api/*.ts`: API client。
- `frontend/src/components/ui/*.tsx`: shadcn-compatible primitives。
- `frontend/src/components/layout/*.tsx`: 用户端和管理员端 Layout。
- `frontend/src/pages/**/*.tsx`: 页面骨架。
- `frontend/src/types/*.ts`: 领域类型。

### Docs

- `docs/requirements.md`: 背景、角色、题型、模式、第一阶段范围。
- `docs/database-design.md`: 表结构、关系、约束、快照原则。
- `docs/api-design.md`: API 路由、请求响应、统一返回格式。
- `docs/import-templates.md`: 题库和应参人员 Excel 字段、校验规则、导入结果格式。

---

## Implementation Checklist

### Task 1: Repository Baseline

**Goal:** 建立不含业务实现的 monorepo 基线。

**Files:**
- Modify: `.gitignore`
- Modify: `README.md`
- Create: `backend/`
- Create: `frontend/`
- Create: `docs/`
- Create: `nginx/`

- [ ] 确认仓库只有初始文件，运行 `git status --short --branch`。
- [ ] 创建目录结构，严格匹配用户指定路径。
- [ ] 更新 `.gitignore`，覆盖 `.env`、`.venv`、`__pycache__`、`.pytest_cache`、`node_modules`、`dist`、`.DS_Store`。
- [ ] 暂不创建业务外的额外顶层目录。
- [ ] 验证：`find . -maxdepth 3 -type d | sort` 能看到 backend/frontend/docs/nginx 主结构。
- [ ] 退出标准：目录结构存在，未引入任何未要求的服务或依赖。

### Task 2: Backend Package and App Shell

**Goal:** FastAPI 后端能启动并暴露 `/api/health`。

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/router.py`
- Create: `backend/app/schemas/common.py`
- Create: `backend/app/tests/test_health.py`

- [ ] 在 `pyproject.toml` 添加最小依赖：`fastapi`、`uvicorn[standard]`、`pydantic-settings`、`sqlalchemy`、`alembic`、`psycopg[binary]`、`openpyxl`、`python-multipart`。
- [ ] 添加开发依赖：`pytest`、`httpx`。
- [ ] 在 `schemas/common.py` 定义统一响应：`ApiResponse[T]`、`PageResponse[T]`、`ErrorResponse`。
- [ ] 在 `api/router.py` 创建 `APIRouter(prefix="/api")`，注册 `/health`。
- [ ] 在 `main.py` 创建 app，挂载 router，配置 CORS 来源从 settings 读取。
- [ ] 在 `test_health.py` 使用 FastAPI TestClient 调用 `/api/health`。
- [ ] 验证：`cd backend && uv run pytest`。
- [ ] 退出标准：健康检查测试通过，OpenAPI 路径中存在 `/api/health`。

### Task 3: Backend Configuration and Database

**Goal:** 后端配置和 PostgreSQL 连接不硬编码。

**Files:**
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/database.py`
- Create: `backend/app/core/security.py`
- Create: `backend/.env.example`

- [ ] 在 `config.py` 用 `pydantic-settings` 定义 `Settings`：`app_name`、`environment`、`database_url`、`cors_origins`、`admin_username`、`admin_password`、`token_secret`。
- [ ] `database_url` 默认指向 Docker Compose 服务名 `db`，本地可通过 env 覆盖。
- [ ] 在 `database.py` 定义 `Base`、`engine`、`SessionLocal`、`get_db()`。
- [ ] 时间字段统一使用 `datetime.now(timezone.utc)` 或数据库 timezone-aware 类型。
- [ ] `security.py` 只提供第一阶段占位 token 函数，不引入复杂权限系统。
- [ ] `.env.example` 只写示例值，不写真实密钥。
- [ ] 验证：`python -c "from app.core.config import settings; print(settings.app_name)"` 可执行。
- [ ] 退出标准：所有配置均来自 env 或安全默认值。

### Task 4: Backend ORM Models

**Goal:** 创建第一阶段核心表模型，字段、索引、约束清晰。

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/base.py`
- Create: `backend/app/models/candidate.py`
- Create: `backend/app/models/question.py`
- Create: `backend/app/models/exam.py`
- Create: `backend/app/models/attempt.py`
- Create: `backend/app/models/import_batch.py`

- [ ] 在 `base.py` 定义 `TimestampMixin`，包含 `created_at`、`updated_at`。
- [ ] `candidate.py` 定义 `Candidate`，`employee_no` 可空但唯一，`name` 建索引。
- [ ] `question.py` 定义 `Question` 和 `QuestionOption`，`question_type/status` 建索引，`question_id + label` 唯一。
- [ ] `exam.py` 定义 `Exam`，`question_rule` 用 JSON 字段，`status` 建索引。
- [ ] `attempt.py` 定义 `ExamAttempt`、`ExamAttemptQuestion`、`ExamAttemptAnswer`、`PracticeAnswer`。
- [ ] `ExamAttemptQuestion` 保存题干、选项、正确答案、解析、分值、顺序快照。
- [ ] `import_batch.py` 定义导入批次和错误报告 JSON。
- [ ] 在 `models/__init__.py` 导入所有模型，供 Alembic metadata 发现。
- [ ] 验证：`python -c "from app.models import Candidate, Question, ExamAttempt"`。
- [ ] 退出标准：模型可导入，关系不循环报错。

### Task 5: Alembic Initial Migration

**Goal:** Alembic 能创建所有核心表。

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/README`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/202606110001_initial_schema.py`

- [ ] `env.py` 从 `app.core.config.settings.database_url` 读取数据库 URL。
- [ ] `env.py` 导入 `app.models` 并绑定 `Base.metadata`。
- [ ] 初始 migration 手写表结构，避免因空库生成失败。
- [ ] migration 包含外键、唯一约束、索引和 JSON 字段。
- [ ] 验证：`cd backend && alembic upgrade head`，连接 Docker PostgreSQL。
- [ ] 验证：`cd backend && alembic downgrade base && alembic upgrade head`。
- [ ] 退出标准：数据库表可创建、可回滚、可再创建。

### Task 6: Backend Schemas

**Goal:** 所有 API 请求和响应都有 Pydantic schema。

**Files:**
- Create: `backend/app/schemas/candidate.py`
- Create: `backend/app/schemas/question.py`
- Create: `backend/app/schemas/exam.py`
- Create: `backend/app/schemas/attempt.py`
- Create: `backend/app/schemas/report.py`
- Create: `backend/app/schemas/common.py`

- [ ] `candidate.py` 定义 `CandidateLoginRequest`、`CandidateRead`、`CandidateImportRow`。
- [ ] `question.py` 定义 `QuestionCreate`、`QuestionUpdate`、`QuestionRead`、`QuestionOptionRead`、`QuestionImportResult`。
- [ ] `exam.py` 定义 `ExamCreate`、`ExamUpdate`、`ExamRead`、`ExamStartResponse`、`RankingRow`。
- [ ] `attempt.py` 定义 `AttemptRead`、`AttemptQuestionRead`、`AnswerSaveRequest`、`SubmitRequest`、`AttemptResultRead`。
- [ ] `report.py` 定义 `ScoreReportRow`、`QuestionAccuracyRow`、`WrongQuestionRow`、`AbsentCandidateRow`。
- [ ] 使用 `ConfigDict(from_attributes=True)` 支持 ORM 转换。
- [ ] 验证：`python -c "from app.schemas.exam import ExamRead"`。
- [ ] 退出标准：route 不返回裸 dict 业务结构，统一走 schema。

### Task 7: Backend Services

**Goal:** 路由保持薄，业务边界清楚。

**Files:**
- Create: `backend/app/services/import_service.py`
- Create: `backend/app/services/question_service.py`
- Create: `backend/app/services/exam_service.py`
- Create: `backend/app/services/scoring_service.py`
- Create: `backend/app/services/report_service.py`
- Create: `backend/app/tests/test_scoring_service.py`

- [ ] `scoring_service.py` 实现 `normalize_answer_set(answer: str) -> set[str]`。
- [ ] `scoring_service.py` 实现 `score_answer(question_type, correct_answer, selected_answer, score)`。
- [ ] 测试多选集合比较：`A,C` 与 `C,A` 判正确。
- [ ] 测试单选和判断完全匹配。
- [ ] `import_service.py` 定义题库 Excel 校验函数，返回成功/失败行结构。
- [ ] `question_service.py` 定义题目列表、创建、更新、删除占位服务。
- [ ] `exam_service.py` 定义开始考试、生成快照、保存答案、提交考试的服务边界。
- [ ] `report_service.py` 定义成绩、正确率、错题、缺考报表查询边界。
- [ ] 验证：`cd backend && uv run pytest`。
- [ ] 退出标准：判分核心规则有测试，路由不直接实现复杂判分。

### Task 8: Backend API Routes

**Goal:** 创建用户端和管理员端要求的全部 API 路由。

**Files:**
- Create: `backend/app/api/auth.py`
- Create: `backend/app/api/candidates.py`
- Create: `backend/app/api/questions.py`
- Create: `backend/app/api/exams.py`
- Create: `backend/app/api/attempts.py`
- Create: `backend/app/api/practice.py`
- Create: `backend/app/api/reports.py`
- Create: `backend/app/api/imports.py`
- Modify: `backend/app/api/router.py`

- [ ] `POST /api/candidates/login` 调用 candidate service。
- [ ] `GET /api/practice/questions` 返回 active 题目列表。
- [ ] `POST /api/practice/answers` 保存练习答案。
- [ ] `GET /api/exams/active` 返回 active 考试。
- [ ] `POST /api/exams/{exam_id}/start` 创建 attempt 和题目快照。
- [ ] `GET /api/attempts/{attempt_id}` 返回考试进行中详情。
- [ ] `POST /api/attempts/{attempt_id}/answers/save` 自动暂存答案。
- [ ] `POST /api/attempts/{attempt_id}/submit` 提交并判分。
- [ ] `GET /api/attempts/{attempt_id}/result` 返回成绩、答案和解析。
- [ ] `GET /api/exams/{exam_id}/ranking` 返回排名。
- [ ] `POST /api/admin/login` 返回管理员占位 token。
- [ ] `POST /api/admin/questions/import` 接收 Excel 文件。
- [ ] `GET/POST/PUT/DELETE /api/admin/questions...` 管理题目。
- [ ] `POST/GET/PUT /api/admin/exams...` 管理考试。
- [ ] `POST /api/admin/exams/{exam_id}/candidates/import` 导入应参人员。
- [ ] `GET /api/admin/reports/*` 返回报表行。
- [ ] 验证：访问 `/docs`，确认 OpenAPI 列出全部路由。
- [ ] 退出标准：所有要求路径存在，未实现的复杂逻辑有明确 service stub。

### Task 9: Frontend Foundation

**Goal:** React/Vite/TypeScript/Tailwind/shadcn 基础可构建。

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/index.html`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/postcss.config.js`
- Create: `frontend/components.json`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/index.css`
- Create: `frontend/src/lib/utils.ts`
- Create: `frontend/.env.example`

- [ ] `package.json` 添加 React、Vite、Router、TanStack Query/Table、React Hook Form、Zod、lucide-react、tailwind、class-variance-authority、clsx、tailwind-merge。
- [ ] `vite.config.ts` 配置 `@` alias 和 `/api` dev proxy。
- [ ] `tailwind.config.ts` 配置 shadcn 常用 CSS variables。
- [ ] `main.tsx` 挂载 `QueryClientProvider` 和 `RouterProvider`。
- [ ] `index.css` 定义 shadcn CSS variables 和基础样式。
- [ ] 验证：`cd frontend && npm install && npm run build`。
- [ ] 退出标准：空页面可以编译，Tailwind class 生效。

### Task 10: Frontend UI Primitives and Layout

**Goal:** 页面骨架使用统一视觉和布局边界。

**Files:**
- Create: `frontend/src/components/ui/button.tsx`
- Create: `frontend/src/components/ui/card.tsx`
- Create: `frontend/src/components/ui/input.tsx`
- Create: `frontend/src/components/ui/label.tsx`
- Create: `frontend/src/components/ui/table.tsx`
- Create: `frontend/src/components/ui/badge.tsx`
- Create: `frontend/src/components/layout/CandidateLayout.tsx`
- Create: `frontend/src/components/layout/AdminLayout.tsx`

- [ ] 按 shadcn 风格创建最小可用 UI primitives。
- [ ] `CandidateLayout` 提供用户端导航：登录、练习、考试、排名。
- [ ] `AdminLayout` 提供管理员导航：仪表盘、题库、考试、报表。
- [ ] 使用 lucide 图标表示导航和按钮动作。
- [ ] 不做营销式首页，第一屏直接进入工具界面。
- [ ] 验证：布局组件在所有页面中无 TypeScript 报错。
- [ ] 退出标准：管理员端和考试人端布局分离。

### Task 11: Frontend API and Types

**Goal:** 前端请求和领域类型集中维护。

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/auth.ts`
- Create: `frontend/src/api/questions.ts`
- Create: `frontend/src/api/exams.ts`
- Create: `frontend/src/api/attempts.ts`
- Create: `frontend/src/api/reports.ts`
- Create: `frontend/src/api/imports.ts`
- Create: `frontend/src/types/candidate.ts`
- Create: `frontend/src/types/question.ts`
- Create: `frontend/src/types/exam.ts`
- Create: `frontend/src/types/attempt.ts`
- Create: `frontend/src/types/report.ts`

- [ ] `client.ts` 读取 `VITE_API_BASE_URL`，默认空字符串以支持 same-origin `/api`。
- [ ] 统一处理 JSON 响应和错误。
- [ ] `auth.ts` 封装 candidate/admin login。
- [ ] 其他 API 文件按业务模块导出函数。
- [ ] 类型文件与 Pydantic schema 字段名保持一致。
- [ ] 验证：`npm run build` 无未使用导出导致的类型错误。
- [ ] 退出标准：页面不直接拼 fetch 细节。

### Task 12: Frontend Candidate Pages

**Goal:** 用户端页面路由完整可跳转。

**Files:**
- Create: `frontend/src/app/router.tsx`
- Create: `frontend/src/pages/LoginPage.tsx`
- Create: `frontend/src/pages/PracticePage.tsx`
- Create: `frontend/src/pages/ExamListPage.tsx`
- Create: `frontend/src/pages/ExamStartPage.tsx`
- Create: `frontend/src/pages/ExamTakingPage.tsx`
- Create: `frontend/src/pages/ExamResultPage.tsx`
- Create: `frontend/src/pages/RankingPage.tsx`

- [ ] `/` 重定向到 `/login`。
- [ ] `/login` 使用 React Hook Form + Zod，字段包含姓名和可选员工号。
- [ ] `/practice` 使用 TanStack Query 拉取练习题，展示答案解析区域。
- [ ] `/exams` 展示 active exams。
- [ ] `/exams/:examId/start` 展示考试说明和开始按钮。
- [ ] `/exams/:examId/taking` 展示倒计时、题目列表、暂存按钮、交卷按钮；第一阶段可用静态骨架。
- [ ] `/exams/:examId/result` 展示分数、正确数、错题和解析。
- [ ] `/exams/:examId/ranking` 使用 TanStack Table 展示排名。
- [ ] 验证：浏览器访问每个路由不出现空白页。
- [ ] 退出标准：所有用户端路径存在且使用 CandidateLayout。

### Task 13: Frontend Admin Pages

**Goal:** 管理员端页面路由完整可跳转。

**Files:**
- Create: `frontend/src/pages/admin/AdminLoginPage.tsx`
- Create: `frontend/src/pages/admin/AdminDashboardPage.tsx`
- Create: `frontend/src/pages/admin/QuestionListPage.tsx`
- Create: `frontend/src/pages/admin/QuestionImportPage.tsx`
- Create: `frontend/src/pages/admin/ExamListPage.tsx`
- Create: `frontend/src/pages/admin/ExamEditPage.tsx`
- Create: `frontend/src/pages/admin/CandidateImportPage.tsx`
- Create: `frontend/src/pages/admin/ScoreReportPage.tsx`
- Create: `frontend/src/pages/admin/QuestionAccuracyPage.tsx`
- Create: `frontend/src/pages/admin/WrongQuestionPage.tsx`
- Create: `frontend/src/pages/admin/AbsentCandidatePage.tsx`
- Modify: `frontend/src/app/router.tsx`

- [ ] `/admin/login` 使用 React Hook Form + Zod。
- [ ] `/admin/dashboard` 展示导入、考试、成绩、缺考概览卡片。
- [ ] `/admin/questions` 用 TanStack Table 展示题库。
- [ ] `/admin/questions/import` 提供 Excel 上传表单和导入结果区域。
- [ ] `/admin/exams` 用 TanStack Table 展示考试配置。
- [ ] `/admin/exams/:examId/edit` 使用 React Hook Form + Zod 编辑考试标题、时长、状态、展示答案、展示排名。
- [ ] `/admin/exams/:examId/candidates` 提供应参人员 Excel 上传。
- [ ] `/admin/reports/scores` 用 TanStack Table 展示个人成绩。
- [ ] `/admin/reports/questions` 展示题目正确率。
- [ ] `/admin/reports/wrong` 展示错题排行。
- [ ] `/admin/reports/absent` 展示未参加人员名单。
- [ ] 验证：所有管理员路由不空白，导航可达。
- [ ] 退出标准：所有管理员路径存在且使用 AdminLayout。

### Task 14: Docker and Nginx

**Goal:** 本地 compose 能拉起完整服务。

**Files:**
- Create: `docker-compose.yml`
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile`
- Create: `nginx/default.conf`

- [ ] PostgreSQL 服务名为 `db`，暴露 `5432:5432`。
- [ ] backend 服务依赖 db，环境变量通过 compose 设置或 `.env` 注入。
- [ ] frontend 服务构建 Vite 静态资源。
- [ ] nginx 服务监听 `8080`，`/api` 代理 backend，其余代理 frontend 或静态前端服务。
- [ ] 添加 PostgreSQL volume。
- [ ] 验证：`docker-compose config`。
- [ ] 验证：`docker-compose up --build` 后访问 `http://localhost:8080` 和 `http://localhost:8080/api/health`。
- [ ] 退出标准：compose 配置有效，服务依赖关系清晰。

### Task 15: Documentation

**Goal:** 文档能让新人理解第一阶段边界并启动项目。

**Files:**
- Modify: `README.md`
- Create: `docs/requirements.md`
- Create: `docs/database-design.md`
- Create: `docs/api-design.md`
- Create: `docs/import-templates.md`

- [ ] README 写项目简介、技术栈、目录结构。
- [ ] README 写后端启动、前端启动、Docker Compose 启动。
- [ ] README 写环境变量说明和数据库迁移方式。
- [ ] README 写后续开发计划。
- [ ] `requirements.md` 记录角色、题型、练习模式、考试模式、判分规则。
- [ ] `database-design.md` 记录每张表、字段、索引、约束、快照原因。
- [ ] `api-design.md` 记录所有初始 API、请求响应概要、统一返回格式。
- [ ] `import-templates.md` 记录题库和应参人员 Excel 字段、校验规则、失败报告格式。
- [ ] 验证：文档不承诺第一阶段未实现的完整业务能力。
- [ ] 退出标准：README 足够清晰，docs 覆盖用户要求的四份文档。

### Task 16: Verification Pass

**Goal:** 证明第一阶段框架可运行。

**Commands:**
- `cd backend && uv run pytest`
- `cd frontend && npm install`
- `cd frontend && npm run build`
- `docker-compose config`
- `docker-compose up --build`
- `cd backend && alembic upgrade head`

- [ ] 后端测试通过。
- [ ] 前端构建通过。
- [ ] Compose 配置通过。
- [ ] PostgreSQL 启动后 Alembic 迁移通过。
- [ ] 浏览器打开前端首页成功。
- [ ] 浏览器访问 FastAPI docs 成功。
- [ ] 浏览器访问 `/api/health` 成功。
- [ ] 若某一步因本机环境不可用失败，记录失败命令、错误摘要、下一步修复动作。
- [ ] 退出标准：验收标准全部有验证证据或明确环境阻塞说明。

---

## Recommended Execution Order

1. Task 1-3: 建立后端可启动外壳和配置。
2. Task 4-5: 建立数据库模型和迁移。
3. Task 6-8: 建立 schema、service、API 路由。
4. Task 9-13: 建立前端基础、类型、页面骨架。
5. Task 14-15: 补齐部署和文档。
6. Task 16: 完整验证。

## Risk Controls

- 每个任务只触碰列出的文件。
- 不引入未要求的技术栈。
- 所有复杂业务先放 service 边界，不塞进路由或页面。
- 判分规则先用测试锁住，尤其是多选集合比较。
- 考试快照字段在模型和文档中第一阶段就固定，避免后续历史成绩被题库变更影响。
- Excel 导入第一阶段只支持标准 Excel，不添加 Word fallback。

## Handoff

Plan complete. When implementation is approved, execute this plan task by task and update checkbox status after each verification point.
