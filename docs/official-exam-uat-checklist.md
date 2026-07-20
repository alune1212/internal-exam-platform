# Official Exam UAT Checklist

正式考试前通过 Docker/Nginx 入口 `http://<INTERNAL_LAN_BIND_IP>:8080` 跑一遍。目标是验证主链和单机运维恢复能力，不扩展成完整 LMS 验收。

## Preflight

### Internal 配置与网络边界

- `.env` 使用 `ENVIRONMENT=internal`。
- `INTERNAL_LAN_BIND_IP` 是部署主机固定私网 IP，不能是 `0.0.0.0`、loopback、link-local 或公网 IP。
- `CORS_ORIGINS` 精确为 `http://<INTERNAL_LAN_BIND_IP>:8080`，不使用 `*`、localhost 或额外 origin。
- `POSTGRES_PASSWORD`、`DATABASE_URL`、`ADMIN_PASSWORD` 和 `TOKEN_SECRET` 已替换示例值；数据库 URL 中的密码与 `POSTGRES_PASSWORD` 一致并正确 URL encode。
- `CANDIDATE_LOGIN_EMAIL_DELIVERY_MODE=smtp`，sender、证书匹配的 host、port、所需 SMTP 凭据和传输模式均已配置；STARTTLS 使用 `USE_TLS=true`，隐式 SSL 使用 `USE_SSL=true`，两者不得同时启用。
- 主机防火墙只允许受控考试子网访问 `<INTERNAL_LAN_BIND_IP>:8080`；`5432` 和 `5173` 只允许本机 loopback。访客 Wi-Fi、公网端口转发和不受控网段必须禁用。
- 已书面接受局域网 HTTP 不加密 bearer token 的残余风险；如果网络或使用范围扩大，停止 `internal` 部署并先升级 HTTPS。

### Automated gates

```bash
cp .env.example .env  # 首次执行；正式环境必须替换里面的口令和密钥
cd backend
uv run ruff format . --check
uv run ruff check .
uv run ty check
uv run pytest
cd ../frontend
npm run format:check
npm test -- --run
npm run lint
npm run build
cd ..
docker compose --env-file .env config --quiet
docker compose --env-file .env up -d --build
docker compose --env-file .env exec -T backend uv run alembic upgrade head
docker compose --env-file .env exec -T nginx nginx -t
docker compose ps
curl -f http://<INTERNAL_LAN_BIND_IP>:8080/api/health
curl -f http://<INTERNAL_LAN_BIND_IP>:8080/api/ready
curl -f http://<INTERNAL_LAN_BIND_IP>:8080/docs
```

`docker compose ps` 中 db、backend 和 auto-submit-worker 必须为 healthy，Nginx 必须已启动。`/api/health` 只证明进程存活，`/api/ready` 才证明 PostgreSQL 与 `learning_media` 可用。Compose 使用 `.env` 里的 `db` 主机名连接数据库，后端 `8000` 只暴露给容器网络；Docker/Nginx UAT 统一走 `<INTERNAL_LAN_BIND_IP>:8080`。

如果目标是 `production` 而非 `internal`，必须改用正式 HTTPS origin；production 会拒绝非 HTTPS CORS、localhost、`127.0.0.1`、`0.0.0.0`、示例密钥和空 SMTP。

如需调整导入预算，显式配置 `IMPORT_MAX_UPLOAD_BYTES`、`IMPORT_MAX_ROWS`、`IMPORT_MAX_SHEETS`；默认是 5 MiB、5000 行、1 个工作表。

## Browser Flow

