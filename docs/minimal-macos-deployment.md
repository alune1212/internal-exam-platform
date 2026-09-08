# 本机最小部署

2026-09-08 选择的部署范围：当前 Mac、`192.168.2.225`、现有 Docker Compose、真实 SMTP；不使用发布包签名，不执行备份、第二副本和恢复演练。

此路径使用独立的新数据库，不迁移现有开发数据。保留数据库和视频的 Docker 持久卷、认证密钥及已有写入保护。签名发布包安装与 staging/promotion 脚本仍属于原有发布路径，不能混用。

## 固定版本和配置

部署目录：`~/Library/Application Support/InternalExamMinimal`。`formal.env` 权限为 `0600`，复用项目 `.env` 的 SMTP 配置，另行生成正式数据库口令、操作员口令和 Token 密钥。操作员账号为 `operator`，密码见该文件的 `PRIMARY_OPERATOR_PASSWORD`。

`release/` 是固定 Git 提交的导出目录；`GIT_COMMIT` 和镜像标签记录该提交。只构建这个目录，日常启动不重新构建。Compose 项目名固定为 `internal-exam-minimal`，不要更改，以免切换数据卷。

```bash
cd "$HOME/Library/Application Support/InternalExamMinimal/release"
docker compose --env-file ../formal.env config --quiet
docker compose --env-file ../formal.env build db backend frontend nginx
docker compose --env-file ../formal.env up -d --wait db
# 仅首次空库执行；已有用户表时拒绝执行。
docker compose --env-file ../formal.env run --rm --no-deps backend \
  uv run --no-sync alembic -x initialize_empty_database=true upgrade head
docker compose --env-file ../formal.env up -d --no-build --wait
```

日常启动使用最后一条命令；暂停使用 `docker compose --env-file ../formal.env stop`。不要执行 `down --volumes`。此路径没有数据恢复能力；保留旧镜像也不代表可以回退已变更的数据库。

## 入口与验收

- 考生：`http://192.168.2.225:8080`。
- 操作员（本机）：`http://127.0.0.1:8081/admin/login`。
- 本机就绪检查：`curl -f http://127.0.0.1:8081/api/ready`。
- 考生入口的管理、运维、文档和 OpenAPI 路径应返回 `404`。

每次开考前确认服务和自动交卷 worker 健康、真实邮箱验证码可达、考试配置与名单正确。首次上线还需真实手机/电脑答题、断线续答、交卷及成绩导出。隔离浏览器测试使用模拟邮箱和移动设备，不能替代真实邮件和手机验收。

Compose 已配置容器自动重启；Mac 必须保持开机、联网且 Docker Desktop 运行。整机重启后登录并启动 Docker Desktop，再检查服务恢复；容器重启验收不能代替整机重启验收。当前验收结果见 `docs/handoff.md` 最新条目。
