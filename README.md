<p align="center">
  <img src="./frontend/public/favicon.svg" width="72" alt="知试标志">
</p>

<h1 align="center">知试 · Internal Exam Platform</h1>

<p align="center">
  面向受控内部场景的轻量学习、练习与正式考试平台。<br>
  用冻结名单、冻结题池和作答快照，把一次考试变成可恢复、可复核的完整记录。
</p>

<p align="center">
  <code>React 19</code> · <code>FastAPI</code> · <code>PostgreSQL</code> · <code>Docker Compose</code> · <code>Nginx</code>
</p>

<p align="center">
  <a href="#快速启动">快速启动</a> ·
  <a href="#产品闭环">产品闭环</a> ·
  <a href="#关键契约">关键契约</a> ·
  <a href="#验证">验证</a> ·
  <a href="#正式运行">正式运行</a>
</p>

> [!IMPORTANT]
> **当前状态：**业务闭环与本地工程门禁已实现；正式 Mac 宿主验收尚未完成，不能据此批准开考。缺失证据与下一步以 [`docs/handoff.md`](docs/handoff.md) 为准。

<p align="center">
  <img src="./assets/readme/zhishi-frozen-record.webp" width="360" alt="知试概念海报：一份带答题格、计时条与红色封存章的考试记录，象征冻结题池和作答快照">
</p>

<p align="center">
  <sub>概念海报 · Frozen examination record。它表达快照语义，不是产品截图；实际验证见 <a href="./docs/handoff.md">handoff</a>，或<a href="./assets/readme/source/zhishi-frozen-record-prompt.md">查看制作配方</a>。</sub>
</p>

## 产品闭环

### 用户与应考人员

- 通过规范化邮箱申请六位 OTP；首次验证后填写显示名称，active 账号获得四小时 session。
- 独立完成视频学习、日常练习和错题复习；学习完成度不影响正式考试资格或成绩。
- 只看到自己已被加入并冻结名单的正式考试；支持开考前提示、答案自动暂存、断线草稿恢复、单设备接管、到时自动交卷和补考。
- 交卷后立即看到分数与通过状态；答案和解析由操作员在全部记录结束后一次性发布。

### 主操作员与备份操作员

- 通过标准化 Excel 导入题库与单场考试名单，并下载逐行失败报告。
- 配置考试、检查发布条件、冻结名单和题池，再显式发送邀请；发布考试本身不会自动发邮件。
- 处理异常 attempt、预览并发放补考、发布结果解析、管理账号和学习视频。
- 按考试查看成绩、正确率、错题与缺考状态，并导出多 Sheet Excel；学习报表独立统计。

```text
题库 Excel + 单场名单 Excel
        ↓
配置考试 → 发布并冻结 roster / question pool → 显式发送邀请
        ↓
邮箱 OTP → 开始 / 恢复 attempt → 暂存 → 提交或到时自动提交
        ↓
快照判分 → 成绩与通过状态 → 解析发布 → 报表 / 备份 / 审计
```

## 关键契约

- **单场授权：**active 账号可以学习和练习；正式考试还必须拥有对应的 per-exam scope。显示名称变化不会改写冻结名单或历史报表。
- **发布冻结：**考试发布时同时冻结 `exam_question_pool` 与 roster；发布后名单不可编辑或删除，邀请发送是独立显式动作。
- **快照判分：**每个 attempt 保存题目、选项、正确答案、解析、分值和顺序快照；历史成绩不依赖后来变化的题库。多选题按答案集合比较，而不是比较字符串顺序。
- **固定试卷：**管理端新建模板默认 50 题 / 100 分 / 60 分及格，题型为 30 单选 + 10 多选 + 10 判断；非空 `question_rule` 支持自定义题数、总分和题型计数，空对象 `{}` 保留 legacy all-active 语义。
- **保存与接管：**答案按 revision 暂存；session-scoped 离线草稿不会暂停倒计时，新 OTP 接管会使旧设备保存失败。
- **结果发布：**分数和通过状态交卷后立即可见；答案解析只能在全部 attempt 结束后由操作员一次性发布。