1. 在允许的局域网设备打开 `http://<INTERNAL_LAN_BIND_IP>:8080/exams`，在没有考试人 session 时确认返回登录页，且不会渲染考试列表。
2. 打开 `http://<INTERNAL_LAN_BIND_IP>:8080/admin/login`，管理员登录成功。
3. 导入一份包含失败行的题库 Excel，确认结果页显示失败行，并能下载失败报告。
4. 导入一份包含失败行的应考名单 Excel，确认结果页显示失败行，并能下载失败报告。
5. 新建或编辑考试，配置 `available_from` / `available_until`、时长、固定试卷规则。
6. 进入单场考试名单页，导入名单，确认成功/失败统计和失败报告下载。
7. 发布考试为 active，确认列表显示发布状态、开放窗口、冻结题池数量。
7a. 候选人登录页用未登记的姓名/邮箱组合请求验证码，确认页面**不**直接报错，而是进入验证码输入步骤并显示「未收到可等待冷却后重发」提示；同时后端日志应有 `event=candidate_login.unknown_identity` 的 WARN。
7b. 候选人登录页用重复姓名（多条同名记录）请求验证码，确认页面行为与未登记身份一致（一致化 200 响应，不暴露歧义）。
8. 用名单内考试人的姓名和邮箱触发真实 SMTP，确认邮件到达、输入验证码后打开考试列表；检查 backend 日志只记录 challenge id、attempt 和 error type，不包含 OTP、收件邮箱、姓名、员工号或 SMTP 凭据。
9. 在开放窗口前确认显示未开始且不可新开考。
10. 到开放窗口内进入考试，确认题目来自 frozen pool，题数/总分符合规则。
11. 暂存答案，刷新页面，确认已有 attempt 可继续。
12. 交卷，确认结果页显示分数、是否通过；若考试关闭答案回看，确认不显示答案解析。
13. 在管理端名单页为该考试人授权补考，确认考试人端重新出现该考试并能生成新的补考 attempt。
14. 在开放窗口结束后刷新已有进行中 attempt，确认仍可继续，倒计时仍按 `started_at + duration_minutes`。
15. 回到管理端报表，选择该考试，确认成绩、题目正确率、错题排行、参考状态不混入其他考试，并以该考试的当前参考 attempt 为准。
16. 导出当前考试报表，确认 Excel 包含个人成绩、题目正确率、错题排行、参考状态四个 sheet。

## Worker Interruption Recovery

使用一场短时长测试考试创建进行中 attempt，确保它在 worker 停止期间到期：

```bash
docker compose --env-file .env stop auto-submit-worker
# 等待该测试 attempt 超时
docker compose --env-file .env start auto-submit-worker
docker compose --env-file .env ps
```

确认 worker 首次成功扫描后恢复 healthy，超时 attempt 被自动提交；再次扫描不会重复提交已完成 attempt。若数据库扫描持续失败超过 `AUTO_SUBMIT_HEARTBEAT_MAX_AGE_SECONDS`，worker 必须变为 unhealthy，数据库恢复后的成功扫描必须刷新 heartbeat。

## Paired Backup And Restore Gate

在无进行中考试、无视频上传和无管理员数据修改的维护窗口，按 [`internal-deployment-operations.md`](internal-deployment-operations.md) 完成以下证据：

1. 创建同一时间戳目录下的 PostgreSQL dump 与 `learning_media` archive。
2. 确认 manifest、`SHA256SUMS` 和最后写入的 `SUCCESS` 存在。
3. 停止正式 stack，使用唯一 `internal-exam-restore-verify-*` project 完成隔离恢复校验。
4. 确认 migration head、代表性表计数、媒体文件数和非空媒体样本一致。
5. 确认临时容器/volume 已清理，重新启动正式 stack，backend 和 worker 恢复 healthy。

## Stop Conditions

- 失败报告无法下载或缺少批次元信息。
- 发布后题库修改影响已发布考试抽题。
- 考试窗口结束后可以新开考。
- 已开始 attempt 因 `available_until` 结束无法恢复。
- 补考授权后考试人无法重新进入考试，或补考未生成新的 attempt。
- 报表默认混入其他考试数据。
- 无考试人 session 访问 `/exams` 时渲染考试列表，或触发 `/api/exams/active` 匿名请求。
- Docker/Nginx `8080` 健康检查失败。
- `/api/health` 成功但 `/api/ready` 返回 503，或 backend/worker 任一容器不是 healthy。
- 真实 SMTP 邮件未到达、最终投递失败不可观测，或日志包含 OTP、收件邮箱、提交身份和 SMTP 凭据。
- worker 重启后未补交超时 attempt、重复提交已完成 attempt，或数据库失败后 heartbeat 仍被刷新。
- 主机 `8080` 可从访客 Wi-Fi、公网或未授权网段访问。
- 配对备份缺少 `SUCCESS`/checksum，隔离恢复的迁移版本、表计数或媒体检查不一致，或临时资源未清理。
