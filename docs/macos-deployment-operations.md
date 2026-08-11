# macOS 正式宿主运维手册

本手册是当前 Mac-first 正式运行的命令入口。宿主为 Apple Silicon macOS + Docker Desktop；正式项目固定为 internal-exam-formal，候选入口固定为 http://192.168.2.34:8080，操作员入口只允许 http://127.0.0.1:8081。正式根目录本身必须位于开发工作树之外并受保护；其 configuration、releases、backups、evidence、diagnostics 和 state 才是正式 mutable paths。release source、staging 临时路径和独立第二副本可以位于其它受控路径，但不得使用 checkout、Docker raw disk 或 named volume 内部目录作为迁移/备份输入。所有命令都不应把真实 secret 写进 shell 历史、日志或证据。

当前 ops/macos/ 的命令名以实际文件为准；不要在 Mac 上调用 ops/windows/*.ps1。若后续新增 Mac 命令，文档和 UAT 必须先回读实际文件名与 --help。

## 1. 初始化正式根目录

designated host account 可以复用现有受管 Mac 账号，不强制新建账号；但只有登记账号可以运行 Docker Desktop、LaunchAgent 和本手册命令。默认根目录为 ${HOME}/Library/Application Support/InternalExam，目录 0700、环境文件和 state 0600，且必须在工作树之外。

~~~zsh
zsh ops/macos/Initialize-InternalExamHost.zsh \
  --root "$HOME/Library/Application Support/InternalExam"

FORMAL_ROOT="$HOME/Library/Application Support/InternalExam"
find "$FORMAL_ROOT" -maxdepth 2 -type d -exec stat -f '%Sp %Su %N' {} \;
~~~

将正式配置填入 $FORMAL_ROOT/configuration/formal.env 时，不要把真实值复制进 Git。至少核对 ENVIRONMENT=internal、INTERNAL_LAN_BIND_IP=192.168.2.34、精确 CORS、SMTP、主/备操作员、签名密钥、正式数据库凭据、绝对生命周期/备份/证据路径和独立加密第二存储路径。正式 Mac 必须满足 192.168.2.34/24 DHCP reservation、pf 允许 192.168.2.0/24 到 8080、operator 8081 loopback、Docker AutoStart、Resource Saver 明确关闭、8 CPU/8 GiB 和 MacBook AC。

## 2. 创建、验证、安装和构建 release

发布包必须来自固定 Git commit，附八天内通过的安全证据；不包含 .env、数据库、媒体、备份或诊断。以下命令中的版本、SHA 和路径只是占位符，不是 secret：

~~~zsh
zsh ops/macos/New-ReleaseBundle.zsh \
  --source-path "$PWD" \
  --destination-path "/private/tmp/internal-exam-1.2.3" \
  --application-version 1.2.3 \
  --git-commit <40位Git提交> \
  --security-evidence "/private/tmp/security-scan-<timestamp>.json"

zsh ops/macos/Test-ReleaseBundle.zsh \
  --release-path "/private/tmp/internal-exam-1.2.3"

zsh ops/macos/Install-Release.zsh \
  --bundle-path "/private/tmp/internal-exam-1.2.3" \
  --root "$HOME/Library/Application Support/InternalExam"

zsh ops/macos/Build-ReleaseImages.zsh \
  --release-path "$HOME/Library/Application Support/InternalExam/releases/1.2.3"
~~~

Build-ReleaseImages.zsh 只在 arm64 Mac 上构建 linux/arm64 镜像，并使用临时 build-only 配置；它不是正式 promotion。每次安装后都重新运行 Test-ReleaseBundle.zsh，再进入 staging。

## 3. Staging 和正式 promotion

Staging 使用与 formal 完全不同的 project、端口和 volume。它固定使用 candidate 18080、operator 18081、PostgreSQL 15432、frontend 15173；不得指向 formal volume：

~~~zsh
MAC_ROOT="$HOME/Library/Application Support/InternalExam"
RELEASE="$MAC_ROOT/releases/1.2.3"

zsh ops/macos/Invoke-Staging.zsh \
  --action Up \
  --release-path "$RELEASE" \
  --root "$MAC_ROOT"

zsh ops/macos/Invoke-Staging.zsh \
  --action Status \
  --release-path "$RELEASE" \
  --root "$MAC_ROOT"

# 完成浏览器、SMTP、服务重启、离线资源、路由和容量证据后：
zsh ops/macos/Invoke-Staging.zsh \
  --action Down \
  --release-path "$RELEASE" \
  --root "$MAC_ROOT"
~~~

Down 只删除该 commit-scoped staging project/volume，不得对 formal 执行 down -v。staging evidence 必须带 SHA-256、commit 和 host/architecture 标识；未通过不得 promotion。

正式 promotion 前必须完成：

- 100-client 容量门禁（100/100、0 errors、P95/连接/worker 条件全部通过）；
- real SMTP、split ingress、浏览器 UAT、服务/worker 重启和磁盘水位；
- pre-upgrade paired backup 与独立第二存储校验；
- source writer 状态、当前 migration head 和人工“允许发布”决定。

~~~zsh
zsh ops/macos/Promote-Release.zsh \
  --release-path "$RELEASE" \
  --paired-backup-path "$MAC_ROOT/backups/<backup-id>" \
  --staging-evidence "$MAC_ROOT/evidence/<staging-evidence>.json" \
  --confirmation "PROMOTE 1.2.3" \
  --root "$MAC_ROOT"
~~~

promotion 会在 formal project 中使用 --no-build、核对 portable backup、记录 current/previous release state；它不是考试批准。promotion 后仍须重新运行 Mac preflight、第二设备负向入口检查和人工开考确认。

正式 preflight 使用实际的 Mac 脚本；它要求 host-evidence.env 中已记录 AutoStart、Resource Saver、AC、sleep、time、FileVault、firewall 和 pf 状态，并要求真实 SMTP 和 browser evidence：

~~~zsh
zsh ops/macos/Test-FormalPreflight.zsh \
  --backup-path "$MAC_ROOT/backups/<backup-id>" \
  --browser-smoke-evidence "$MAC_ROOT/evidence/<browser-smoke>.json" \
  --root "$MAC_ROOT"
~~~

该命令失败即阻断 promotion/开考，并写入带 checksum 的 formal-preflight evidence；即使 status 通过，approval 仍为 manual-required。

## 4. 启动、状态和停止

~~~zsh
zsh ops/macos/Start-Platform.zsh --root "$HOME/Library/Application Support/InternalExam"
zsh ops/macos/Get-PlatformStatus.zsh --root "$HOME/Library/Application Support/InternalExam"
zsh ops/macos/Stop-Platform.zsh --root "$HOME/Library/Application Support/InternalExam"
~~~

Start-Platform.zsh 只恢复 current immutable release，使用 up -d --no-build，不切换版本、不迁移数据库、不批准考试。Stop-Platform.zsh 使用 stop，不删除 formal volume。考试时必须停止 development/staging 项目；任何时刻只允许一个 formal writer。

## 5. 配对备份、第二副本和 restore drill

每日可在无进行中考试时运行机会式备份；无变化时保留 skipped，不得手工改成成功：

~~~zsh
zsh ops/macos/Invoke-PairedBackup.zsh \
  --kind daily \
  --opportunistic \
  --root "$HOME/Library/Application Support/InternalExam"
~~~

考试前、升级前和考后分别运行强制备份。考后备份必须同步到与 Mac 不同物理宿主/磁盘的独立加密第二存储；不要使用 Docker.raw 或 named-volume 内部目录：

~~~zsh
MAC_ROOT="$HOME/Library/Application Support/InternalExam"
SECOND_COPY="/Volumes/InternalExamSecondCopy"

# 仅在磁盘工具已经把该独立物理卷加密、挂载并确认可写后创建标记；
# 标记本身不替代 diskutil 的加密与物理磁盘检查。
install -m 600 /dev/null "$SECOND_COPY/.internal-exam-encrypted-storage"
zsh ops/macos/Capture-SecondCopyStorageEvidence.zsh \
  --root "$MAC_ROOT"

zsh ops/macos/Invoke-PairedBackup.zsh \
  --kind pre-exam \
  --root "$MAC_ROOT"

zsh ops/macos/Invoke-PairedBackup.zsh \
  --kind pre-upgrade \
  --root "$MAC_ROOT"

zsh ops/macos/Invoke-PairedBackup.zsh \
  --kind post-exam \
  --second-copy-path "$SECOND_COPY" \
  --root "$MAC_ROOT"
~~~

`Capture-SecondCopyStorageEvidence.zsh` 从 `formal.env` 的 `SECOND_COPY_PATH` 读取位置，要求它是已挂载、加密、可写且与正式根目录处于不同 `ParentWholeDisk` 的物理卷，并生成带 checksum 的 `second-copy-storage.json`。备份必须包含 PostgreSQL custom dump、learning_media archive、manifest、SHA-256、SUCCESS 和 writer/release 信息。第二副本不可校验时不得开考、升级或记录同步成功。

配对备份取得的 `backup-write-freeze` 必须由同一操作员 owner 显式释放；`expires_at` 只用于诊断，不会自动恢复写入或允许另一份备份覆盖它。若宿主或备份进程异常退出，应先确认没有 `pg_dump`、媒体归档或第二份备份仍在运行，再使用版本化后端的 `operational_lock release-backup --owner <原 owner>` 恢复；不得仅因 TTL 已过就开放考试或手工改数据库锁。

每季度、重大更新前和迁移前从第二副本做一次隔离 restore drill：

~~~zsh
zsh ops/macos/Invoke-RestoreDrill.zsh \
  --second-copy-backup-path "$SECOND_COPY/<backup-id>" \
  --root "$MAC_ROOT"
~~~

该命令创建一次性 internal-exam-restore-verify-* project/volume，验证 migration、表计数、媒体数量和代表性读取后清理；不得修改 formal project。

## 6. 备份操作员和会话关闭

备份操作员默认禁用；只有主操作员不可用时按精确确认启用，接管后不允许两人并行操作：

~~~zsh
zsh ops/macos/Set-BackupOperator.zsh \
  --state Enabled \
  --confirmation "ENABLE BACKUP OPERATOR" \
  --root "$HOME/Library/Application Support/InternalExam"

zsh ops/macos/Set-BackupOperator.zsh \
  --state Disabled \
  --confirmation "DISABLE BACKUP OPERATOR" \
  --root "$HOME/Library/Application Support/InternalExam"
~~~

考后关闭全部 session：

~~~zsh
zsh ops/macos/Close-ExamSessions.zsh \
  --confirmation "CLOSE ALL SESSIONS" \
  --root "$HOME/Library/Application Support/InternalExam"
~~~

诊断包最多采集每服务 500 行日志，脱敏并带 checksum；可以从受保护的 token 文件读取，不要把 token 写入命令行：

~~~zsh
zsh ops/macos/Export-Diagnostics.zsh \
  --admin-token-file "/private/secure/<admin-token-file>" \
  --root "$HOME/Library/Application Support/InternalExam"
~~~

## 7. 同宿主回滚与跨宿主迁移

同宿主回滚命令有两个明确模式：

~~~zsh
# 尚未 migration、没有正式写入，且有证明：
zsh ops/macos/Rollback-Release.zsh \
  --mode PreMigration \
  --proven-no-migration-or-writes \
  --confirmation "ROLLBACK PRE-MIGRATION <上一版本>" \
  --root "$HOME/Library/Application Support/InternalExam"

# 已 migration 或写入，必须显式授权破坏性恢复：
zsh ops/macos/Rollback-Release.zsh \
  --mode PostMigrationOrWrite \
  --allow-destructive-restore \
  --confirmation "RESTORE PAIRED BACKUP <上一版本>" \
  --root "$HOME/Library/Application Support/InternalExam"
~~~

禁止 alembic downgrade。迁移或正式写入后只能使用上一 release + 已验证 paired backup 恢复，并重新执行 health、migration、入口、SMTP 和人工 preflight。

Mac→Windows 迁移必须先：

1. 停止 development/staging 和 Mac formal candidate gateway；
2. 等待/处置所有 in_progress attempt；
3. 生成最终 paired backup + SUCCESS + SHA-256，并同步独立加密第二存储；
4. 记录 source stopped、release commit、backup ID 和 writer generation；
5. 在真实 Windows Docker Desktop + WSL2 native AMD64 上从同一 release inputs 构建、restore、staging、UAT、100-client 和防火墙证据；
6. 只有 source stopped 且 target evidence/人工批准齐全才开放 Windows candidate writer。

Windows target 一旦写入，回切 Mac 必须先在 Windows 生成新的 verified paired backup，再停止 Windows writer、在 Mac staging/restore 后切换；不能重启旧 Mac 形成双写。Mac 证据永远不满足 Windows acceptance。完整状态机见 host-migration.md。

正式 Mac source 准备切换时，使用实际的 Mac source-stop/writer-generation 命令。`Prepare-HostCutover.zsh` 只在 Mac source 上运行：

~~~zsh
zsh ops/macos/Prepare-HostCutover.zsh \
  --target-host windows-docker-wsl2 \
  --confirmation "PREPARE HOST CUTOVER" \
  --root "$MAC_ROOT"
~~~

该命令在持久 writer fence 内自行创建并验证最终 `cutover` 配对备份及其独立加密第二副本；不得把操作员预先选择的普通备份冒充最终迁移快照。

Windows target 不运行下面的 Mac zsh；它必须使用未来 Windows Docker Desktop + WSL2 适配器完成独立 restore、native 架构 staging、SMTP、UAT 和 100-client gate。下面的 `Accept-HostCutover.zsh` 只在 Mac target（例如 Windows→Mac 回切）上运行，用于接受已停止 source 的备份和 target evidence：

~~~zsh
zsh ops/macos/Accept-HostCutover.zsh \
  --final-backup-path "$MAC_ROOT/backups/<final-backup-id>" \
  --browser-smoke-evidence "$MAC_ROOT/evidence/<target-browser-smoke>.json" \
  --prepared-evidence "$MAC_ROOT/evidence/<cutover-prepared>.json" \
  --source-stopped \
  --confirmation "ACCEPT HOST CUTOVER" \
  --root "$MAC_ROOT"
~~~

这些命令会验证 source stopped 和备份/证据，但不自动批准考试；目标开放前仍要由目标宿主主操作员人工确认。

## 8. LaunchAgent 和人工批准

当前正式主机必须安装项目提供的 LaunchAgent，并让它经过 plist 校验、加载和日志路径检查。LaunchAgent 仅可等待 Docker ready、恢复已选 release（up -d --no-build）或执行 skip-aware opportunity backup；不能 build/promote/restore/delete/rotate sessions/approve exam。

当前模板文件为 com.internal-exam.formal-bootstrap.plist.template 和 com.internal-exam.opportunity-backup.plist.template；使用实际的 Install-LaunchAgents.zsh 安装并验证 loaded：

~~~zsh
MAC_ROOT="$HOME/Library/Application Support/InternalExam"
zsh ops/macos/Install-LaunchAgents.zsh --root "$MAC_ROOT"
~~~

安装脚本会渲染模板、运行 plutil、bootstrap/print 两个 LaunchAgent，并将命令路径固定为同一 release 的 ops/macos/LaunchAgent-Dispatcher.zsh；不能指向 development checkout。卸载必须有精确确认：

~~~zsh
zsh ops/macos/Uninstall-LaunchAgents.zsh \
  --confirmation "UNINSTALL INTERNAL EXAM LAUNCHAGENTS"
~~~

LaunchAgent loaded、容器 healthy 或自动恢复成功都不等于开考授权。

重启或 Docker 恢复后，主操作员仍须完成 official-exam-uat-checklist.md 的 Mac host、network、SMTP、backup、browser 和 capacity 检查，并明确人工确认开考。LaunchAgent loaded、容器 healthy、status 绿都不等于开考授权。
