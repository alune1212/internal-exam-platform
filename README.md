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
> **已正式上线（2026-09-08）：**公司内网单机 Mac 部署已完成真实邮件、手机答题和整机重启验收。使用入口见[正式运维手册](docs/minimal-macos-deployment.md)，部署版本与验收结果见[上线交接](docs/handoff.md)。

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
快照判分 → 成绩与通过状态 → 解析发布 → 报表 / 审计
```

## 关键契约

- **单场授权：**active 账号可以学习和练习；正式考试还必须拥有对应的 per-exam scope。显示名称变化不会改写冻结名单或历史报表。
- **发布冻结：**考试发布时同时冻结 `exam_question_pool` 与 roster；发布后名单不可编辑或删除，邀请发送是独立显式动作。
- **快照判分：**每个 attempt 保存题目、选项、正确答案、解析、分值和顺序快照；历史成绩不依赖后来变化的题库。多选题按答案集合比较，而不是比较字符串顺序。
- **固定试卷：**管理端新建模板默认 50 题 / 100 分 / 60 分及格，题型为 30 单选 + 10 多选 + 10 判断；非空 `question_rule` 支持自定义题数、总分和题型计数，空对象 `{}` 保留 legacy all-active 语义。
- **保存与接管：**答案按 revision 暂存；session-scoped 离线草稿不会暂停倒计时，新 OTP 接管会使旧设备保存失败。
- **结果发布：**分数和通过状态交卷后立即可见；答案解析只能在全部 attempt 结束后由操作员一次性发布。

## 快速启动

以下仅启动开发环境。正式环境已运行，日常启停按[正式运维手册](docs/minimal-macos-deployment.md)执行。同机并行开发须先调整开发 PostgreSQL 和前端直连端口，避免与正式栈冲突。

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
| `internal` | 受控私有局域网内的正式内部考试 | 候选端使用显式私网 IP 的 HTTP；强凭据、精确 CORS、真实 SMTP；当前已上线配置 |
| `production` | 外部 HTTPS 部署 | 只接受 HTTPS origin；仓库内 Nginx 不负责 TLS 终止，需要外部可信 HTTPS 层 |

正式网络、目录和启停命令统一维护在[正式运维手册](docs/minimal-macos-deployment.md)。字段定义以 [`.env.example`](.env.example) 和后端配置校验为准；正式 `formal.env` 保存在受保护的宿主目录，凭据不进入 Git。

## 功能边界

### 导入与学习媒体

- 仓库模板与已验证的导入格式为 `.xlsx`（legacy `.xls` 未验证），后端基于 openpyxl 读取工作簿；不解析 Word。默认单文件上限 5 MiB、5000 行、1 个工作表。
- 题库导入和单场 roster 导入都会记录 `import_batch`；有效行入库，错误行可导出 Excel。
- 学习视频支持 `mp4` / `webm`，默认单文件上限 500 MiB；完成阈值为 90%。
- 数据库和视频使用持久卷。当前未启用备份、第二副本和恢复演练，因此没有经过验证的数据恢复保障。

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

浏览器门禁使用隔离栈和 fake SMTP，默认脚本包含测试库备份步骤；本次上线验收省略了该步骤。容量门禁要求干净、可识别的 Git revision，属于工程复验工具；当前上线已完成的检查以[上线交接](docs/handoff.md)为准。

## 正式运行

当前已在公司受控局域网正式上线。用户入口为 `http://192.168.2.225:8080`，管理入口仅在 Mac 本机开放：`http://127.0.0.1:8081/admin/login`。

- [正式运维手册](docs/minimal-macos-deployment.md)：主机、配置、首次部署及日常启停的唯一操作入口。
- [上线交接](docs/handoff.md)：当前部署身份、已完成验收及未启用范围的唯一状态记录。
- [考试日操作指南](docs/exam-day-guide.md)：准备题目和名单、发布考试、处理答题及成绩。
- [实机验收清单](docs/official-exam-uat-checklist.md)：本次结果与后续变更的复验动作。
- [局域网 HTTP 安全例外](docs/security-http-exception.md)：内网 HTTP 的适用边界。
- [OpenSpec 导航](openspec/README.md)：当前规格、未采用的完整运维方案及历史归档。

发布包签名、备份、第二副本和恢复演练未纳入本次上线；旧 Windows、签名发布和跨主机迁移手册已退出当前文档，历史背景保留在 OpenSpec 与 Git 中。现有相关工具仍保留，但不用于当前生产启停。

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

进一步阅读：[`docs/requirements.md`](docs/requirements.md) · [`docs/database-design.md`](docs/database-design.md) · [`docs/api-design.md`](docs/api-design.md) · [`docs/import-templates.md`](docs/import-templates.md)。API 路由的运行时真值以 [`backend/app/api/router.py`](backend/app/api/router.py) 及对应 route 文件为准；文档分工与当前状态以本页“正式运行”的导航为准。

## License

[MIT](LICENSE) © 2026 Alune
