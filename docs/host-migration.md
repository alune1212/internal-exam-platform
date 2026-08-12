# Mac ↔ Windows 宿主迁移手册

## 适用范围

当前选定的正式主机/source writer 是 Apple Silicon macOS + Docker Desktop；Mac 真实主机验收仍是独立门禁。未来目标是 Windows Docker Desktop + WSL2 + Docker Compose；Windows 迁移不是当前部署状态，也不能用 Mac 的通过证据提前宣称 Windows ready。

迁移只允许使用一个逻辑数据集、一个正式 writer 和一个经过校验的 release。Mac 与 Windows 不得同时暴露应考人员写入口；开发 checkout、staging、旧宿主和 target host 不得共享正式 volume。

## 不可迁移的内容

不得复制 Docker Desktop VM/raw disk、`Docker.raw`、named-volume 内部目录、容器可写层或未完成归档。它们可能包含架构/运行时内部状态，不能作为跨宿主数据格式。

跨宿主唯一数据格式是 verified paired backup：

- PostgreSQL custom dump；
- `learning_media` 媒体归档；
- manifest、SHA-256、备份类型、source release/commit、migration head 和 writer generation；
- 最后写入的 `SUCCESS`。

第二副本必须放在与当前 Mac 不同物理宿主/磁盘的独立加密存储；证据包只写路径标识、校验和和状态，不写 secret、OTP、token、数据库 URL 或上传内容。

## 迁移前的 Mac source gate

1. 在 designated host account 上确认 Docker Desktop ready、formal release/manifest/checksum 与 migration head 一致，记录 `host_os=macOS`、`architecture=arm64`、release commit 和 writer generation。
2. 停止 development/staging project，并确认它们的 candidate gateway、volume 和 writer 均已退出；考试窗口内不能再启动。
3. 关闭新考试入口，等待或处置所有 `in_progress` attempt；不允许在迁移过程中继续保存或交卷。正式业务数据必须达到 quiescent 状态。
4. 执行最终 post-migration cutover backup（数据库 + media），校验 manifest、SHA-256、`SUCCESS`，再同步到独立加密第二存储；第二副本不可用或未验证时，正式 pre/post/upgrade/cutover gate 必须 fail closed。保留 source stopped 证据。
5. 停止整个 Mac formal Compose project（应考人员/操作员 gateway、frontend、backend、worker、database），并记录停止时间、最后 commit、最后 backup ID、writer generation 和“source stopped”状态。停止后不得重新暴露应考人员入口。
6. 目标 Windows 未完成 restore、migration、服务、网络、SMTP、浏览器和容量证据前，不得向应考人员开放。

“备份已完成”不等于整个 source project 已停止；“source 已停止”也不等于 target 已获准开考。必须证明 source 的全部正式服务均已停止，两个状态和 writer generation 必须在同一份切换证据中出现。

## Windows target 验证和开放

Windows target 必须在真实 Docker Desktop + WSL2、native AMD64 环境中从同一 release inputs 构建或取得相应 AMD64 镜像；不能直接把 Mac ARM64 镜像 archive 当作 Windows acceptance。验证顺序：

1. 使用独立 staging project/volume restore paired backup，运行 migration 到 head，核对表计数、媒体数量、代表性媒体读取、release commit 和 writer generation。
2. 在 staging 完成 split ingress、真实 SMTP、服务/worker 重启恢复、诊断脱敏、浏览器 E2E、100-client 容量和安全门禁。
3. 配置 Windows 固定私网地址、loopback operator 入口、防火墙、电源和 Docker Desktop/WSL2 资源；重新取得桌面/手机 UAT。Mac 的 `192.168.2.34/24` 租约和 pf 证据不自动迁移到 Windows。
4. 仅在 staging evidence、preflight、paired backup 和人工批准均通过后，把应考人员入口切换到 Windows。记录 target writer generation、target release/commit、target host OS/architecture 和 source stopped 证据。
5. 切换后关闭旧 Mac 的 LaunchAgent/Compose recovery，并保持旧 Mac 断开应考人员入口；只允许 Windows writer。

Windows -> Mac 反向迁移完全相同：Windows 必须先无进行中 attempt、停止整个 Windows formal Compose project（candidate/operator gateway、frontend、backend、worker、database）、生成新的 verified paired backup；Mac 用 native ARM64 release inputs 做 staging/恢复，再切换到 Mac。不得把早先的 Mac backup 或停机 Windows state 当作最新回滚点。

## 回滚语义

账号/名单 destructive migration 也遵循同一 restore-only 边界：迁移前必须具备 paired backup、独立加密第二副本、隔离 restore、writer fence 和无进行中 attempt 证据；删除旧全局人员/出席字段后不能用 `alembic downgrade` 伪造字段，只能停止全部 writer，使用上一 release + 已验证 paired backup 恢复，再重跑 migration/count/health、邮箱 OTP/邀请 SMTP、冻结 roster 报表和人工 UAT。备份之后的写入按精确数据损失确认处理。

### 同一宿主、尚未发生迁移或正式写入

若上一 release 已通过 staging，且本次 promotion 尚未执行 migration、没有正式写入，停止当前项目后可启动上一 immutable release。需要记录精确 release/commit 和“无 migration/无 writes”证明。不得直接改代码或使用 `alembic downgrade`。

### 同一宿主、已发生 migration 或正式写入

迁移或写入后，上一版本不能只靠重启容器恢复。必须停止当前 project，使用经过校验的 pre-upgrade paired backup 和上一 release 做明确授权的破坏性 restore，然后重新核对 migration、健康、入口、SMTP、锁和 writer generation。恢复结果要生成新的 rollback evidence。

### 跨宿主、target 尚未写入

若 Windows staging/target 尚未开放应考人员写入，可停止 target，回到已停止的 Mac source，重新验证 source release、最后 paired backup 和 source writer generation，再由人工批准恢复 Mac。不能把“target 容器启动失败”当作双写理由。

### 跨宿主、target 已写入

只要 target 接受过任何正式写请求，旧 source 就不是可直接回切的数据库。必须先在 target 生成新的 verified paired backup（含 target writer generation），停止整个 target formal Compose project，再在 source 以兼容 release restore 该新备份并重新做 host-specific staging/UAT。回切后只允许 source writer；过期 source backup、旧 Mac volume 和 raw Docker disk 均不接受。

## 证据和停止条件

每次迁移/回切保留 source stop、backup/restore `SUCCESS`、manifest/SHA-256、migration head、writer generation、host OS/architecture、split ingress、SMTP、浏览器、100-client、服务恢复和人工批准记录。证据按宿主标注，不能把 Mac evidence 复制成 Windows evidence。

以下任一项缺失即停止迁移或开考：第二副本不可校验；source 仍可写；存在 `in_progress` attempt；target 使用错误架构或未验证 release；两宿主同时暴露应考人员入口；固定 IP/CORS/pf 未重新验证；真实 SMTP、UAT、capacity 或 restore drill 失败；LaunchAgent/Windows recovery 自动批准开考；诊断或证据含 secret/PII。
