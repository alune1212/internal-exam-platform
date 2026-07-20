# Internal Exam Platform

公司内部轻量级临时考试与刷题平台，用于快速组织内部视频学习、考试、练习刷题、自动判分和基础报表统计。

第一阶段已经形成可运行的考试闭环，并增加了独立的视频学习模块：后端 API、数据库模型、迁移、前端页面、Docker Compose 和项目文档。考试默认按固定 50 题等价试卷出题并保留题目快照；管理员使用签名 session token，考试名单按单场考试维护，支持名单移除和补考授权，发布时冻结题池，报表支持按考试过滤并导出单个 Excel 多 Sheet 工作簿。视频学习由管理员本地上传视频，考试人完成 90% 观看后标记完成，不绑定考试资格、交卷、成绩或排名。

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

## 运行配置

系统支持三个 `ENVIRONMENT`：

| Profile | 用途 | 网络与安全约束 |
| --- | --- | --- |
| `development` | 本机开发、自动化测试 | 保留示例值兼容性，可使用 `memory` OTP |
| `internal` | 受控私有局域网内的正式内部考试 | 仅允许显式私网 IP 的 HTTP 入口，强密钥、正式数据库凭据、精确 CORS 和 SMTP 均为必填 |
| `production` | 具备 HTTPS 的正式部署 | CORS 只允许正式 HTTPS origin，并沿用全部强配置校验 |

`APP_ROLE` 支持 `backend` 和 `worker`。Compose 已固定各容器角色：backend 接收认证、SMTP、导入和媒体配置；worker 只接收数据库、扫描间隔和 heartbeat 配置，不接收管理员或 SMTP 凭据。

根目录 `.env.example` 是 Compose 配置字段的完整清单。首次使用先复制，且不要提交 `.env`：

```bash
cp .env.example .env
```

受控局域网部署的 `.env` 至少要逐项确认以下值，其中示例 IP 必须替换为部署主机的固定私网地址，口令和密钥必须使用随机强值：

```text
ENVIRONMENT=internal
INTERNAL_LAN_BIND_IP=192.168.10.20
CORS_ORIGINS=http://192.168.10.20:8080
POSTGRES_PASSWORD=<strong-random-password>
DATABASE_URL=postgresql+psycopg://exam:<same-url-encoded-password>@db:5432/internal_exam
ADMIN_PASSWORD=<strong-random-password>
TOKEN_SECRET=<strong-random-secret>
CANDIDATE_LOGIN_EMAIL_DELIVERY_MODE=smtp
CANDIDATE_LOGIN_EMAIL_FROM=exam@example.internal
CANDIDATE_LOGIN_SMTP_HOST=smtp.example.internal
CANDIDATE_LOGIN_SMTP_PORT=587
CANDIDATE_LOGIN_SMTP_USERNAME=<smtp-user-if-required>
CANDIDATE_LOGIN_SMTP_PASSWORD=<smtp-password-if-required>
CANDIDATE_LOGIN_SMTP_USE_TLS=true
CANDIDATE_LOGIN_SMTP_USE_SSL=false
```

`CANDIDATE_LOGIN_SMTP_USE_TLS` 适用于 `587` 等 STARTTLS 端口；`CANDIDATE_LOGIN_SMTP_USE_SSL` 适用于 `465` 或服务商指定的 `994` 等隐式 SSL 端口，两者不能同时为 `true`。SMTP 主机必须使用与服务器证书匹配的域名，不能直接沿用证书未覆盖的别名或 IP。需要认证时，SMTP 用户名和密码必须同时配置；密码应使用邮件服务商提供的 SMTP 授权码或应用专用密码。

`internal` 会拒绝 `0.0.0.0`、loopback、公网 IP、示例数据库口令、示例管理员口令/签名密钥、`memory` OTP、空 SMTP，以及不精确匹配 `http://<INTERNAL_LAN_BIND_IP>:<port>` 的 CORS。修改后先做只读渲染检查；不要把渲染输出上传到工单或聊天：

```bash
docker compose --env-file .env config --quiet
```

直接运行后端服务时参考 `backend/.env.example`。前端示例见 `frontend/.env.example`：

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
curl http://localhost:8000/api/ready
```

`/api/health` 仅表示进程存活；`/api/ready` 还会验证 PostgreSQL 和学习媒体目录可用，Compose backend healthcheck 使用后者。

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
cp .env.example .env  # 首次启动前执行，并按目标 profile 替换配置
docker compose --env-file .env config --quiet
docker compose --env-file .env up -d --build
```

统一入口：

```text
http://<INTERNAL_LAN_BIND_IP>:8080
http://<INTERNAL_LAN_BIND_IP>:8080/api/health
http://<INTERNAL_LAN_BIND_IP>:8080/api/ready
http://<INTERNAL_LAN_BIND_IP>:8080/docs
```

Compose 会启动 PostgreSQL、后端、auto-submit worker、前端和 Nginx。后端容器启动时会执行 `alembic upgrade head`。`development` 保留 `0.0.0.0:8080` 默认值；`internal` 必须将 Nginx `8080` 绑定到显式私网 IP。PostgreSQL `5432` 和前端直连 `5173` 始终只绑定本机回环地址。主机防火墙还必须只允许受控考试子网访问该 IP 的 `8080`，禁止访客 Wi-Fi、公网和不受控网段。

