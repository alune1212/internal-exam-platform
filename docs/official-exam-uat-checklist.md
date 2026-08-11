# macOS 正式考试 UAT 与证据清单

每次正式发布和考试前在当前 Mac 宿主执行。候选入口固定为 `http://192.168.2.34:8080`；操作员入口严格为 Mac 本机 `http://127.0.0.1:8081`。任何阻断项失败都不得开考。未来 Windows Docker Desktop + WSL2 迁移必须使用同一清单的 Windows 版本重新取证；Mac 证据不能替代 Windows acceptance。

## 1. 宿主、账号、电源和网络

- [ ] designated host account 已登记；可以是现有受管 Mac 账号，不要求新建账号。Docker Desktop、LaunchAgent 和 formal 配置只由该账号运行。
- [ ] macOS、Apple Silicon/arm64、Docker Desktop 和 Docker Compose 可用；Docker Desktop 已启用登录后启动并关闭 Resource Saver。
- [ ] Docker Desktop 资源固定为 8 CPU/8 GiB，磁盘余量满足容量/备份合同；没有启用 Kubernetes、无关扩展或公网端口。
- [ ] MacBook 全程接入稳定 AC；电池不作为正式电源方案。Mac mini/台式 Mac 的 UPS 和受控关机证据已记录。
- [ ] 正式根目录在工作树外，目录 0700、`formal.env`/state/evidence 0600；configuration、releases、backups、evidence、diagnostics、state 均由 designated host account owner-only 管理。
- [ ] FileVault（或公司认可的等效全盘加密）、Application Firewall 和 pf 状态可核验；恢复密钥不在证据包中。
- [ ] `192.168.2.34/24` 已由 DHCP reservation 固定；实际接口、租约和路由均匹配，`INTERNAL_LAN_BIND_IP=192.168.2.34`。
- [ ] pf/受管防火墙仅允许 `192.168.2.0/24` 到 `192.168.2.34:8080`；`8081` 只监听 `127.0.0.1`。没有公网转发、访客网或未授权 VPN。
- [ ] CORS 精确为 `http://192.168.2.34:8080`；已确认当前使用范围仍符合 [`security-http-exception.md`](security-http-exception.md)。

## 2. 自动化、发布包和 staging

- [ ] CI backend、frontend、release-gates、browser-E2E、Mac zsh/LaunchAgent 检查全部通过。
- [ ] `openspec validate --all --strict --no-interactive` 通过。
- [ ] 最终镜像 Python/npm/Trivy 扫描完成：无 Critical；High 均有具名“不可利用”理由，否则阻断。
- [ ] `sh ops/e2e/run-capacity-gate.sh` 通过 100-client 阈值，保留 JSON 和 SHA-256；证据绑定 Mac ARM64、8 CPU/8 GiB 和 release commit。
- [ ] `zsh -n ops/macos/*.zsh` 通过，LaunchAgent plist 通过 `plutil -lint`；正式 Compose render 只暴露候选 8080，其他端口 loopback。
- [ ] release bundle 的 manifest、SHA-256、Git commit、migration head、image digest、ARM64 支持和安全扫描证据一致；发布包不含 `.env`、数据库、媒体、备份或诊断。
- [ ] Mac staging 使用独立 project、18080/18081/15432/15173 和独立 volume 完成构建、迁移、候选/管理路由隔离、浏览器 E2E、离线资源检查和服务重启恢复；清理后无残留，未触碰 formal volume。
- [ ] 考试窗口开始前已停止 development/staging project，只留下一个 formal writer；记录 writer generation/commit。
- [ ] `zsh ops/macos/Install-LaunchAgents.zsh --root "$HOME/Library/Application Support/InternalExam"` 成功；两个 plist 均 loaded，日志路径有界且没有 secret。

## 3. 正式预检和恢复边界

