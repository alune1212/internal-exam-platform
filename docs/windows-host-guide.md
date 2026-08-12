# Windows Docker Desktop + WSL2 未来迁移目标

> 当前正式宿主是 Apple Silicon macOS + Docker Desktop；本页不是当前开考指南。它只描述未来 Windows target 的准备合同。Mac→Windows 的备份、source stop、单写入者、回滚和证据语义见 [`host-migration.md`](host-migration.md)，Mac 证据不满足本页的 Windows acceptance。

Windows target 在真实 staging、恢复、网络、防火墙、SMTP、浏览器和 100-client 门禁全部通过并完成人工 promotion 前，不得开放应考人员入口，也不得与 Mac 并行写入。

## 主机和账号

- 使用受公司资产管理的 Windows 11 Pro 未来 target 主机，开启 CPU 虚拟化、WSL2 和 Docker Desktop；Docker Desktop 后端固定选择 WSL2，部署只使用 Docker Compose。
- 创建一个专用 Windows 操作系统账号运行平台，不用于日常办公、网页浏览、邮件或安装无关软件。该账号保管 `C:\ProgramData\InternalExam`；应用内仍使用主/备两个具名操作员账号。
- 磁盘使用 NTFS；系统盘和第二存储均启用公司认可的全盘加密。第二存储必须与主机本地备份目录物理或逻辑独立。
- BIOS/Windows 设置为来电恢复开机；正式运行期间禁用睡眠、休眠和自动关机。Docker Desktop设为登录后启动，并在主机重启后人工确认所有容器 healthy 再开考。

## 安装核验

在 PowerShell 逐项确认：

```powershell
wsl --status
wsl --update
docker version
docker compose version
```

Docker Desktop 只保留项目需要的 CPU、内存和磁盘资源；不得启用公网容器端口、Kubernetes 或不相关扩展。执行 `Initialize-InternalExamHost.ps1` 后，确认目录 ACL 已关闭继承，只有当前专用账号、Administrators 和 SYSTEM 可访问。

## 网络和防火墙

- 为主机保留固定私网 IPv4（DHCP reservation 或公司允许的静态地址），保持公司时间同步和 DNS 正常。
- Windows 防火墙只在 Private/Domain profile 允许已批准办公网段访问 TCP 8080；Public profile 一律阻断。禁止路由器公网转发、UPnP、访客网和 VPN 非授权网段访问。
- TCP 8081、5432、5173 只绑定 `127.0.0.1`。操作员必须坐在正式主机本地使用 `http://127.0.0.1:8081`；不能从办公电脑远程打开管理入口。
- 普通办公设备和手机与平台共用现有办公局域网，因此第一阶段 HTTP 风险必须按 [`security-http-exception.md`](security-http-exception.md) 明确接受，不能描述为安全传输。

## 账号、名单和 Windows 外部验收

- 从 Mac paired backup 恢复后，先取得 writer fence、协调写冻结、无 `in_progress` attempt、独立加密第二副本和隔离 restore 证据；运行只读 account-migration preflight，确认邮箱可规范化且无重复、历史 attempt 都有 scope、scope 可补齐冻结 `roster_email`/`roster_name`。预检失败不得写 schema、账号、scope 或 challenge。
- 先做 additive/backfill 并核对账号/scope/attempt 计数、外键、冻结 roster 和题池；随后才允许 destructive migration 删除旧全局人员/组织/出席字段及登录占位数据。该边界后禁止 `alembic downgrade`，失败只能停止 writer，使用上一 release + verified paired backup restore-only 回滚并重跑全部门禁。
- Windows 真实桌面/手机 UAT 必须覆盖：统一“邮箱登录”六位 OTP（十分钟、单次、最多五次、60 秒重发冷却）及 SMTP fail-closed；新邮箱/pending 完成显示名称后才取得四小时 session，inactive 返回不可用；不提供 remember-me，Profile 仅可改显示名称且邮箱只读；同源邀请回跳不携带 token/OTP/invite code，发布后显式 initial-send、failed-only resend，正式报表只读冻结 roster identity。
- 通过上述 UAT、真实邀请 SMTP、服务恢复、容量和 second-copy restore 后，才能人工批准 promotion；Mac 的证据不得代替 Windows evidence。

## 电源、时间和更新

- `w32tm /query /status` 必须显示已同步；考前同时检查 Windows 时间、浏览器时间和平台运维页时间。
- Windows Update、Docker Desktop、WSL2、镜像和应用更新不得在考试进行中自动重启。没有固定维护窗口；发现更新需求时另行安排、先备份、在 staging 验证后再发布。
- 正式发布后七天冻结；每季度至少核对 Windows/Docker/WSL2 更新、磁盘健康、恢复演练和防火墙规则。季度检查不等于固定停机窗口。

## 24×7 边界

系统自动重启容器并持续运行，但仍是单主机、无高可用。主机、磁盘、Docker Desktop 或办公网络发生严重故障时，允许暂停或改期考试。不要通过临时复制数据库、双机同时写入或现场搭建未经验证的新主机来伪造高可用。