`internal` 的 HTTP 不会加密管理员或考试人的 bearer token。该残余风险只在受控私网、小范围内部考试中被接受；不得把端口暴露到公网或不受控网络。扩大网络或人员范围前必须升级到 `production` + HTTPS。

学习视频文件保存在 Compose named volume `learning_media`，Nginx 通过 `/media/learning/` 只读提供播放，并启用匹配的 500 MiB 上传大小限制。正式备份必须同时覆盖 PostgreSQL 和 `learning_media`。创建配对备份与隔离恢复校验的命令见 [`docs/internal-deployment-operations.md`](docs/internal-deployment-operations.md)。

配置或代码变更后的更新方式：

- 只修改 `.env`：执行 `docker compose --env-file .env up -d --force-recreate`。
- 修改 backend/frontend 源码、依赖或 Dockerfile：执行 `docker compose --env-file .env up -d --build`。
- 修改 `docker-compose.yml` 或 Nginx 配置：重新执行 `config --quiet`，再执行 `up -d --build --force-recreate`。
- 只修改文档或测试：运行相应检查即可，不需要 rebuild 正在运行的镜像。

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
npm test -- --run
npm run lint
npm run build
```

Docker 配置检查：

```bash
docker compose --env-file .env config --quiet
```

## 第一阶段已包含

- `/api/health` 存活检查和 `/api/ready` 数据库/媒体就绪检查
- 候选人、题库、考试、考试记录、题目快照、答案、练习记录、导入批次 ORM 模型
- Alembic 初始迁移
- 考试人端和管理员端 API 路由
- 多选题集合判分服务和测试
- 用户端与管理员端 React 页面
- 独立视频学习模块：管理员本地上传/发布/归档学习视频，考试人观看并记录 90% 完成进度
- 题库/考试/报表代表性 TanStack Table 页面
- 登录/导入/考试编辑代表性 React Hook Form + Zod 表单
- 题库 Excel 导入行级校验、合法题目入库、选项入库、导入批次记录
- 应参人员 Excel 导入行级校验、合法人员入库、导入批次记录
- 单场考试应考名单导入会复用已有人员，并写入 `exam_candidate_scope`
- 题库导入、人员导入、单场考试名单导入均记录 `import_batch`，失败报告可下载 Excel 明细
- 考试配置创建、更新、管理端列表和考试人端 candidate-scoped active 列表入库，支持 `available_from` / `available_until` 开放窗口
- 考试从 draft 发布为 active 时冻结 `exam_question_pool`；正式开始考试时只从该场 frozen pool 抽题
- 单场考试名单支持导入、列表、移除和补考授权；未使用补考授权会让已提交考生重新出现在可参加考试列表中
- 开始考试时按 `question_rule` 生成固定 50 题等价试卷，题干去重、整数均分，创建 attempt 和题目快照，答案暂存入库，提交后按快照自动判分
- 考试结果返回及格线和通过状态，当前固定试卷规则为总分 100、及格线 60
- 到时自动提交后台检查、原子 heartbeat/容器健康检查、考试排名和管理端报表 SQL 查询
- 管理端报表支持按 `exam_id` 过滤，并导出为单个 Excel 工作簿，包含成绩报表、题目正确率、错题统计和参考状态
- 学习报表支持按视频和完成状态过滤，并导出 Excel
- 候选人登录需要姓名、邮箱邮件验证码，以及可选员工号；登录验证码和管理员 token 颁发接口带应用层限流
- 练习模式通过 `X-Candidate-Token` 识别考生，练习题列表和提交响应都不返回正确答案、解析或判分结果
- 管理员登录返回签名 session token，管理端 API 使用 `X-Admin-Token`
- Academic Editorial 前端 redesign：设计令牌、UI primitives、candidate/admin layouts、P0/P1/P2 页面、空态/错态/加载态和考试快捷键

## 当前边界

第一阶段的路由、页面和 service 边界已经建立，题库 Excel 导入、应参人员 Excel 导入、导入失败报告、考试配置、单场考试名单管理、补考授权、发布冻结题池、固定 50 题试卷、开始考试快照、答案暂存、提交判分、自动提交、排名、按考试过滤报表、报表导出、视频学习上传和学习完成报表已经具备入库/查询闭环。当前加固边界包含候选人邮件 OTP 登录校验与短暂有界重试、公开 token/验证码接口限流、Excel 导入大小/行数/sheet 限制、视频上传类型/大小限制、Excel 导出公式转义、`internal`/`production` fail-closed 配置、依赖就绪与 worker heartbeat、配对备份/隔离恢复校验、保存/提交时锁定 attempt 读取，以及只通过 Nginx `8080` 对指定局域网 IP 开放浏览器入口。系统仍保持轻量内部考试平台定位，不包含复杂 RBAC、多租户、完整 LMS、监考/防作弊、Word 导入、短信验证码、SSO、持久邮件队列或自动 HTTPS。

## 后续开发计划

1. 正式使用前按 `docs/official-exam-uat-checklist.md` 从第二台允许的局域网设备完成真实 SMTP、考试主链、worker 恢复和配对备份恢复验收。
2. 将每次正式考试前的配置检查、服务 healthcheck 和隔离恢复验证留存为发布证据。
3. 如需扩大网络暴露范围，先部署 HTTPS 并切换 `production`；权限扩展仍遵循轻量边界，不引入复杂 RBAC。
