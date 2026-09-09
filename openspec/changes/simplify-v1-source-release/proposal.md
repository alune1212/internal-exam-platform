## Why

已确认发布面向现有内网的 v1.0.0 源码版本，保留全部业务功能。当前仓库仍维护未采用的签名发布、Windows 和跨主机运维链，CI 与状态展示没有完全匹配轻量范围。

## What Changes

- **BREAKING**：移除未采用的 Mac/Windows 完整运维脚本及其专用 CI 和合同测试，历史保留于 Git 与 OpenSpec。
- 保留仍被业务、迁移、安全评估和隔离回归调用的数据保护工具。
- 未启用且无备份证据时如实报告未启用，不显示虚假的运行失败。
- 清理无用依赖与重复配置，统一 1.0.0 版本，完成验证后创建标签及 GitHub 源码 Release。
- 非目标：删业务功能、改数据库结构、公网或离线镜像交付、升级现有正式主机、补建备份与签名体系。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `internal-deployment-readiness`：定义源码定版与现网部署的分离，退出未采用运维路径的当前维护责任，以及未启用保障的状态语义。

## Impact

影响 ops/macos、ops/windows、CI、专用测试、运维状态、依赖与版本声明、当前文档和 OpenSpec。保留考试快照、鉴权、保存/交卷和迁移链；正式运行环境与数据不变。
