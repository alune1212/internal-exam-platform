# Internal Deployment Operations

本文档用于受控局域网正式考试的配对备份与隔离恢复验证。工具不会、也不得默认覆盖当前正式数据。

## 安全边界

- 一次备份必须同时包含 PostgreSQL custom-format dump 和 `learning_media` archive；两者不能拆开使用。
- 备份必须在维护窗口执行：停止新登录、考试开始、作答提交、管理员变更和视频上传。工具会拒绝数据库中仍有 `in_progress` attempt 的情况，但无法自动识别浏览器中尚未提交的视频上传。
- 只有同时存在 `database.dump`、`learning_media.tar.gz`、`manifest.json`、`SHA256SUMS` 和最后写入的 `SUCCESS` 时，备份才有效。
- 恢复验证只接受名称以 `internal-exam-restore-verify-` 开头的一次性 Compose project，并使用独立 PostgreSQL volume 和临时媒体 volume。
- 仓库不提供覆盖当前正式数据库或正式媒体 volume 的默认恢复命令。真实灾难恢复必须由操作员另行审批目标、停机范围和回滚点。

## 创建配对备份

先确认服务健康、磁盘空间充足，且已进入维护窗口：

```bash
docker compose --env-file .env ps
curl -f http://<INTERNAL_LAN_BIND_IP>:8080/api/ready
```

从仓库根目录执行：

```bash
cd backend
uv run python -m app.ops.internal_backup backup \
  --output-root ../backups \
  --env-file ../.env
cd ..
```

成功目录形如 `backups/backup-20260710T000000Z/`。工具按以下顺序工作：

1. 拒绝存在进行中考试的数据库。
2. 记录 Alembic head、代表性表计数和媒体文件数。
3. 创建 `database.dump` 与 `learning_media.tar.gz`。
4. 写入 manifest 和三个产物的 SHA-256 checksum。
5. 最后写入 `SUCCESS`，并在命令成功返回前执行完整读取校验。

命令返回非零、目录缺少 `SUCCESS` 或 checksum 不匹配时，该目录是无效的部分产物，不得用于恢复。

## 隔离恢复验证

当前 Compose stack 的 PostgreSQL 占用 loopback `5432`。完成备份后，继续留在维护窗口并先停止正式 stack，释放端口；数据 volume 不会因 `stop` 被删除：

```bash
docker compose --env-file .env stop
```

选择唯一的一次性 project 名并运行校验：

```bash
cd backend
uv run python -m app.ops.internal_backup verify \
  ../backups/backup-20260710T000000Z \
  --env-file ../.env \
  --project-name internal-exam-restore-verify-20260710a
cd ..
```

验证会在一次性资源中执行以下检查：

- checksum 与 `SUCCESS` 完整；
- PostgreSQL custom-format dump 可恢复；
- 恢复后的 Alembic head 与 manifest 一致；
- `candidate`、`question`、`exam`、`exam_attempt`、`learning_video` 计数一致；
- media archive 可解压、文件数一致，并且有媒体时至少一个样本非空且可读。

无论成功或失败，工具都会尝试删除临时媒体 volume，并执行一次性 Compose project 的 `down -v --remove-orphans`。成功后重新启动正式 stack 并复核健康：

```bash
docker compose --env-file .env up -d
docker compose --env-file .env ps
curl -f http://<INTERNAL_LAN_BIND_IP>:8080/api/ready
```

## 失败处理

- 备份失败：保留日志中的非敏感错误说明；删除部分目录前先确认其中没有 `SUCCESS`。重新进入干净维护窗口后创建新时间戳备份，不要补写或复用旧目录。
- 恢复校验失败：不要把该备份标记为发布证据；排查 checksum、迁移版本、表计数或媒体样本差异后重新创建整套备份。
- 清理失败：工具会返回非零并提示人工检查。使用实际的一次性 project 名执行：

```bash
docker volume rm internal-exam-restore-verify-20260710a_learning_media
docker compose --env-file .env \
  --project-name internal-exam-restore-verify-20260710a \
  down -v --remove-orphans
```

- 正式 stack 未自动恢复：从仓库根目录执行 `docker compose --env-file .env up -d`，等待 backend 和 worker 均为 healthy 后再结束维护窗口。

备份目录应复制到受控的第二存储位置并按内部数据保留制度保护；不要提交到 Git，也不要通过非受控聊天或网盘传输。