## 快速启动

需要 Docker Desktop（或兼容 Docker Engine）与支持 `docker compose up --wait` 的 Docker Compose v2。仓库根目录的 [`.env.example`](.env.example) 仅包含本机开发默认值。

```bash
# 仅首次初始化；已有 .env 时不要覆盖
cp .env.example .env

docker compose --env-file .env config --quiet
docker compose --env-file .env up --detach --build --wait
docker compose --env-file .env ps
```

默认开发入口：

| 用途 | 地址 |
| --- | --- |
| 用户端 | `http://127.0.0.1:28080` |
| 操作员登录 | `http://127.0.0.1:28081/admin/login` |
| 存活检查 | `http://127.0.0.1:28080/api/health` |
| 就绪检查 | `http://127.0.0.1:28081/api/ready` |
| OpenAPI | `http://127.0.0.1:28081/docs` |

PostgreSQL 与前端直连端口分别为 `127.0.0.1:25432` 和 `127.0.0.1:25173`；后端 `8000` 只在单独运行 Uvicorn 时对宿主开放。候选入口不会暴露 admin、operations、readiness 详情、docs 或 OpenAPI。

> [!NOTE]
> `.env.example` 默认使用 `memory` OTP，适合自动化测试，但不会把验证码投递到真实邮箱。手工验证候选人登录前，请在本地 `.env` 配置可用 SMTP；开发管理员凭据则直接来自该文件。不要提交 `.env`。

停止开发栈而保留数据卷：

```bash
docker compose --env-file .env down
```

## 运行配置

| Profile | 场景 | 入口与约束 |
| --- | --- | --- |
| `development` | 本机开发、自动化测试 | 默认全部 loopback；允许示例凭据和 `memory` OTP |
| `internal` | 受控私有局域网内的正式内部考试 | 候选端使用显式私网 IP 的 HTTP；强凭据、精确 CORS、SMTP 与正式运维证据必填 |
| `production` | 外部 HTTPS 部署 | 只接受 HTTPS origin；仓库内 Nginx 不负责 TLS 终止，需要外部可信 HTTPS 层 |

正式 `internal` 网络字段的关系如下；这不是完整配置，也不能在地址获批前直接复制使用：

```dotenv
ENVIRONMENT=internal
INTERNAL_LAN_BIND_IP=<FORMAL_LAN_IP>
CANDIDATE_GATEWAY_PORT=8080
OPERATOR_GATEWAY_PORT=8081
CORS_ORIGINS=http://<FORMAL_LAN_IP>:8080
CANDIDATE_PUBLIC_BASE_URL=http://<FORMAL_LAN_IP>:8080
CANDIDATE_LOGIN_EMAIL_DELIVERY_MODE=smtp
```

全部字段、速率限制、SMTP、媒体和持久化路径以 [`.env.example`](.env.example) 为准。正式配置应保存在受保护的宿主根目录中，而不是开发 checkout。

## 功能边界

### 导入与学习媒体

- 仓库模板与已验证的导入格式为 `.xlsx`（legacy `.xls` 未验证），后端基于 openpyxl 读取工作簿；不解析 Word。默认单文件上限 5 MiB、5000 行、1 个工作表。
- 题库导入和单场 roster 导入都会记录 `import_batch`；有效行入库，错误行可导出 Excel。
- 学习视频支持 `mp4` / `webm`，默认单文件上限 500 MiB；完成阈值为 90%。
- 正式备份必须把 PostgreSQL 与 `learning_media` 作为配对数据处理，并验证独立第二副本恢复。

### 有意保持轻量

本阶段不包含复杂 RBAC、多租户、完整 LMS、Word 导入、短信 OTP、SSO、Redis / Celery、持久邮件队列、高可用、自动 HTTPS 或完整监考/防作弊。练习与正式考试共享 active 题库；`internal` HTTP 是已记录的局域网例外，不是传输安全。

## 验证

后端静态检查与快速测试：

