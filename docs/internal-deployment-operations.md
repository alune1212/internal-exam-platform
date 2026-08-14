# Internal 正式宿主运行手册

当前正式主机是 Apple Silicon macOS + Docker Desktop + Docker Compose；本页规定 internal 部署的共通边界，Mac 命令和完整操作顺序见 [macos-deployment-operations.md](macos-deployment-operations.md)。Windows Docker Desktop + WSL2 仅是未来迁移目标，不能在 Mac 证据上宣称 Windows ready。

## 运行合同

- designated host account 可以复用现有受管 Mac 账号，不强制新建账号；只有登记账号运行 Docker Desktop、LaunchAgent 和 formal 配置。
- 正式根目录默认是 ${HOME}/Library/Application Support/InternalExam，必须在工作树外；目录 0700、formal.env/state/evidence 0600。不得把 Docker Desktop raw disk、named volume 内部目录或 checkout 当作正式根/迁移输入。
- Docker Desktop 启用登录后启动、关闭 Resource Saver，并固定 8 CPU/8 GiB。MacBook 正式考试全程 AC，电池不是正式电源方案。
- 正式应考人员入口使用网络管理员批准并完成 DHCP reservation 的 `<FORMAL_LAN_IP>/24`。pf/受管防火墙仅允许已批准的局域网 CIDR 到 `<FORMAL_LAN_IP>:8080`；operator 8081 严格仅 127.0.0.1。HTTP 是明确接受的第一阶段安全例外，不是传输安全。历史或 synthetic UAT 地址不得复制为正式配置。
- formal 项目 24×7 best-effort；考试窗口内停止 development/staging，任何时刻只允许一个 writer。LaunchAgent 只做无构建恢复，不能 promotion、restore、delete、rotate session 或批准开考。
- PostgreSQL 和媒体使用 verified paired backup；本机备份之外必须有不同物理宿主/磁盘的独立加密第二存储。备份必须包含 manifest、SHA-256 和 SUCCESS。
- 同宿主 rollback 在 migration/write 前需要“无 migration/无 writes”证明；之后必须授权上一 release + paired backup 破坏性恢复，禁止 alembic downgrade。
- 邮箱/名单 destructive migration 另需只读 conflict preflight、writer fence、协调写冻结、无进行中正式 attempt、paired backup/独立第二副本隔离 restore 和计数/外键校验；迁移删除旧全局人员/出席字段后只能 restore-only 回到上一 release，不能用 downgrade 伪造已删除数据。
- 迁移后的 smoke 必须覆盖 active/pending/inactive 账号、六位十分钟 OTP、注册完成/Profile、四小时 session/no remember-me、邮箱限流、冻结 roster identity、显式 invitation initial-send 与 failed-only resend；邀请链接不得携带 bearer credential。
- Mac→Windows 或 Windows→Mac 迁移只能以 paired backup 为数据格式；source 必须停止并生成 writer generation，target 完成 native 架构 staging/UAT 后才可开放，target 写入后回切必须先从 target 生成新 backup。见 host-migration.md。

## 工作区与浏览器恢复边界

- 管理员单场工作区为 `GET /api/admin/exams/{exam_id}/workspace`，返回带 `observed_at` 的发布就绪、名单/邀请/出席/attempt/incident 聚合和服务端 advisory next action；响应不含 roster identity 或其它名单 PII，next action 仍需在对应 mutation 时重新校验。
- 应考人员的短时凭据和答题草稿只保留在当前标签页的 `sessionStorage`。同一标签页 reload 可恢复并在网络恢复后按 revision 同步；关闭标签页/窗口、换标签页、换设备或迁移到另一宿主不保证恢复，必须重新 OTP 登录或 takeover。
- 受控 Playwright mobile Chromium 只覆盖窄视口 formal action area（保存、题号导航、交卷可达性和无横向溢出），属于 disposable engineering gate；它不替代真实 macOS Safari/手机 UAT，也不构成 Mac 正式 commissioning 或 Windows Docker Desktop + WSL2 acceptance。正式 Mac/Windows 证据仍按各自 host gate 单独取得。

