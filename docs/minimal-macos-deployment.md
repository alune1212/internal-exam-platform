# Mac 正式运维手册

平台已于 2026-09-08 在公司受控局域网正式上线。本文件是当前生产操作的唯一手册；部署版本和验收结论以[上线交接](handoff.md)为准。

## 主机、入口与配置

| 项目 | 配置 |
| --- | --- |
| 主机 | 当前 Apple Silicon Mac，固定内网 IP `192.168.2.225` |
| 考生入口 | `http://192.168.2.225:8080` |
| 管理入口 | 本机 `http://127.0.0.1:8081/admin/login` |
| Compose 项目名 | `internal-exam-minimal`，保持固定以使用同一组数据卷 |
| 保护目录 | `~/Library/Application Support/InternalExamMinimal` |
| 源码与配置 | 保护目录下 `release/` 为固定源码导出，`formal.env` 权限为 `0600` |
| 操作员 | `operator`；口令读取 `formal.env` 中 `PRIMARY_OPERATOR_PASSWORD` |

`formal.env` 使用 `internal` 模式和真实 SMTP，CORS 与公开链接均匹配考生入口；正式数据库、操作员和 Token 使用独立随机凭据。Token 签名仍是登录保护的一部分，与未启用的发布包签名不同。数据库及前端直连仅绑定 loopback 的 `25432`、`25173`；backend 和 worker 不暴露宿主端口。

Docker Desktop 已设置登录自启动、关闭 Resource Saver；Mac 接交流电时不自动睡眠。考试期间保持主机开机、联网及 Docker 运行。整机重启后需要登录 macOS；当前方案不承诺登录前恢复或无人值守高可用。

## 日常检查与启停

```bash
cd "$HOME/Library/Application Support/InternalExamMinimal/release"
docker compose --env-file ../formal.env ps
curl -f http://192.168.2.225:8080/api/health
curl -f http://127.0.0.1:8081/api/ready
docker compose --env-file ../formal.env exec -T auto-submit-worker \
  uv run --no-sync python -m app.core.auto_submit_worker healthcheck
```

日常启动或异常恢复使用固定镜像：

```bash
docker compose --env-file ../formal.env up -d --no-build --wait
```

确认没有进行中的考试后，暂停使用 `docker compose --env-file ../formal.env stop`。查看错误使用 `docker compose --env-file ../formal.env logs --tail 100 backend auto-submit-worker`，分享日志前去除敏感信息。`down --volumes` 会删除数据，不能作为启停命令。

容器配置了自动重启。若 Mac 重启后服务未恢复，先确认已登录、Docker 已就绪以及 IP 未变化，再运行上述检查和启动命令。业务开考前按[考试日指南](exam-day-guide.md)检查名单、题目及开放时间。

## 首次安装与版本更新

当前生产已经初始化，下面仅解释首次全新空库的步骤，日常启停无需重复执行：

1. 将已经验证的明确 Git 提交导出至新主机的受保护 `release/` 目录，准备该主机独立的 `formal.env`。
2. 设置匹配源码提交的 `GIT_COMMIT` 和唯一 `APP_VERSION_TAG`；从该目录构建 `db backend frontend nginx` 镜像。
3. 启动数据库后，只对全新空库执行显式初始化，再启动其他服务：

```bash
docker compose --env-file ../formal.env config --quiet
docker compose --env-file ../formal.env build db backend frontend nginx
docker compose --env-file ../formal.env up -d --wait db
docker compose --env-file ../formal.env run --rm --no-deps backend \
  uv run --no-sync alembic -x initialize_empty_database=true upgrade head
docker compose --env-file ../formal.env up -d --no-build --wait
```

空库入口会在迁移前检查非系统 schema 的表和视图；已有用户对象即拒绝。它不用于现有数据升级。后续版本更新需重新核对迁移影响、固定新的提交与镜像，并完成适用的复验；不要重建覆盖正在使用的版本标签，也不要覆盖现有 `formal.env`。在没有备份的当前范围内，不承诺破坏性数据升级或数据库回退。

## 范围与历史

当前不使用签名发布包、staging/promotion、跨主机切换，也不执行备份、第二副本和恢复演练。原有相关工具仍在仓库内，但不用于当前启停。数据库和视频持久卷保留；这不等于有可恢复的独立备份。

旧 Windows、Mac 签名发布及跨主机迁移手册已移除，独有历史背景由[OpenSpec 历史记录](../openspec/README.md)与 Git 保留。部署目录的固定源码快照保留原貌；当前操作请使用本仓库的本手册，不以旧快照内的历史手册覆盖当前流程。