- [ ] `zsh ops/macos/Get-PlatformStatus.zsh --root "$HOME/Library/Application Support/InternalExam"` 显示 db、backend、auto-submit-worker、frontend、candidate Nginx 和 operator Nginx healthy，且 formal project name 为 `internal-exam-formal`。
- [ ] 运维页显示版本、migration、服务、worker 心跳、运维锁、磁盘、备份、第二副本、恢复演练、保留和安全扫描状态；stale/skipped/failed 均已解释。
- [ ] 动态磁盘水位满足“操作后至少 20 GiB 且不少于三倍占用”。
- [ ] 已创建并验证 pre-exam 配对备份；正式升级另有 pre-upgrade 配对备份。
- [ ] 使用真实 SMTP 向 `PREFLIGHT_SMTP_RECIPIENT` 发送探针成功。停止/阻断 SMTP 后，验证码无法投递且没有共享码、人工 token 或登录后门；恢复 SMTP 后重新申请成功。
- [ ] `zsh ops/macos/Test-FormalPreflight.zsh --backup-path <backup> --browser-smoke-evidence <evidence> --root "$HOME/Library/Application Support/InternalExam"` 全部 checks 为 passed，并保留 JSON 与 SHA-256；预检只给出 `approval=manual-required`。
- [ ] LaunchAgent 只在 Docker ready 后恢复已选 release、使用 `--no-build`，不 build/promote/restore/删除/轮换 session。
- [ ] 预检全部通过后由主操作员人工确认“允许开考”；Docker/worker 自动恢复或 status 变绿不构成批准。

## 4. 真实桌面和手机浏览器

至少使用一台真实 macOS Chrome、一台真实 macOS Safari 和一台真实 Android Chrome 或 iOS Safari；不以模拟器替代全部实机验证。

- [ ] 两端均能提前 30 分钟申请 OTP；到点前不能开始，到点后可开始，开考 15 分钟后不能新建 attempt。
- [ ] 未登记、同名歧义和有效身份申请验证码的页面响应一致，不泄露名单；只有有效身份收到真实邮件。
- [ ] 一台设备开始考试并保存；刷新后题目快照、截止时间、修订号和答案保持。
- [ ] 断开网络后选择答案出现本地待同步草稿；恢复网络后成功同步且不覆盖更高服务器修订。
- [ ] 第二台设备用新鲜 OTP 接管后，第一台设备继续保存收到会话冲突；快照、已保存答案和截止时间不重置。
- [ ] 键盘、焦点、标签、错误提示、200% zoom、手机固定操作区和横竖屏布局可用；页面不请求公共 CDN/字体。
- [ ] 交卷后立即显示分数/通过状态，但未发布解析；全部 attempt terminal 后管理员手动一次性发布，考试人刷新后才看到答案解析。
- [ ] 排名仅管理端可见。作废 attempt 后保留证据；批量补考必须先预览、确认名单/影响，再发放。
- [ ] 练习作答立即显示正确答案/解析并锁定；重做新增历史；错题“已掌握”按最后一次结果变化且不串候选人。

## 5. 开考后写入门禁和事件

- [ ] 至少一个 attempt `in_progress` 时，备份写冻结、保留删除、升级和 close-session 都拒绝或按设计等待；正式答题保存/交卷不被磁盘水位门禁阻断。
- [ ] 开考后管理端导入、改题、考试结构变更等写操作被只读运维窗口阻断；全部交卷后恢复。
- [ ] 停止 worker，让测试 attempt 超时后恢复 worker；首次扫描补交，后续扫描不重复，心跳在失败期间不会虚假刷新。
- [ ] 故障事件记录事实、影响、处置和补考/作废关系；日志与诊断不含 OTP、token、密码、SMTP 凭据或完整个人数据。
- [ ] 开考期间 development/staging 和任何未来 Windows project 均保持停止；不允许第二个 writer。

## 6. 备份、第二副本、恢复和回滚

