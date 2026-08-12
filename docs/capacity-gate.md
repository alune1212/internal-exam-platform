# 100 客户端容量门禁

当前 Mac 正式发布候选必须在与正式配置隔离、可丢弃的 Nginx、backend、worker、PostgreSQL Compose 栈上运行；开发和 staging 项目在门禁期间不得连接 formal volume：

```bash
./ops/e2e/run-capacity-gate.sh
```

门禁固定创建 100 个使用规范化邮箱的隔离 active 账号/应考 scope，并同时执行开始考试、修订号保存和交卷。fixture 不使用姓名、旧人员字段或全局出席标记作为身份；正式 report/roster identity 只来自 per-exam scope。通过条件为：请求错误数为 0、100 份记录全部交卷、开始/保存/交卷的 P95 分别不超过 5000/2000/3000 ms、测试期间数据库连接数不超过 40、worker 心跳不超过 90 秒。结果和 SHA-256 写入 `.runtime/e2e/evidence/`。任一条件失败时命令返回非零，不得生成新的正式发布证据；这份证据必须绑定 Mac 的 Docker 资源、ARM64 镜像和 release commit。

开考门限包含固定试卷快照创建成本，按 100 人同一时刻点击的突发场景设为 5 秒；保存和交卷仍保持更严格门限。Docker Desktop 资源按正式 Mac 合同固定为 8 CPU/8 GiB；门限不通过增加数据库连接数或临时关闭限制来换取。

这是一阶段“少量人员、偶发正式考试”的可重复最低门槛，不表示系统支持持续 100 人高并发，也不构成高可用承诺。Mac 的 100-client 证据只证明当前 Mac host，不能满足未来 Windows Docker Desktop + WSL2 的 AMD64 acceptance；Windows 迁移后必须重新运行。若正式使用规模、宿主资源或网络条件改变，应重新基准测试并调整阈值。
