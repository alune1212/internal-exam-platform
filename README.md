<p align="center">
  <img src="./frontend/public/favicon.svg" width="72" alt="知试标志">
</p>

<h1 align="center">知试 · ZHISHI</h1>

<p align="center">
  面向公司内部的视频学习、日常练习与正式考试平台。<br>
  考试发布时冻结名单和题池，作答时保存快照，支持中断续答和成绩复核。
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

<p align="center">
  <img src="./assets/readme/zhishi-frozen-record.webp" width="360" alt="知试概念海报：一份带答题格、计时条与红色封存章的考试记录，象征冻结题池和作答快照">
</p>

<p align="center">
  <sub>概念海报 · Frozen examination record，以封存的考试记录表现作答快照。非产品截图。验收结果见 <a href="./docs/handoff.md">handoff</a>，或<a href="./assets/readme/source/zhishi-frozen-record-prompt.md">查看海报提示词</a>。</sub>
</p>

## 产品闭环

### 用户与应考人员

- 使用邮箱申请六位验证码。系统统一规范邮箱格式；首次验证后填写显示名称，启用的账号可登录，会话有效期为四小时。
- 支持视频学习、日常练习和错题复习。学习完成度不影响正式考试资格或成绩。
- 应考人员仅可查看本人已列入冻结名单的正式考试。平台支持开考前提示、答案自动保存、断网后恢复草稿、设备接管、到时自动交卷和补考。
- 交卷后即可查看分数和通过状态。全部作答记录结束后，操作员可以一次性发布答案和解析。

### 主操作员与备份操作员

- 按 Excel 模板导入题库和单场考试名单，下载包含各行错误原因的失败报告。
- 配置考试并检查发布条件，发布时固定名单和题池。邀请邮件需要单独发送，发布考试不会自动发邮件。
- 处理异常作答记录，预览并发放补考，发布答案解析，管理账号和学习视频。
- 按考试查看成绩、正确率、错题和缺考情况，导出包含多个工作表的 Excel 文件。学习情况通过独立报表统计。

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

- 启用的账号可以学习和练习，参加正式考试还需要该场考试的名单授权。修改显示名称不会改写冻结名单或历史报表。
- 发布考试时同时冻结题池 `exam_question_pool` 和名单。发布后不能编辑或删除名单，邀请邮件仍需单独发送。
- 每次作答保存题目、选项、正确答案、解析、分值和顺序快照，后续题库变化不会影响历史成绩。多选题比较答案集合，选项顺序不影响判分。
- 管理端新建模板默认为 50 题、100 分、60 分及格，包含 30 道单选、10 道多选和 10 道判断题。非空 `question_rule` 可自定义题数、总分和各题型数量；空对象 `{}` 沿用全部启用题目的规则。
- 答案按修订号保存，离线草稿只保存在当前会话中，断网不会暂停倒计时。通过新的邮箱验证码接管考试后，旧设备无法继续保存答案。
- 交卷后立即显示分数和通过状态。操作员需等全部作答记录结束后才能发布答案解析，且只能发布一次。

## 快速启动

以下步骤用于启动开发环境。正式环境按[正式运维手册](docs/minimal-macos-deployment.md)启停。在同一台 Mac 上开发时，先调整开发环境的 PostgreSQL 和前端直连端口，避免占用正式环境的端口。

需要 Docker Desktop（或兼容的 Docker Engine），以及支持 `docker compose up --wait` 的 Docker Compose v2。仓库根目录的 [`.env.example`](.env.example) 仅包含本机开发默认值。

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

PostgreSQL 与前端直连端口分别为 `127.0.0.1:25432` 和 `127.0.0.1:25173`；后端 `8000` 只在单独运行 Uvicorn 时对宿主开放。考生入口不开放管理接口、运维接口、就绪详情、API 文档和 OpenAPI。

> [!NOTE]
> `.env.example` 默认使用 `memory` OTP，适合自动化测试，但不会把验证码投递到真实邮箱。手动测试考生登录前，先在本地 `.env` 配置可用的 SMTP。开发环境的管理员凭据也从该文件读取。不要提交 `.env`。

停止开发环境并保留数据卷：

```bash
docker compose --env-file .env down
```

## 运行配置

| 运行模式 | 使用场景 | 配置要求 |
| --- | --- | --- |
| `development` | 本机开发、自动化测试 | 默认只监听本机；允许示例凭据和 `memory` OTP |
| `internal` | 受控私有局域网内的正式内部考试 | 考生通过指定私网 IP 使用 HTTP，须配置强凭据、精确 CORS 和真实 SMTP |
| `production` | 外部 HTTPS 部署 | 只接受 HTTPS 来源地址；须由外部可信服务处理 TLS，仓库内 Nginx 不处理 TLS |

