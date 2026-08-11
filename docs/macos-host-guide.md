# macOS 正式宿主准备指南

## 当前宿主边界

当前第一阶段正式宿主是 Apple Silicon macOS + Docker Desktop + Docker Compose。应用运行时、PostgreSQL、迁移、备份校验和 SMTP 检查都在版本化容器内执行；宿主只需要 Docker Desktop、Docker Compose 和 `/bin/zsh` 适配器，不要求安装 Python、Node.js、uv 或 PostgreSQL 客户端。

正式运行是单宿主、24×7 best-effort，不是高可用或无人值守服务。Docker、磁盘、Mac 或办公网络发生严重故障时，允许暂停或改期考试。未来如迁移到 Windows Docker Desktop + WSL2，必须走 [`host-migration.md`](host-migration.md) 的单写入者流程；Windows 不是当前正式主机。

这份指南定义宿主配置合同，不把开发 Compose、静态脚本检查或一次本地容量运行描述为正式验收。正式开考仍须完成 [`official-exam-uat-checklist.md`](official-exam-uat-checklist.md) 的当前 Mac 检查并保留非敏感、带 SHA-256 的证据。

## designated host account 与正式根目录

- Docker Desktop 必须由一个受公司管理的 designated host account 运行。可以复用当前已受管的 Mac 账号，不强制新建操作系统账号；但该账号必须明确登记为宿主责任人，负责 Docker、LaunchAgent、正式配置和证据。不要把“建议专用账号”写成强制迁移条件。
- 平台操作应与日常办公、邮件、网页浏览和无关软件安装保持隔离；即使当前已登录账号另有日常用途，也不因本指南强制新建操作系统账号。复用现有账号时按公司策略使用专门的登录会话和最小权限。账号密码、FileVault 恢复材料和外接存储密钥按公司密码/密钥流程保管，不写进 Git 或证据。
- 正式根目录必须在工作树之外，默认是 ${HOME}/Library/Application Support/InternalExam，下设 `configuration`、`releases`、`backups`、`evidence`、`diagnostics` 和 `state`。不要使用当前 checkout、Docker Desktop VM/raw disk 或 named volume 内部路径作为迁移/备份根。
- 正式根目录、子目录和 mutable state 只允许 designated host account 读取；目录使用 `0700`，`formal.env`、release state 和证据索引使用 `0600`。正式环境文件只能放在 `configuration`，发布包不得包含密钥、数据库、媒体、备份或诊断数据。
- `formal.env` 的 `SECOND_COPY_PATH` 必须指向已挂载的独立加密物理卷。创建 `.internal-exam-encrypted-storage` owner-only 标记后，运行 `zsh ops/macos/Capture-SecondCopyStorageEvidence.zsh --root "$FORMAL_ROOT"`；命令会用 `diskutil` 同时核对加密、可写和不同 `ParentWholeDisk`，标记文件本身不构成加密证明。

初始化由项目适配器完成（不会写入真实 secret）：

```zsh
zsh ops/macos/Initialize-InternalExamHost.zsh \
  --root "$HOME/Library/Application Support/InternalExam"

FORMAL_ROOT="$HOME/Library/Application Support/InternalExam"
find "$FORMAL_ROOT" -maxdepth 2 -type d -exec stat -f '%Sp %Su %N' {} \;
stat -f '%Sp %Su %N' "$FORMAL_ROOT/configuration/formal.env"
```

`formal.env` 尚不存在时最后一条命令失败是预期的；初始化后必须确认它是 owner-only（`0600`）。任何命令输出都不要上传到聊天或工单，路径可能含有账号名。

## Docker Desktop 自启和资源

在 designated host account 的 Docker Desktop 设置中记录截图或导出证据：

1. 打开“登录后启动 Docker Desktop”（AutoStart）。macOS 重启后必须先登录该账号，等待 Docker ready，再做人工预检。
2. 关闭 Resource Saver。Docker Desktop 当前没有供本项目验证的、可靠的按 Compose project 排除机制；正式主机不能依赖空闲暂停后的机会式恢复来维持 24x7 best-effort 服务。
3. Docker Desktop 资源固定为 **8 CPU、8 GiB memory**，并保留足够磁盘余量；更改资源后必须重新做 staging 和 100-client 容量门禁。
4. 保留 Compose 的 `restart: unless-stopped` 和有界日志轮转；不要启用 Kubernetes、无关扩展、公网容器端口，也不要把 Docker Desktop raw disk 当作备份。

只读核对命令如下；通过这些命令不等于正式预检通过：

```zsh
docker version
docker compose version
docker context show
docker info --format '{{.OSType}}/{{.Architecture}}'
docker system df
```

正式项目的自动恢复只允许恢复已选中的 immutable release。LaunchAgent 可以在 Docker ready 后执行无构建的 Compose recovery，但不能 build、promote、restore、删除数据、轮换 session 或批准开考；恢复成功永远不等于“允许开考”。LaunchAgent 必须安装并经过 `launchctl`/plist 验证，未安装或加载失败即为预检阻断项。

## 固定地址、入口和 HTTP 例外

