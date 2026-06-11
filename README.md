# Internal Exam Platform

公司内部轻量级临时考试与刷题平台，用于快速组织内部考试、练习刷题、自动判分和基础报表统计。

第一阶段交付目标是可启动的项目框架：后端 API、数据库模型、迁移、前端路由页面骨架、Docker Compose 和项目文档。复杂抽题规则、完整认证体系、Excel 导出美化和正式报表计算会在后续阶段补齐。

## 技术栈

- 前端：React、TypeScript、Vite、Tailwind CSS、shadcn/ui-compatible components、React Router、TanStack Query、TanStack Table、React Hook Form、Zod
- 后端：FastAPI、Pydantic、SQLAlchemy 2.0、Alembic、PostgreSQL、openpyxl
- 部署：Docker Compose、Nginx

## 目录结构

```text
internal-exam-platform/
  backend/       FastAPI 后端、SQLAlchemy 模型、Alembic 迁移
  frontend/      React/Vite 前端、页面骨架、API client
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
docker-compose up --build
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
- 考试人端和管理员端 API 路由骨架
- 多选题集合判分服务和测试
- 用户端与管理员端 React 路由页面骨架
- 题库/考试/报表代表性 TanStack Table 页面
- 登录/导入/考试编辑代表性 React Hook Form + Zod 表单
- 题库 Excel 导入行级校验、合法题目入库、选项入库、导入批次记录
- 应参人员 Excel 导入行级校验、合法人员入库、导入批次记录

## 当前边界

第一阶段的路由、页面和 service 边界已经建立，题库 Excel 导入和应参人员 Excel 导入已经具备入库闭环。考试快照持久化、答案提交判分落库、排名和报表 SQL 仍是后续工作。接手实现真实业务时优先查看 `docs/handoff.md`。

## 后续开发计划

1. 为题库导入增加失败报告下载。
2. 将考试配置与应参人员范围建立明确关联。
3. 实现考试开始时的真实抽题和题目快照保存。
4. 实现答案自动暂存、到时自动提交和提前交卷。
5. 完成成绩、题目正确率、错题排行、未参加人员报表查询。
6. 增加必要的管理员会话保护，但不引入复杂 RBAC。
