# Internal Exam Platform

公司内部轻量级临时考试与刷题平台，用于快速组织内部考试、练习刷题、自动判分和基础报表统计。

第一阶段已经形成可运行的考试闭环：后端 API、数据库模型、迁移、前端页面、Docker Compose 和项目文档。考试默认按固定 50 题等价试卷出题并保留题目快照；管理员使用签名 session token，考试名单按单场考试维护，报表支持单个 Excel 多 Sheet 导出。

## 技术栈

- 前端：React、TypeScript、Vite、Tailwind CSS、shadcn/ui-compatible components、React Router、TanStack Query、TanStack Table、React Hook Form、Zod
- 后端：FastAPI、Pydantic、SQLAlchemy 2.0、Alembic、PostgreSQL、openpyxl
- 部署：Docker Compose、Nginx

## 目录结构

```text
internal-exam-platform/
  backend/       FastAPI 后端、SQLAlchemy 模型、Alembic 迁移
  frontend/      React/Vite 前端、页面、API client、Academic Editorial 设计系统
  docs/          需求、数据库、API、导入模板、交接文档
  nginx/         统一入口反向代理配置
  docker-compose.yml
```

## 环境变量

后端示例见 `backend/.env.example`：

```text
DATABASE_URL=postgresql+psycopg://exam:exam@db:5432/internal_exam
CORS_ORIGINS=http://localhost:5173,http://localhost:8080
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change-me
TOKEN_SECRET=change-me-in-production
```

前端示例见 `frontend/.env.example`：

```text
VITE_API_BASE_URL=
```

留空时前端按 same-origin 请求 `/api`，适合 Nginx 统一入口。

## 后端启动

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

健康检查：

```bash
curl http://localhost:8000/api/health
```

OpenAPI 文档：

```text
http://localhost:8000/docs
```

## 前端启动

```bash
cd frontend
npm install
npm run dev
```

前端开发地址：

```text
http://localhost:5173
```

## Docker Compose 启动

```bash
docker-compose up -d --build
```

统一入口：

```text
http://localhost:8080
http://localhost:8080/api/health
http://localhost:8080/docs
```

Compose 会启动 PostgreSQL、后端、前端和 Nginx。后端容器启动时会执行 `alembic upgrade head`。

## 数据库迁移

创建迁移：

```bash
cd backend
uv run alembic revision --autogenerate -m "describe change"
```

执行迁移：

```bash
uv run alembic upgrade head
```

回滚到空库：

```bash
uv run alembic downgrade base
```

## 测试和构建

后端测试：

```bash
cd backend
uv run pytest
```

前端构建：

```bash
cd frontend
npm run build
```

Docker 配置检查：

```bash
docker-compose config
```

## 第一阶段已包含

- `/api/health` 健康检查
- 候选人、题库、考试、考试记录、题目快照、答案、练习记录、导入批次 ORM 模型
- Alembic 初始迁移
- 考试人端和管理员端 API 路由
- 多选题集合判分服务和测试
- 用户端与管理员端 React 页面
- 题库/考试/报表代表性 TanStack Table 页面
- 登录/导入/考试编辑代表性 React Hook Form + Zod 表单
- 题库 Excel 导入行级校验、合法题目入库、选项入库、导入批次记录
- 应参人员 Excel 导入行级校验、合法人员入库、导入批次记录
- 单场考试应考名单导入会复用已有人员，并写入 `exam_candidate_scope`
- 考试配置创建、更新、管理端列表和考试人端 active 列表入库
- 开始考试时按 `question_rule` 生成固定 50 题等价试卷，题干去重、整数均分，创建 attempt 和题目快照，答案暂存入库，提交后按快照自动判分
- 考试结果返回及格线和通过状态，当前固定试卷规则为总分 100、及格线 60
- 到时自动提交后台检查、考试排名和管理端报表 SQL 查询
- 管理端报表导出为单个 Excel 工作簿，包含成绩报表、题目正确率、错题统计和参考状态
- 管理员登录返回签名 session token，管理端 API 使用 `X-Admin-Token`
- Academic Editorial 前端 redesign：设计令牌、UI primitives、candidate/admin layouts、P0/P1/P2 页面、空态/错态/加载态和考试快捷键

## 当前边界

第一阶段的路由、页面和 service 边界已经建立，题库 Excel 导入、应参人员 Excel 导入、考试配置、单场考试名单、固定 50 题试卷、开始考试快照、答案暂存、提交判分、自动提交、排名、基础报表和报表导出已经具备入库/查询闭环。仍未完成的是导入失败报告下载。接手实现真实业务时优先查看 `docs/handoff.md`。

## 后续开发计划

1. 为题库导入增加失败报告下载。
2. 继续增强导入结果的失败明细下载与前端入口。
3. 如需扩展权限，仅增加轻量能力，不引入复杂 RBAC。