- [ ] 独立加密卷已挂载；`zsh ops/macos/Capture-SecondCopyStorageEvidence.zsh --root "$HOME/Library/Application Support/InternalExam"` 通过，并证明 `SECOND_COPY_PATH` 可写、已加密且 `ParentWholeDisk` 不同于正式根目录所在磁盘。
- [ ] daily opportunity backup 在无变化时记录 skipped，有变化时短暂冻结并生成验证备份；本机只保留最近三份成功副本。
- [ ] post-exam/pre-upgrade 备份包含数据库、媒体、manifest、SHA256SUMS、`SUCCESS`，并同步到与 Mac 不同物理宿主/磁盘的独立加密第二存储；不可用/校验失败时不得写成功。
- [ ] 从第二副本运行一次性 restore drill，migration、表计数和媒体校验通过；正式项目未改变，临时 project/volume 已清理。
- [ ] 同宿主回滚演练使用“上一版本发布包 + 升级前配对备份”：迁移/写入前可安全回到上一 release；迁移或写入后必须授权破坏性恢复配对备份，不使用 `alembic downgrade`。
- [ ] 目标宿主迁移前，`zsh ops/macos/Prepare-HostCutover.zsh --target-host windows-docker-wsl2 --confirmation "PREPARE HOST CUTOVER"` 成功；该命令在 writer fence 内自行创建最终 `cutover` 配对备份和独立加密第二副本，并证明无进行中 attempt、整个正式 Compose 已停止及 source writer generation 已记录。只有这一步完成后才允许 Windows target expose。
- [ ] Mac target 完成独立 restore/UAT 后，`zsh ops/macos/Accept-HostCutover.zsh --final-backup-path <backup> --browser-smoke-evidence <evidence> --source-stopped --confirmation "ACCEPT HOST CUTOVER"` 证据通过；该 zsh 只在 Mac target/回切运行，Windows target 不运行它，而使用未来 Windows 适配器；人工批准仍是单独步骤。
- [ ] Windows target 一旦产生写入，回切 Mac 必须先从 Windows 生成新的验证配对备份；不能让已停机 Mac 直接重启形成双写，也不能使用过期 source state。
- [ ] `zsh ops/macos/Export-Diagnostics.zsh --root "$HOME/Library/Application Support/InternalExam"` 生成有界、脱敏、带 checksum 的 ZIP；能从中定位版本、服务、worker、锁、磁盘和备份状态。

## 7. 考后关闭和证据包

- [ ] 全部 attempt terminal；结果解析已按决定发布或保持未发布。
- [ ] post-exam 本机备份及独立加密第二副本校验通过。
- [ ] `zsh ops/macos/Close-ExamSessions.zsh --confirmation "CLOSE ALL SESSIONS" --root "$HOME/Library/Application Support/InternalExam"` 成功，旧 admin/candidate token 均为 401，新登录和 readiness 正常。
- [ ] 正式证据包包含 host、release/preflight、题池与名单摘要、真实 SMTP、时间、电源、网络/pf、incident/void/retake、备份、第二副本、restore drill、解析发布、writer generation 和 close-session 引用；每个文件有 SHA-256。
- [ ] 证据包不含密码、OTP、token、SMTP secret、数据库连接串或不必要的个人明细。
- [ ] 证据包明确标注 `host_os=macOS`、`architecture=arm64`；不得把它标记为 Windows acceptance。

## Stop Conditions

出现以下任一情况立即停止开考或暂停考试：候选 8080 暴露管理/API docs；操作员入口不是 loopback；DHCP reservation 或 pf 规则不满足；MacBook 不在 AC；真实 SMTP 失败；worker/数据库/backend 不 healthy；migration/version/checksum 不一致；浏览器发起公共 Internet 请求；设备接管后旧设备仍可保存；答案修订丢失；快照变化；管理写冻结失效；安全扫描/100-client 门禁失败；磁盘水位不足；正式备份或第二副本无法验证；restore drill 触碰正式项目；LaunchAgent 自动批准开考；close-session 在进行中考试时仍轮换 secret；日志/诊断泄露 secret 或 PII。

严重主机或办公网络故障无法在既定边界内恢复时，允许暂停或改期；不要现场引入双写、高可用、人工登录后门或未经验证的新部署路径。