```bash
cd backend
uv sync
uv run ruff format . --check
uv run ruff check .
uv run ty check
uv run pytest
cd ..
```

包含迁移与并发用例的 disposable PostgreSQL 全量测试：

```bash
./scripts/test-backend-full.sh
```

前端检查：

```bash
cd frontend
npm install
npm run format:check
npm test -- --run
npm run lint
npm run build
npm run check:offline
cd ..
```

本地 disposable 浏览器与 100-client 工程门禁：

```bash
sh ops/e2e/run-browser-gate.sh
sh ops/e2e/run-capacity-gate.sh
```

浏览器门禁使用隔离栈和 fake SMTP；容量门禁要求干净、可识别的 Git revision。两者都不会替代 designated host 上的真实 SMTP、桌面/手机、网络、防火墙、重启与恢复证据。

## 正式运行

当前正式目标是 **Apple Silicon macOS + Docker Desktop + Docker Compose**。正式根目录默认位于工作树外的 `${HOME}/Library/Application Support/InternalExam`；考试窗口内停止 development / staging，任何时刻只允许一个 formal writer。容器健康或 LaunchAgent 恢复都不等于批准开考，最终决定必须由操作员完成预检后人工给出。

正式宿主当前仍待完成 LAN 地址预留与批准、版本化 release 安装、正式 staging / promotion、正式宿主 SMTP、桌面/手机 UAT、LaunchAgent 恢复，以及独立加密第二副本恢复；这些都是阻断验收项，不是已通过证据。

正式 LAN 地址目前必须写作 `<FORMAL_LAN_IP>`，直到网络管理员完成未占用地址的 DHCP reservation。不要复用历史文档或本地 UAT 中出现过的临时地址。地址获批后，入口合同为：

```text
应考人员  http://<FORMAL_LAN_IP>:8080
操作员    http://127.0.0.1:8081/admin/login
```

`internal` 模式通过共享办公 LAN 使用 HTTP，候选 token、题目、答案与结果不具备传输加密；其使用范围和补偿控制必须持续满足已接受的安全例外。未来 Windows Docker Desktop + WSL2 只是迁移目标，必须重新完成 native AMD64 staging、配对备份恢复、网络、SMTP、浏览器、容量与人工 promotion，不能复用 Mac 证据。

正式操作从以下文档进入：

- [macOS 宿主准备](docs/macos-host-guide.md)
- [macOS release、staging、promotion、备份与恢复](docs/macos-deployment-operations.md)
- [正式考试 UAT 清单](docs/official-exam-uat-checklist.md)
- [考试日操作指南](docs/exam-day-guide.md)
- [局域网 HTTP 安全例外](docs/security-http-exception.md)（范围原则；具体地址以当前 Mac host guide / handoff 为准）
- [主机迁移与 single-writer 语义](docs/host-migration.md)
- [当前验证状态与 Known Gaps](docs/handoff.md)

## 代码地图

```text
backend/app/api/       薄路由与 /api 聚合
backend/app/services/  考试、导入、学习、报表与运维业务逻辑
backend/app/schemas/   Pydantic 请求 / 响应契约
frontend/src/api/      前端 API client
frontend/src/pages/    用户端与操作员页面
frontend/src/features/  考试作答工作区与状态 hooks
nginx/                 候选端 / 操作员双入口边界
ops/                   E2E、容量、安全、macOS 与未来 Windows 运维工具
docs/                  需求、数据库、API、模板、UAT 与交接文档
```

进一步阅读：[`docs/requirements.md`](docs/requirements.md) · [`docs/database-design.md`](docs/database-design.md) · [`docs/api-design.md`](docs/api-design.md) · [`docs/import-templates.md`](docs/import-templates.md)。API 路由的运行时真值以 [`backend/app/api/router.py`](backend/app/api/router.py) 及对应 route 文件为准；部署地址与验收状态以本页“正式运行”所列 Mac 文档和 handoff 为准。

## License

[MIT](LICENSE) © 2026 Alune
