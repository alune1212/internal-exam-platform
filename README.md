# Internal Exam Platform

公司内部轻量级临时考试与刷题平台，用于快速组织内部视频学习、考试、练习刷题、自动判分和基础报表统计。

第一阶段已经形成可运行的考试闭环，并增加了独立的视频学习模块：后端 API、数据库模型、迁移、前端页面、Docker Compose 和项目文档。平台以规范化邮箱 OTP 创建/登录账号：active 用户可学习、练习和复习错题；首次登录的新邮箱先完成显示名称步骤。正式考试仍按单场冻结的应考名单和题池授权，邀请发送是发布后的显式动作，报表从冻结 roster identity 读取并按考试过滤，导出单个 Excel 多 Sheet 工作簿。固定试卷和所有 attempt 均保留题目/答案/成绩快照；视频学习完成度不绑定考试资格、交卷、成绩或排名。

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
  nginx/         应考人员/操作员双入口反向代理配置
  ops/           macOS/未来 Windows、E2E、容量与安全发布门禁
  docker-compose.yml
```

## 正式宿主边界

当前正式宿主是 Apple Silicon macOS + Docker Desktop + Docker Compose，按单宿主 24×7 best-effort 运行；严重宿主、磁盘或办公网络故障允许暂停或改期。Docker Desktop 由登记的 designated host account 运行，可以复用现有受管账号，不强制新建账号。Docker Desktop 必须启用登录后启动、关闭 Resource Saver 并固定为 8 CPU/8 GiB；MacBook 正式考试全程接入 AC，电池不作为正式电源方案。

正式根目录默认是 ${HOME}/Library/Application Support/InternalExam，必须在工作树外；目录 0700、正式环境/state/evidence 0600。正式应考人员入口地址固定为 `192.168.2.34/24`，需要 DHCP reservation；pf/受管防火墙只允许 `192.168.2.0/24` 到 `192.168.2.34:8080`，操作员入口严格只绑定 `127.0.0.1:8081`。考试窗口内停止 development/staging，任何时刻只允许一个 formal writer。LaunchAgent 只恢复已选 release，不等于批准开考。

未来 Windows Docker Desktop + WSL2 仅是迁移目标，必须从 verified paired backup 在真实 Windows/native AMD64 上重新完成 staging、恢复、网络、防火墙、SMTP、桌面/手机 UAT 和 100-client gate；Mac 证据不能替代 Windows acceptance。迁移和回切语义见 [`docs/host-migration.md`](docs/host-migration.md)。

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
INTERNAL_LAN_BIND_IP=192.168.2.34
CORS_ORIGINS=http://192.168.2.34:8080
POSTGRES_PASSWORD=<strong-random-password>
DATABASE_URL=postgresql+psycopg://exam:<same-url-encoded-password>@db:5432/internal_exam
PRIMARY_OPERATOR_USERNAME=<named-primary-operator>
PRIMARY_OPERATOR_PASSWORD=<strong-random-password>
BACKUP_OPERATOR_USERNAME=<named-backup-operator>
BACKUP_OPERATOR_PASSWORD=<different-strong-random-password>
BACKUP_OPERATOR_ENABLED=false
TOKEN_SECRET=<strong-random-secret>
CANDIDATE_LOGIN_EMAIL_DELIVERY_MODE=smtp
CANDIDATE_LOGIN_EMAIL_FROM=exam@example.internal
CANDIDATE_LOGIN_SMTP_HOST=smtp.example.internal
CANDIDATE_LOGIN_SMTP_PORT=587
CANDIDATE_LOGIN_SMTP_USERNAME=<smtp-user-if-required>
CANDIDATE_LOGIN_SMTP_PASSWORD=<smtp-password-if-required>
CANDIDATE_LOGIN_SMTP_USE_TLS=true
CANDIDATE_LOGIN_SMTP_USE_SSL=false
# 可选：账号 OTP 持久化限流与邀请发送边界按环境配置
# CANDIDATE_LOGIN_OTP_PER_EMAIL_LIMIT=...
# CANDIDATE_LOGIN_OTP_PER_SOURCE_LIMIT=...
# CANDIDATE_LOGIN_OTP_GLOBAL_LIMIT=...
# INVITATION_SEND_BATCH_LIMIT=...
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

## Docker Compose 启动（开发/验证）

以下命令用于开发或 disposable 验证，不代表正式宿主 promotion。当前 Mac 正式部署必须使用版本化 release 根目录和 [macos-deployment-operations.md](docs/macos-deployment-operations.md)，禁止直接从开发 checkout 作为 formal writer。

```bash
cp .env.example .env  # 首次启动前执行，并按目标 profile 替换配置
docker compose --env-file .env config --quiet
docker compose --env-file .env up -d --build
```

正式入口分离：

```text
http://192.168.2.34:8080
http://192.168.2.34:8080/api/health
http://127.0.0.1:8081/admin/login
http://127.0.0.1:8081/api/ready
http://127.0.0.1:8081/docs
```

Compose 会启动 PostgreSQL、后端、auto-submit worker、前端、应考人员 Nginx 和操作员 Nginx。后端容器启动时执行 `alembic upgrade head`。`internal` 必须把应考人员 8080 绑定到 `192.168.2.34`；操作员 8081、PostgreSQL 5432 和前端直连 5173 始终只绑定 loopback。普通办公设备与应考人员设备共用现有局域网，pf/主机防火墙仍须把 8080 限制在 `192.168.2.0/24`，禁止公网端口转发、访客网和未授权网段。

`internal` 的 HTTP 不会加密应考人员 bearer token 和考试数据；管理员只在主机本地 8081 操作。该残余风险已作为第一阶段例外接受，但不能描述为传输安全。完整数据范围、补偿控制和事件触发条件见 [`docs/security-http-exception.md`](docs/security-http-exception.md)。

学习视频文件保存在 Compose named volume `learning_media`，Nginx 通过 `/media/learning/` 只读提供播放，并启用匹配的 500 MiB 上传大小限制。正式备份必须同时覆盖 PostgreSQL 和 `learning_media`，并同步到独立加密第二存储。创建配对备份与隔离恢复校验的命令见 [`docs/macos-deployment-operations.md`](docs/macos-deployment-operations.md)。

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

仅用于丢弃本地开发空库的回退：

```bash
uv run alembic downgrade base
```

正式环境的账号/名单迁移必须先完成只读 conflict preflight、writer fence、写冻结、verified paired PostgreSQL/media backup、独立加密第二副本和隔离 restore。destructive migration 删除旧全局人员/出席字段后，禁止使用 `alembic downgrade` 伪造数据；唯一标准路径是停止所有 writer，用上一版本发布包 + 已验证配对备份执行 restore-only 回滚，再重做 migration/count/health/SMTP/UAT。详见 [`docs/official-exam-uat-checklist.md`](docs/official-exam-uat-checklist.md)、[`docs/macos-deployment-operations.md`](docs/macos-deployment-operations.md) 和 [`docs/host-migration.md`](docs/host-migration.md)。

## 测试和构建

后端快速测试（使用内存 SQLite）：

```bash
cd backend
uv run pytest
```

后端完整测试（推荐；从仓库根目录运行，使用独立临时 PostgreSQL，测试结束后自动销毁）：

```bash
./scripts/test-backend-full.sh
```

完整测试服务只监听 `127.0.0.1:55432`，数据库固定为
`internal_exam_test`，不会读取或清理当前部署使用的 `internal_exam`。

前端构建：

```bash
cd frontend
npm test -- --run
npm run lint
npm run build
npm run check:offline
```

真实浏览器和 100 客户端发布门禁：

```bash
sh ops/e2e/run-browser-gate.sh
sh ops/e2e/run-capacity-gate.sh
```

Docker 配置检查：

```bash
docker compose --env-file .env config --quiet
```

## 第一阶段已包含

- `/api/health` 存活检查和 `/api/ready` 数据库/媒体就绪检查
- 平台账号、题库、考试、考试记录、题目快照、答案、练习记录、导入批次 ORM 模型
- Alembic 迁移与既有数据兼容回填（当前 head `202608110001_email_accounts_and_invited_exam_scopes.py`）
- 用户/应考人员端和管理员端 API 路由
- 多选题集合判分服务和测试
- 用户端与管理员端 React 页面
- 独立视频学习模块：管理员本地上传/发布/归档学习视频，用户观看并记录 90% 完成进度
- 题库/考试/报表代表性 TanStack Table 页面
- 登录/导入/考试编辑代表性 React Hook Form + Zod 表单
- 题库 Excel 导入行级校验、合法题目入库、选项入库、导入批次记录
- 单场应考名单 Excel 导入按规范化邮箱复用/创建 pending 账号，写入 per-exam `exam_candidate_scope`，并冻结 roster identity
- 题库导入和单场名单导入均记录 `import_batch`，失败报告可下载 Excel 明细；独立全局账号/人员导入与模板已移除
- 考试配置创建、更新、管理端列表和 active scoped 用户列表入库，支持 `available_from` / `available_until` 开放窗口；已发布受邀考试立即可见但按时间门禁开始
- 考试从 draft 发布为 active 时同时冻结 `exam_question_pool` 与 roster；正式开始考试时只从该场 frozen pool 抽题
- 单场考试名单支持导入、冻结、邀请 initial-send、failed-only resend 和补考授权；已发布名单不可编辑或删除
- 开始考试时按 `question_rule` 生成固定 50 题等价试卷，题干去重、整数均分，创建 attempt 和题目快照，答案暂存入库，提交后按快照自动判分
- 考试结果返回及格线和通过状态，当前固定试卷规则为总分 100、及格线 60
- 到时自动提交后台检查、原子 heartbeat/容器健康检查、考试排名和管理端报表 SQL 查询
- 管理端报表支持按 `exam_id` 过滤，并导出为单个 Excel 工作簿，包含成绩报表、题目正确率、错题统计和参考状态
- 学习报表支持按视频和完成状态过滤，并导出 Excel
- 邮箱登录/注册使用六位、十分钟、单次 OTP（最多五次校验、60 秒重发冷却），按邮箱/来源/全局限流；active 账号获得四小时 token，pending/新邮箱先完成显示名称，inactive 账号需管理员 reactivation
- 账号 Profile 只允许编辑显示名称，规范化邮箱只读，不提供记住我、改邮箱、密码或物理删除；管理端可搜索并切换已完成账号 active/inactive
- 练习模式通过 `X-Candidate-Token` 识别 active 用户：题目列表提交前隐藏答案；提交后立即显示对错、正确答案、选项对比和解析；每次重做保留独立历史，并提供按账号隔离、分类可筛选的错题复习与掌握状态
- 管理员登录返回签名 session token，管理端 API 使用 `X-Admin-Token`
- Academic Editorial 前端 redesign：设计令牌、UI primitives、candidate/admin layouts、P0/P1/P2 页面、空态/错态/加载态和考试快捷键

## 当前边界

第一阶段的路由、页面和 service 边界已经建立，题库 Excel 导入、单场应考名单导入、失败报告、账号注册/Profile、考试配置、冻结 roster/题池、显式邀请发送、补考授权、固定 50 题试卷、开始考试快照、答案暂存、提交判分、自动提交、管理员排名、按考试过滤报表、报表导出、视频学习上传和学习完成报表已经具备入库/查询闭环。当前加固边界包含邮箱 OTP、具名主/备操作员、四小时 token、单设备 attempt session 与修订号、离线草稿、结果解析一次性发布、审计、保留/备份/恢复、发布与安全门禁，以及仅向 `192.168.2.34` 开放应考人员 8080、仅向本机开放操作员 8081 的双入口。系统仍保持轻量内部考试平台定位，不包含复杂 RBAC、多租户、完整 LMS、监考/防作弊、Word 导入、短信验证码、SSO、持久邮件队列、高可用或自动 HTTPS。

## 正式运行文档

- [`docs/macos-host-guide.md`](docs/macos-host-guide.md)：当前 Mac 宿主、designated host account、Docker AutoStart/Resource Saver、8 CPU/8 GiB、电源、固定 IP、pf 和证据要求。
- [`docs/macos-deployment-operations.md`](docs/macos-deployment-operations.md)：当前 Mac 版本化安装、staging、预检、发布、备份、恢复、诊断、回滚和 LaunchAgent 边界。
- [`docs/internal-deployment-operations.md`](docs/internal-deployment-operations.md)：internal profile 的共通运行合同、Mac 命令入口和 Windows 迁移门禁。
- [`docs/host-migration.md`](docs/host-migration.md)：Mac↔Windows paired-backup、source stop、single-writer、回滚和切换语义。
- [`docs/windows-host-guide.md`](docs/windows-host-guide.md)：未来 Windows Docker Desktop + WSL2 target，不是当前正式宿主。
- [`docs/exam-day-guide.md`](docs/exam-day-guide.md)：应考人员、主/备操作员、设备接管、离线草稿、解析发布和练习规则。
- [`docs/official-exam-uat-checklist.md`](docs/official-exam-uat-checklist.md)：当前 Mac + 桌面/手机 UAT 和证据清单（Mac 证据不满足 Windows acceptance）。
