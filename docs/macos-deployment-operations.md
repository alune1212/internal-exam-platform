# macOS 正式宿主运维手册

本手册是当前 Mac-first 正式运行的命令入口。宿主为 Apple Silicon macOS + Docker Desktop；正式项目固定为 internal-exam-formal，候选入口使用完成 DHCP reservation 后确定的 `http://${FORMAL_LAN_IP}:8080`，操作员入口只允许 `http://127.0.0.1:8081`。正式根目录本身必须位于开发工作树之外并受保护；其 configuration、releases、backups、evidence、diagnostics 和 state 才是正式 mutable paths。release source、staging 临时路径和独立第二副本可以位于其它受控路径，但不得使用 checkout、Docker raw disk 或 named volume 内部目录作为迁移/备份输入。所有命令都不应把真实 secret 写进 shell 历史、日志或证据。

当前现场尚未确定正式地址：实测 `192.168.2.34` 已被其他设备占用；不得把它写入正式配置，也不得擅自把当前 `192.168.2.46` 或任何其它地址当作正式地址。网络管理员必须先为未占用地址建立 DHCP reservation，随后把同一个 `<FORMAL_LAN_IP>` 统一写入 `formal.env`、CORS、pf 规则和 host/network evidence；在此之前网络验收和正式开考均保持阻断。

命令示例统一使用以下占位变量；只有网络管理员确认 reservation 后才替换其值：

```zsh
export FORMAL_LAN_IP="<FORMAL_LAN_IP>"
```