- 正式 Mac 使用 `192.168.2.34/24`。网络团队必须先为该 MAC 地址建立 DHCP reservation；没有 reservation、地址冲突或实际租约不是 `192.168.2.34/24` 时，不得开考。不要临时热点、link-local、公网地址或任意 `0.0.0.0`。
- `INTERNAL_LAN_BIND_IP=192.168.2.34`，`CORS_ORIGINS` 必须精确为 `http://192.168.2.34:8080`，不追加 localhost、其他端口或通配符。
- 考生入口为 `http://192.168.2.34:8080`；操作员入口严格为 Mac 本机 `http://127.0.0.1:8081`。PostgreSQL `5432`、前端直连 `5173`、admin/operations/readiness detail、docs 和 OpenAPI 不得向局域网开放。
- pf/受管防火墙只允许 `192.168.2.0/24` 到 `192.168.2.34:8080` 的候选流量；`8081` 只允许 `127.0.0.1`。禁止公网端口转发、访客网、未授权 VPN 和其他网段。
- 这是 [`security-http-exception.md`](security-http-exception.md) 记录的共享办公局域网 HTTP 例外，没有传输加密，不能称为“安全 HTTP”“内网 HTTPS”或等同 HTTPS。

至少用一台已批准的第二办公设备实测：`192.168.2.34:8080` 可达，`8081/5432/5173` 及 `/admin`、`/api/admin/`、`/operations`、`/docs`、`/openapi.json` 不可达；Mac 本机能访问 `127.0.0.1:8081`。固定租约或 CORS 变化时，先停止 formal candidate gateway，更新配置、重建证据并完成预检；不能在旧地址和新地址上双写。

可用以下命令记录接口和租约（只读；不要把输出当作 DHCP reservation 证明）：

```zsh
networksetup -listallhardwareports
networksetup -getinfo "Wi-Fi"
networksetup -getinfo "Ethernet"
ipconfig getifaddr en0
route -n get default
```

## FileVault、pf、电源和时间

- 系统盘及保存正式配置/备份的磁盘必须启用 FileVault 或公司认可的等效全盘加密；恢复密钥和外接盘密钥进入受控密钥库。
- macOS Application Firewall 与受管 pf 规则必须可核验，并满足上面的单一候选入口规则。不得为排障执行 `pfctl -F all`、关闭 FileVault 或关闭防火墙。
- MacBook 正式考试期间必须接入稳定 AC 电源；**不能把电池电量当作正式电源方案**。若 MacBook 离开 AC、进入低电量或电源适配器异常，立即停止新考生进入并按考试日流程暂停/改期。Mac mini/台式 Mac 还应接 UPS，并验证低电量通知或受控关机。
- 关闭睡眠、休眠、自动关机以及会暂停 Docker 的屏幕锁定路径，但保留账号锁屏和最小桌面暴露。写入电源策略必须在维护窗口执行，不在考试中试错。
- macOS、Docker Desktop、基础镜像和应用更新只在维护窗口进行；更新前先创建配对备份并在 staging 验证，考试中禁止自动重启。
- 时间必须与公司认可时间源同步；开考前核对 macOS、浏览器、容器日志和运维页时间，避免 OTP、token、截止时间或备份证据误判。

状态采集示例（需要管理员权限的输出须脱敏保存）：

```zsh
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate
sudo pfctl -s info
sudo pfctl -sr
sudo fdesetup status
pmset -g custom
pmset -g batt
systemsetup -getusingnetworktime
date -u
```

## 重启恢复和考试窗口

重启恢复顺序固定为：

1. designated host account 登录，确认 Docker AutoStart 已完成、Docker ready、Resource Saver 已关闭，且 MacBook 已接入 AC。
2. LaunchAgent 仅恢复当前选中的 release，使用 `compose up -d --no-build`；它不切换版本、不恢复备份、不批准开考。
3. 运行 `zsh ops/macos/Get-PlatformStatus.zsh --root "$HOME/Library/Application Support/InternalExam"` 和 `zsh ops/macos/Test-FormalPreflight.zsh --backup-path <backup> --browser-smoke-evidence <evidence> --root "$HOME/Library/Application Support/InternalExam"`，核对 release/commit、迁移 head、ARM64、固定 IP/CORS、入口隔离、服务/worker、SMTP、磁盘、电源和备份证据。
4. 主操作员人工确认“允许开考”。即使所有容器自动恢复为 healthy，也必须重新完成预检；恢复不等于批准。

正式项目保持 24×7 best-effort，但考试窗口内必须停止开发和 staging 项目（包括停止它们的 candidate gateway），禁止任何第二个项目写入正式数据库。正式考试时只允许查看状态、日志和运维页；导入、改题、改名单、升级、删除、恢复和发布等写操作按考试日流程冻结。

若账号未登录、Docker 不 ready、MacBook 不在 AC、服务 degraded、时间/网络/备份证据缺失，停止 candidate gateway 或暂停/改期考试；不要临时使用开发 Compose、手工登录后门或第二写入主机补救。

## 客户端和正式证据

当前 Mac UAT 至少覆盖 macOS Chrome、macOS Safari 和一台真实 Android Chrome 或 iOS Safari。嵌入式浏览器、过旧版本和未知 user agent 必须阻断；浏览器运行时不访问公共 CDN、字体或遥测服务。

正式证据包至少包含：macOS/版本、arm64、Docker/Compose 版本、AutoStart/Resource Saver/8 CPU/8 GiB、固定 IP 和 DHCP reservation、CORS、FileVault、pf、防火墙、AC/UPS/睡眠、时间、formal root 权限、release manifest/SHA-256、ARM64 镜像、staging、真实 SMTP、服务重启、备份/独立加密第二存储/restore drill、split ingress、真实桌面/手机 UAT 和 100-client 结果。证据不得包含密码、OTP、token、SMTP secret、数据库 URL、上传内容或不必要个人数据。

Mac 证据只证明 Mac host 的状态；它**不满足**未来 Windows Docker Desktop + WSL2 的 AMD64 staging、恢复、网络、防火墙、备份恢复、桌面/手机 UAT 或正式 promotion。Windows 迁移必须按 [`host-migration.md`](host-migration.md) 重新生成完整证据，并在切换前后保持单写入者。