## 当前 Mac 操作入口

| 目的 | 实际脚本 |
| --- | --- |
| 初始化根目录 | ops/macos/Initialize-InternalExamHost.zsh |
| 创建发布包 | ops/macos/New-ReleaseBundle.zsh |
| 校验发布包 | ops/macos/Test-ReleaseBundle.zsh |
| 安装发布包 | ops/macos/Install-Release.zsh |
| 构建 ARM64 镜像 | ops/macos/Build-ReleaseImages.zsh |
| staging Up/Down/Status | ops/macos/Invoke-Staging.zsh |
| 正式启动/状态/停止 | ops/macos/Start-Platform.zsh、Get-PlatformStatus.zsh、Stop-Platform.zsh |
| 正式预检 | ops/macos/Test-FormalPreflight.zsh |
| 配对备份/第二副本 | ops/macos/Invoke-PairedBackup.zsh |
| 隔离恢复演练 | ops/macos/Invoke-RestoreDrill.zsh |
| 正式 promotion | ops/macos/Promote-Release.zsh |
| Mac source stop/Mac target acceptance | ops/macos/Prepare-HostCutover.zsh、Accept-HostCutover.zsh |
| 备份操作员切换 | ops/macos/Set-BackupOperator.zsh |
| 关闭 session | ops/macos/Close-ExamSessions.zsh |
| 脱敏诊断 | ops/macos/Export-Diagnostics.zsh |
| 回滚 | ops/macos/Rollback-Release.zsh |
| LaunchAgent 安装/卸载 | ops/macos/Install-LaunchAgents.zsh、Uninstall-LaunchAgents.zsh |

所有 Mac 命令必须先通过 --help、zsh -n、临时 root/项目边界检查和 UAT；不要在 Mac 上调用同名 Windows .ps1，也不要把手工 token、直接数据库写入或未脱敏日志当作替代。

## 考试前、考试中和考后

1. 按 macos-host-guide.md 配置 AutoStart、关闭 Resource Saver、8 CPU/8 GiB、AC、DHCP reservation、pf、FileVault、formal root 和时间。
2. 按 macos-deployment-operations.md 创建/校验 release，完成独立 staging、账号迁移 preflight（如适用）、真实 OTP/邀请 SMTP、路由负向测试、100-client gate、pre-exam/pre-upgrade backup、second-copy 和 restore drill。
3. promotion 或 Docker/host 重启后，主操作员再次执行 status/preflight、SMTP、浏览器和第二设备检查，人工确认开考；LaunchAgent loaded 或容器 healthy 不等于批准。
4. 开考后只读运维，不改题、名单、导入、升级、归档删除或恢复；development/staging 保持停止。
5. 考后完成 terminal/解析决定、post-exam backup、独立加密第二副本、diagnostic/incident evidence 和 close-session；没有对应 Mac 命令落地前不得宣称该项完成。账号迁移失败或 destructive boundary 后只能按配对备份 restore 语义回滚。

详细 checkbox、Stop Conditions 和证据字段见 official-exam-uat-checklist.md。HTTP 例外和复审触发器见 security-http-exception.md。

## Windows 未来迁移门禁

Windows target 必须在真实 Docker Desktop + WSL2、native AMD64 上从同一 release inputs 构建/验证镜像，使用 paired backup restore 到独立 staging，重新核对 migration、网络/pf、防火墙、SMTP、浏览器、服务恢复、100-client 和 second-copy restore。Mac 的 host_os=macOS、architecture=arm64、`<FORMAL_LAN_IP>` 租约和 pf 证据不得复制为 Windows evidence。

只有 source stopped、无 in_progress attempt、final backup/SUCCESS/sha256、writer generation、target staging/UAT 和人工 promotion 全部存在时，才允许 Windows 成为唯一应考人员 writer。任何 target 正式写入后，旧 Mac 不能直接重启；回切必须先从 Windows 新建 verified paired backup，再做 Mac restore/staging/UAT。