正式网络、目录和启停命令统一维护在[正式运维手册](docs/minimal-macos-deployment.md)。字段定义见 [`.env.example`](.env.example)，有效值由后端校验。正式 `formal.env` 保存在受保护的主机目录中，凭据不提交到 Git。

## 功能边界

### 导入与学习媒体

- 导入使用仓库中的 `.xlsx` 模板，旧版 `.xls` 尚未验证。后端通过 openpyxl 读取工作簿，不解析 Word。默认单文件上限 5 MiB、5000 行、1 个工作表。
- 题库和单场考试名单导入都会记录 `import_batch`。有效行保存到数据库，错误行可导出为 Excel。
- 学习视频支持 `mp4` / `webm`，默认单文件上限 500 MiB；学习完成阈值为 90%。
- 数据库和视频使用持久卷。当前未启用备份、第二副本和恢复演练，因此没有经过验证的数据恢复保障。

### 暂不支持的功能

平台暂不支持复杂 RBAC、多租户、完整 LMS、Word 导入、短信 OTP、SSO、Redis / Celery、持久邮件队列、高可用、自动 HTTPS 或完整监考/防作弊。练习与正式考试共用启用的题库。`internal` 模式采用已记录的局域网 HTTP 例外，不提供传输加密。

## 验证

以下命令用于源码验证，各版本的实际结果见[上线交接](docs/handoff.md)。

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

使用可丢弃的 PostgreSQL 实例运行全量测试，包含迁移和并发用例：

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

在本地隔离环境中运行浏览器测试和 100 客户端容量检查：

```bash
sh ops/e2e/run-browser-gate.sh
sh ops/e2e/run-capacity-gate.sh
```

浏览器测试使用隔离环境和模拟 SMTP，默认脚本包含测试库备份步骤。容量检查要求工作区干净且 Git 提交可追溯。部署版本、源码发布版本及各自的验收结果见[上线交接](docs/handoff.md)。

## 正式运行

正式环境运行于公司受控局域网内的单台 Mac。考生入口为 `http://192.168.2.225:8080`，管理入口仅在 Mac 本机开放：`http://127.0.0.1:8081/admin/login`。本仓库的 v1.0.0 源码发布与现网版本分离；本次源码发布不升级正式主机，现网提交仍以[上线交接](docs/handoff.md)记录为准。

- [正式运维手册](docs/minimal-macos-deployment.md)：统一维护主机配置、首次部署和日常启停步骤。
- [上线交接](docs/handoff.md)：统一记录部署版本、验收结果和未启用的功能。
- [考试日操作指南](docs/exam-day-guide.md)：准备题目和名单、发布考试、处理答题及成绩。
- [实机验收清单](docs/official-exam-uat-checklist.md)：查看验收结果的入口，以及后续变更的复验步骤。
- [局域网 HTTP 安全例外](docs/security-http-exception.md)：内网 HTTP 的适用边界。
- [OpenSpec 导航](openspec/README.md)：当前规格、未采用的完整运维方案及历史归档。

正式环境未启用发布包签名、备份、第二副本和恢复演练。完整签名/备份运维链、Windows 部署和跨主机迁移不属于 v1.0.0 支持路径；历史要求和未完成验收保留在 OpenSpec 与 Git 中。

## 代码地图

```text
backend/app/api/       薄路由与 /api 聚合
backend/app/services/  考试、导入、学习、报表与运维业务逻辑
backend/app/schemas/   Pydantic 请求 / 响应契约
frontend/src/api/      前端 API client
frontend/src/pages/    用户端与操作员页面
frontend/src/features/  考试作答工作区与状态 hooks
nginx/                 候选端 / 操作员双入口边界
ops/                   E2E、容量、安全及共享数据保护工具
docs/                  需求、数据库、API、模板、UAT 与交接文档
```

进一步阅读：[`docs/requirements.md`](docs/requirements.md) · [`docs/database-design.md`](docs/database-design.md) · [`docs/api-design.md`](docs/api-design.md) · [`docs/import-templates.md`](docs/import-templates.md)。核对实际 API 路由时，以 [`backend/app/api/router.py`](backend/app/api/router.py) 及对应路由文件为准。其他文档的用途和当前状态见本页“正式运行”中的导航。

## License

[MIT](LICENSE) © 2026 Alune