当前 ops/macos/ 的命令名以实际文件为准；不要在 Mac 上调用 ops/windows/*.ps1。若后续新增 Mac 命令，文档和 UAT 必须先回读实际文件名与 --help。

## 1. 初始化正式根目录

designated host account 可以复用现有受管 Mac 账号，不强制新建账号；但只有登记账号可以运行 Docker Desktop、LaunchAgent 和本手册命令。默认根目录为 ${HOME}/Library/Application Support/InternalExam，目录 0700、环境文件和 state 0600，且必须在工作树之外。

~~~zsh
zsh ops/macos/Initialize-InternalExamHost.zsh \
  --root "$HOME/Library/Application Support/InternalExam"

FORMAL_ROOT="$HOME/Library/Application Support/InternalExam"
find "$FORMAL_ROOT" -maxdepth 2 -type d -exec stat -f '%Sp %Su %N' {} \;
~~~

将正式配置填入 $FORMAL_ROOT/configuration/formal.env 时，不要把真实值复制进 Git。至少核对 ENVIRONMENT=internal、`INTERNAL_LAN_BIND_IP=<FORMAL_LAN_IP>`、`CORS_ORIGINS=http://<FORMAL_LAN_IP>:8080`、SMTP、主/备操作员、签名密钥、正式数据库凭据、绝对生命周期/备份/证据路径和独立加密第二存储路径。正式 Mac 必须满足 `<FORMAL_LAN_IP>/24` DHCP reservation、pf 允许已批准 CIDR 到 `<FORMAL_LAN_IP>:8080`、operator 8081 loopback、Docker AutoStart、Resource Saver 明确关闭、8 CPU/8 GiB 和 MacBook AC。

## 2. 创建、构建、扫描、封存、验证和安装 release

发布包必须来自固定、干净的 Git commit，不包含 .env、数据库、媒体、备份或诊断。正式 release 的唯一顺序是：

```text
New-ReleaseBundle（未构建、未封存）
→ Build-ReleaseImages（本机 ARM64 最终镜像）
→ Invoke-ReleaseSecurityScan（绑定最终镜像 identity）
→ Seal-Release（导入扫描报告并封存）
→ Test-ReleaseBundle（封存包完整性验证）
→ Install-Release（安装到正式根目录）
```

`New-ReleaseBundle.zsh` 的 `--security-evidence` 参数如果使用，只能传入已有 checksum 且 `status` 不是 `passed` 的预构建证据；它会在 release 中写入 `status=pending` 的占位记录。省略该参数时脚本自动创建同样的 pending 占位记录。这个记录不是安全扫描结果，不能通过普通 `Test-ReleaseBundle`，也不能安装、启动或 promotion；native ARM64 镜像构建后必须重新扫描。将旧的、已通过但未绑定本次最终镜像的报告传给 `New-ReleaseBundle` 会被 fail closed 拒绝。

以下命令中的版本、SHA 和路径只是占位符，不是 secret。`New-ReleaseBundle` 会自行拒绝 tracked modification、untracked/ignored file 和非当前 HEAD 的 Git SHA；命令返回成功才表示 bundle 创建完成：

~~~zsh
MAC_ROOT="$HOME/Library/Application Support/InternalExam"
RELEASE_VERSION="1.2.3"
RELEASE_COMMIT="<40位Git提交>"
RELEASE_BUNDLE="/private/tmp/internal-exam-${RELEASE_VERSION}"
SECURITY_EVIDENCE_DIR="$MAC_ROOT/evidence/release-${RELEASE_VERSION}"

zsh ops/macos/New-ReleaseBundle.zsh \
  --source-path "$PWD" \
  --destination-path "$RELEASE_BUNDLE" \
  --application-version "$RELEASE_VERSION" \
  --git-commit "$RELEASE_COMMIT"

# 必须在 ARM64 Mac 上执行；脚本会拒绝重建同一个已存在的 image tag。
zsh ops/macos/Build-ReleaseImages.zsh \
  --release-path "$RELEASE_BUNDLE"

# 输出目录必须在 release bundle 之外。扫描器使用本次 Build 写入的
# built-image-identity.json，并生成带 checksum 的 security-scan-*.json
# 与 canonical-images-*.json；最后一行日志会打印 report= 与 image_record=。
zsh ops/macos/Invoke-ReleaseSecurityScan.zsh \
  --release-path "$RELEASE_BUNDLE" \
  --output-dir "$SECURITY_EVIDENCE_DIR" \
  --root "$MAC_ROOT"

# 将上一条命令的 report= 和 image_record= 实际路径分别填入；两份文件
# 必须保留相邻的 .sha256 sidecar，且都位于 release bundle 外。
SCANNER_EVIDENCE="$SECURITY_EVIDENCE_DIR/security-scan-<timestamp>.json"
FINAL_IMAGE_RECORD="$SECURITY_EVIDENCE_DIR/canonical-images-<timestamp>.json"
zsh ops/macos/Seal-Release.zsh \
  --release-path "$RELEASE_BUNDLE" \
  --security-evidence "$SCANNER_EVIDENCE" \
  --image-record "$FINAL_IMAGE_RECORD" \
  --confirmation "SEAL RELEASE ${RELEASE_VERSION}" \
  --root "$MAC_ROOT"

# Seal-Release 已把 identity-bound 扫描结果写入 release-evidence/security-scan.json。
zsh ops/macos/Test-ReleaseBundle.zsh \
  --release-path "$RELEASE_BUNDLE"

zsh ops/macos/Install-Release.zsh \
  --bundle-path "$RELEASE_BUNDLE" \
  --root "$MAC_ROOT"
~~~

`Invoke-ReleaseSecurityScan.zsh` 只在 arm64 Mac 上扫描 Build 产生的四个 `linux/arm64` 镜像，并将镜像引用、immutable ID、平台、host OS/architecture、scanner provenance 和 canonical image record digest 写入报告。`Seal-Release.zsh` 会再次核对这些绑定、freshness（默认 7 天）、blocking findings 为空及 checksum，然后替换 bundle 内的 pending security record；扫描报告或 image record 只要来自另一轮构建、另一 commit、另一架构或另一组镜像，封存就会拒绝。`Build-ReleaseImages.zsh` 使用临时 build-only 配置，永远不会执行正式 promotion；只有 Seal、Test 均成功后才能 Install，Install 后仍需进入 staging。

## 3. Staging 和正式 promotion

Staging 使用与 formal 完全不同的 project、端口和 volume。它固定使用 candidate 18080、operator 18081、PostgreSQL 15432、frontend 15173；不得指向 formal volume：

fresh formal root 必须先执行本节后文的 `Initialize-FormalWriter.zsh --action Prepare --empty-dataset`，取得 pending `hostId`/`datasetId` 后再运行下面的 staging；已有正式 writer 的普通版本升级不重复 Prepare。

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

# 从 Up 的日志/JSON 取出本次 run-<id>，然后由版本化容器探测
# health/migration、服务重启恢复和候选/操作员路由；该命令只生成它实际探测的
# 三类 raw evidence，不会伪造 browser、SMTP 或 capacity 通过。
RUN_IDENTITY="$MAC_ROOT/staging/<commit12>/evidence/run-<run-id>.json"
HEALTH_MIGRATION="$MAC_ROOT/staging/<commit12>/evidence/health-migration-<run-id>.json"
RESTART="$MAC_ROOT/staging/<commit12>/evidence/restart-<run-id>.json"
ROUTE="$MAC_ROOT/staging/<commit12>/evidence/route-<run-id>.json"
zsh ops/macos/Invoke-StagingRuntimeChecks.zsh \
  --release-path "$RELEASE" \
  --run-identity "$RUN_IDENTITY" \
  --health-migration-evidence "$HEALTH_MIGRATION" \
  --restart-evidence "$RESTART" \
  --route-evidence "$ROUTE" \
  --root "$MAC_ROOT"

# 以下四份必须由真实外部/人工流程产生（不能在本机静态脚本中手写
# status=passed）：browser、SMTP、100-client capacity、backup/restore。
STAGING_EVIDENCE_DIR="$MAC_ROOT/staging/<commit12>/evidence"
LIVE_IMAGES="$STAGING_EVIDENCE_DIR/live-images-<run-id>.json"
BROWSER_REPORT="$STAGING_EVIDENCE_DIR/browser-e2e-report-<run-id>.json"
CAPACITY_REPORT="$STAGING_EVIDENCE_DIR/capacity-report-<run-id>.json"
BROWSER="$STAGING_EVIDENCE_DIR/staging-check-browser-<run-id>.json"
SMTP="$STAGING_EVIDENCE_DIR/staging-check-smtp-<run-id>.json"
CAPACITY="$STAGING_EVIDENCE_DIR/staging-check-capacity-<run-id>.json"
BACKUP_RESTORE="$STAGING_EVIDENCE_DIR/staging-check-backup-restore-<run-id>.json"

# 真实桌面 E2E 报告必须覆盖 operator-login、exam-publish、candidate-otp-login、
# exam-start、answer-autosave、offline-draft-recovery、takeover-conflict、submit、
# answer-release、session-invalidation，并绑定本次 run、commit、project 和 live images。
zsh ops/macos/Invoke-StagingExternalChecks.zsh \
  --check browser \
  --release-path "$RELEASE" \
  --run-identity "$RUN_IDENTITY" \
  --live-image-ids "$LIVE_IMAGES" \
  --output-dir "$STAGING_EVIDENCE_DIR" \
  --candidate-url http://127.0.0.1:18080 \
  --operator-url http://127.0.0.1:18081 \
  --browser-report "$BROWSER_REPORT" \
  --browser-output "$BROWSER" \
  --root "$MAC_ROOT"

# SMTP 由版本化 backend 容器真实投递；recipient 只从受控配置/环境读取，不把
# 密码或 SMTP secret 放进命令行。停止 SMTP 后应有 fail-closed 负向证据。
zsh ops/macos/Invoke-StagingExternalChecks.zsh \
  --check smtp \
  --release-path "$RELEASE" \
  --run-identity "$RUN_IDENTITY" \
  --output-dir "$STAGING_EVIDENCE_DIR" \
  --recipient "$PREFLIGHT_SMTP_RECIPIENT" \
  --smtp-output "$SMTP" \
  --root "$MAC_ROOT"

# capacity-report 必须来自 clean exact-commit checkout 的真实 100-client 测量。
# shipped runner 使用隔离的 internal-exam-capacity project；运行结束后把同名 JSON 与
# .sha256 一起复制到本次 staging evidence 目录。后续脚本会重新核对 exact live image
# IDs、0 errors、100 submissions、P95、DB connections 和 worker heartbeat；若重新构建的
# image ID 与当前 staging 不一致，必须阻断，不得手工改报告。
sh ops/e2e/run-capacity-gate.sh
CAPACITY_SOURCE="<repo>/.runtime/e2e/capacity-runs/<run>/evidence/capacity-report-<run>.json"
/bin/cp -p "$CAPACITY_SOURCE" "$CAPACITY_SOURCE.sha256" "$STAGING_EVIDENCE_DIR/"
CAPACITY_REPORT="$STAGING_EVIDENCE_DIR/${CAPACITY_SOURCE:t}"
zsh ops/macos/Invoke-StagingExternalChecks.zsh \
  --check capacity \
  --release-path "$RELEASE" \
  --run-identity "$RUN_IDENTITY" \
  --live-image-ids "$LIVE_IMAGES" \
  --output-dir "$STAGING_EVIDENCE_DIR" \
  --capacity-report "$CAPACITY_REPORT" \
  --capacity-project internal-exam-capacity \
  --capacity-output "$CAPACITY" \
  --root "$MAC_ROOT"

# 先按第二副本流程取得真实 encrypted-storage evidence，再运行隔离 restore smoke；
# 该命令永远不接触 formal project/volume。
SECOND_COPY="/Volumes/<INDEPENDENT_ENCRYPTED_SECOND_COPY>"
zsh ops/macos/Invoke-StagingBackupRestoreCheck.zsh \
  --release-path "$RELEASE" \
  --run-identity "$RUN_IDENTITY" \
  --second-copy-root "$SECOND_COPY" \
  --output "$BACKUP_RESTORE" \
  --root "$MAC_ROOT"

CANONICAL="$STAGING_EVIDENCE_DIR/staging-acceptance-<run-id>.json"
zsh ops/macos/Invoke-Staging.zsh \
  --action Accept \
  --release-path "$RELEASE" \
  --run-identity "$RUN_IDENTITY" \
  --live-image-ids "$LIVE_IMAGES" \
  --health-migration-evidence "$HEALTH_MIGRATION" \
  --browser-evidence "$BROWSER" \
  --smtp-evidence "$SMTP" \
  --capacity-evidence "$CAPACITY" \
  --restart-evidence "$RESTART" \
  --route-evidence "$ROUTE" \
  --backup-restore-evidence "$BACKUP_RESTORE" \
  --canonical-output "$CANONICAL" \
  --root "$MAC_ROOT"

# 仅在 Accept 成功后清理 staging；Down 会删除该 commit-scoped project/volume，
# 并把 schemaVersion=2 canonical + 七份 raw evidence 保留为 durable bundle。
zsh ops/macos/Invoke-Staging.zsh \
  --action Down \
  --release-path "$RELEASE" \
  --root "$MAC_ROOT"

# Down 成功后，从日志中的 staging_evidence_preserved 路径取出 canonical；
# 该 durable bundle 才是后续 Promote 的输入，不能再引用已删除的 staging 目录。
STAGING_CANONICAL="$MAC_ROOT/evidence/staging-<commit12>-<run-id>/staging-acceptance-<run-id>.json"
~~~

Down 只删除该 commit-scoped staging project/volume，不得对 formal 执行 down -v。staging evidence 必须带 SHA-256、commit 和 host/architecture 标识；未通过不得 promotion。

正式 promotion 前必须完成：

- 100-client 容量门禁（100/100、0 errors、P95/连接/worker 条件全部通过）；
- real SMTP、split ingress、浏览器 UAT、服务/worker 重启和磁盘水位；
- pre-upgrade paired backup 与独立第二存储校验；
- source writer 状态、当前 migration head 和人工“允许发布”决定。

下列 `Promote-Release` 仅适用于已有正式 current writer 的版本升级；fresh root 的首次 generation-1 commissioning 不运行 `Promote-Release`，而按本节后面的 `Prepare` → private maintenance → `Activate` 流程执行。

~~~zsh
zsh ops/macos/Promote-Release.zsh \
  --release-path "$RELEASE" \
  --paired-backup-path "$MAC_ROOT/backups/<backup-id>" \
  --staging-evidence "$STAGING_CANONICAL" \
  --confirmation "PROMOTE 1.2.3" \
  --root "$MAC_ROOT"
~~~

promotion 会在 formal project 中使用 --no-build、核对 portable backup、记录 current/previous release state；它不是考试批准。promotion 后仍须重新运行 Mac preflight、第二设备负向入口检查和人工开考确认。

正式 preflight 使用实际的 Mac 脚本；它要求 Docker settings、AC/sleep、time、FileVault、firewall、privileged `pf`/network-time evidence、真实 SMTP 和 browser evidence。首次 generation-1 commissioning 时，`Activate` 会在私有 maintenance 阶段内部生成 target-maintenance preflight；普通正式重启/发布仍按下列命令显式运行：

~~~zsh
# 先由 designated account 完成一次 sudo ticket；不要以 root 运行整段 preflight。
/usr/bin/sudo -v
zsh ops/macos/Capture-PrivilegedHostEvidence.zsh --root "$MAC_ROOT"

zsh ops/macos/Test-FormalPreflight.zsh \
  --backup-path "$MAC_ROOT/backups/<backup-id>" \
  --browser-smoke-evidence "$MAC_ROOT/evidence/<browser-smoke>.json" \
  --pf-evidence "$MAC_ROOT/evidence/pf-privileged-host-evidence.json" \
  --network-time-evidence "$MAC_ROOT/evidence/network-time-privileged-host-evidence.json" \
  --root "$MAC_ROOT"
~~~

`Capture-PrivilegedHostEvidence.zsh` 必须由 designated account 以普通用户运行；它只对固定的只读 `pfctl`/`systemsetup` 探针使用 `sudo -n`。禁止写成 `sudo zsh ops/macos/Test-FormalPreflight.zsh ...`，也不要把任何真实 sudo 密码写入命令、日志或证据。预检命令失败即阻断 promotion/开考，并写入带 checksum 的 formal-preflight evidence；即使 status 通过，approval 仍为 manual-required。

### 初始 formal writer commissioning（generation 1）

当前 `Initialize-FormalWriter.zsh` 已提供两阶段、可 crash-resume 的首次 writer 路径；实际接口仍以 `--help`/源码为准。该路径只适用于 fresh formal root，不能与未来跨宿主 `prepare-cutover`/`accept-cutover` 混用：

~~~zsh
MAC_ROOT="$HOME/Library/Application Support/InternalExam"
RELEASE="$MAC_ROOT/releases/1.2.3"
BROWSER_SOURCE="/private/tmp/internal-exam-browser-source-<exact-commit>"

# Stage A：只预留空 dataset、host identity、writerGeneration=1 和独立 volumes；
# 不启动 public candidate，不进行 ownership change。
zsh ops/macos/Initialize-FormalWriter.zsh \
  --action Prepare \
  --release-path "$RELEASE" \
  --empty-dataset \
  --root "$MAC_ROOT"

# 现在返回本节前面的 staging 流程，依次完成 Up、七份真实 raw、Accept 和 Down，
# 并把 Down 保留的 durable canonical 路径赋给 STAGING_CANONICAL；未完成时不要继续。

# 私有 maintenance endpoints 只用于最终 writer 的 browser smoke，端口固定
# 127.0.0.1:28080/28081；它不是 staging E2E，也不是手机 UAT。
zsh ops/macos/Start-Platform.zsh --maintenance --root "$MAC_ROOT"
BROWSER_SMOKE="$MAC_ROOT/evidence/formal-browser-smoke-<timestamp>.json"
zsh ops/macos/Capture-FormalBrowserSmokeEvidence.zsh \
  --browser-source "$BROWSER_SOURCE" \
  --release-path "$RELEASE" \
  --output-path "$BROWSER_SMOKE" \
  --candidate-url http://127.0.0.1:28080 \
  --operator-url http://127.0.0.1:28081 \
  --root "$MAC_ROOT"

# privileged evidence 只能由 designated account 先 sudo -v、再以普通用户运行。
/usr/bin/sudo -v
zsh ops/macos/Capture-PrivilegedHostEvidence.zsh --root "$MAC_ROOT"
PF_EVIDENCE="$MAC_ROOT/evidence/pf-privileged-host-evidence.json"
NETWORK_TIME_EVIDENCE="$MAC_ROOT/evidence/network-time-privileged-host-evidence.json"

# Stage B：Activate 会校验 schemaVersion=2 staging 七份 raw、private browser smoke，
# 并在内部完成 generation-1 fence、writer-fence 下最终 paired backup + second copy、
# restore drill、target-maintenance preflight、pending barrier、fence release、terminal
# evidence，最后才 public Start。若任一证据缺失/过期/身份不匹配，命令 fail closed。
zsh ops/macos/Initialize-FormalWriter.zsh \
  --action Activate \
  --release-path "$RELEASE" \
  --staging-evidence "$STAGING_CANONICAL" \
  --browser-smoke-evidence "$BROWSER_SMOKE" \
  --pf-evidence "$PF_EVIDENCE" \
  --network-time-evidence "$NETWORK_TIME_EVIDENCE" \
  --confirmation "ACTIVATE FORMAL WRITER 1.2.3" \
  --root "$MAC_ROOT"
~~~

`BROWSER_SOURCE` 必须是与 release commit 完全一致、无 tracked/untracked 修改且已安装本地 Playwright/Chromium 的 Git 工作树；当前 checkout 只有在已提交且完全 clean 时才能使用。脚本不接受自签的目录 manifest 或非 Git 导出目录。该 smoke 只验证私有维护端点，不能代替 staging E2E、手机 UAT 或第二设备网络门禁。

`Prepare` 与 `Activate` 之间可以暂停；`Activate` 在每个边界写入 checksummed phase journal（`intent → maintenance-started → fence-acquired → backup-passed → restore-passed → preflight-passed → state-bound → fence-released → terminal`）。若进程/主机在 fence 内崩溃，保留精确 fence 和 phase journal，由同一命令按 digest、dataset/host/generation 重新校验并 resume；不得删除 journal、补写 sidecar、手工把 `bootstrapPending` 改为 false 或绕过 terminal barrier。只有 terminal evidence 与 public-ready current state 同时落盘后，才允许 public `Start-Platform`；随后仍需主操作员人工确认“允许开考”。真实网络、SMTP、第二设备、独立加密第二副本和桌面/手机 UAT 缺失时，整体验收仍为 **BLOCKED**，不能用本机静态/synthetic evidence 替代。

如果 Docker Desktop settings 文件不含 `UseResourceSaver`/等价字段，先生成带 checksum 的 operator settings evidence，再将其作为 `--docker-settings-evidence` 传给 `Activate`/`Test-FormalPreflight`；不要用未签名截图或手写 JSON 冒充。

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
