---
title: 知试（Zhishi）前端重构与设计
date: 2026-06-12
status: approved-for-implementation
spec-version: 1.0
---

# 知试（Zhishi）前端重构与设计

## 1. 概述

将公司内部临时考试与刷题平台的前端，按 `frontend/DESIGN.md` 锁定的 Cal.com 现代 SaaS 骨架，叠加 **C · 现代学术（Academic Editorial）** 的视觉诠释，做一次完整重构。同时打磨桌面与手机两端的体验，并按 9 个工作日的工作量分阶段落地。

不修改后端逻辑、不改路由树、不引入新依赖（React 19 / Tailwind 3.4 / Radix UI Slot / TanStack Query+Table / React Hook Form+Zod / lucide-react 全部沿用）。

## 2. 决策摘要

| # | 维度 | 决定 |
|---|---|---|
| 1 | 风格调性 | A · 原汁原味的 Cal.com 风（白底 + 黑 CTA + 几何 display 字） |
| 2 | 暗色模式 | 不上，只做亮色 |
| 3 | 桌面 / 手机打磨 | C · 同样重要，双场景都打磨 |
| 4 | Display 字体 | Manrope 600 + -0.04em tracking |
| 5 | Body 字体 | Inter 400 / 500 / 600 |
| 6 | Mono 字体 | JetBrains Mono 400 / 500（题号、倒计时、版本号） |
| 7 | 管理后台浓度 | A · 统一轻量（与候选端共享视觉语言，侧栏换黑色 pop-out） |
| 8 | 作答页布局 | A · 单题聚焦（Focus Mode），桌面 + 手机同形态 |
| 9 | 考生身份验证 | 保持「填名字就能进」的信任制 |
| 10 | 品牌名 | 知试（Zhishi）· wordmark「知试」+ 28×28 黑色 Z 圈 |
| 11 | 整体方向 | C · 现代学术（Cal.com 骨架 + 学术 / 编辑感细节） |
| 12 | 新增依赖 | `@radix-ui/react-dialog`（用于 Dialog / Sheet 弹层） |

## 3. 品牌系统

### 3.1 色彩

| Token | 值 | 用法 |
|---|---|---|
| `--canvas` | `#ffffff` | 主背景 |
| `--canvas-warm` | `#fafaf7` | 浅纸色，替代 #f5f5f5 给"翻书"感 |
| `--ink` | `#111111` | 主文字、primary |
| `--ink-soft` | `#2a2a2a` | 二级标题 |
| `--body` | `#374151` | 正文 |
| `--muted` | `#6b7280` | 提示、章节编号 |
| `--hairline` | `#e5e7eb` | 边线 |
| `--hairline-soft` | `#f3f4f6` | 隔断 |
| `--surface-card` | `#f5f3ee` | 浅米色，feature card |
| `--surface-elev` | `#ffffff` | 弹层、modal 背景 |
| `--footer` | `#0a0a0a` | 页脚、admin 侧栏 |
| `--footer-soft` | `#a1a1aa` | 页脚文字 |
| `--success` | `#166534` | 答对、考试进行中 |
| `--warning` | `#b45309` | 即将开始、提示 |
| `--error` | `#b91c1c` | 答错、必填提示 |

唯一相对 `DESIGN.md` 的偏离：把冷灰 `#f5f5f5` 改成更暖的 `#f5f3ee` / `#fafaf7` 米白，让"翻书"感出来。

### 3.2 字体

- **Display**: Manrope 600 + -0.04em tracking。h1 / h2 / h3。
- **Display Italic**: Manrope 600 italic。用于编辑感副标、章节编号、登录页 h1。
- **Body**: Inter 400 / 500 / 600。
- **Mono**: JetBrains Mono 400 / 500。tabular-nums 用于题号、倒计时。

### 3.3 字号

| Token | 桌面 | 手机 | 用法 |
|---|---|---|---|
| `text-display-2xl` | 72px | 40px | 登录页 h1 |
| `text-display-xl` | 56px | 32px | 章节大标题 |
| `text-display-lg` | 40px | 28px | 页面 h1 |
| `text-display-md` | 28px | 22px | 卡片 / 区块 h2 |
| `text-display-sm` | 22px | 18px | 子标题 |
| `text-body-lg` | 17px | 16px | 引言 / 描述 |
| `text-body` | 15px | 15px | 正文 |
| `text-body-sm` | 13px | 13px | 提示、注脚 |
| `text-caption` | 11px | 11px | 全大写小标签（letter-spacing 0.16em） |

### 3.4 圆角

| Token | 值 | 用法 |
|---|---|---|
| `rounded-pill` | 9999px | **primary 按钮**（学术感关键：所有按钮变 pill） |
| `rounded-lg` | 16px | 卡片（比 Cal.com 的 12px 略大，更"翻书"） |
| `rounded-md` | 8px | 输入框、辅助按钮 |
| `rounded-sm` | 4px | 标签、徽章 |
| `rounded-circle` | 50% | 头像、Z 圈 |

### 3.5 阴影

```
--shadow-card:    0 1px 2px rgba(17,17,17,0.04), 0 4px 12px rgba(17,17,17,0.04)
--shadow-pop:     0 8px 24px rgba(17,17,17,0.08)
--shadow-elevate: 0 16px 40px rgba(17,17,17,0.10)
```

学术感的轻浮起，不是 Material 那种深阴影。

### 3.6 间距

按 `DESIGN.md` 的 4/8/12/16/24/32/48/96 节奏不变。学术感节奏：section 之间 96px，content 与 subhead 之间 32px，body 行距 1.7。

## 4. 组件库

### 4.1 基础组件

#### Button — `components/ui/button.tsx`

- **形态**：圆角从 `rounded-md` 改为 **`rounded-pill`**（9999px）。
- **size**：
  - `sm` — h-9, px-4, 13px
  - `default` — h-11, px-6, 14px
  - `lg` — h-12, px-8, 15px
  - `icon` — 36×36 圆形
- **variant**：
  - `default` — bg `var(--ink)`, text `#fff`, hover `#0a0a0a`
  - `outline` — bg `var(--canvas)`, border `1px var(--ink)`, hover bg `var(--canvas-warm)`
  - `ghost` — 透明，hover bg `var(--surface-card)`
  - `link` — text `var(--ink)`, underline-offset 4
- **detail**：按钮内 icon 用 `data-icon="inline-start"`；不引入 drop shadow。
- 沿用 `asChild` + Radix `Slot`（已是当前实现）。

#### Card — `components/ui/card.tsx`

- 圆角 `rounded-lg`（16px），背景 `--canvas` 或 `--surface-card`，border `1px --hairline`，轻 `--shadow-card`。
- `CardHeader` 改造为 **chapter 标签（caps + tracking 0.16em）+ 标题（display-sm）+ 描述（body-sm）** 三行结构 + 1 道 hairline 分割。
- `CardContent` padding `p-6 lg:p-8`；手机 `p-5`。

#### Input — `components/ui/input.tsx`

- 圆角 `rounded-md`（8px），高度 h-11，bg `#fff`，border `1px --hairline`。
- focus 时 border 变 `--ink`，加 1px ring。
- label 放在 input 上方，**中英双语**（`姓名 · Name`），中英文之间用 middle dot + 空格。

#### Label — `components/ui/label.tsx`

- `text-body-sm` 600 weight + 0.04em tracking + 中英双语。

#### Badge — `components/ui/badge.tsx`

- 圆角 `rounded-sm`（4px），padding `1px 8px`，字号 11px，**全大写 + letter-spacing 0.16em**。
- variant：`default`（黑底白字）、`outline`（白底黑边）、`muted`（米色底深灰字）。
- 替换 shadcn 默认的圆胶囊形态；用印章感。

#### Table — `components/ui/table.tsx`

- 不做斑马纹、不做粗分割线；只用 `1px --hairline-soft` 行间分隔。
- 表头 `text-caption` 全大写 + tracking 0.12em，颜色 `--muted`；数据行 `text-body`。
- 手机端用 **Card View 模式**自动启用：每行变成独立卡片（用 TanStack Table `columnVisibility` + 自定义 mobile renderer）。

#### Dialog / Sheet — 新增

- 弹层用 `var(--surface-elev)` + `var(--shadow-pop)` + 16px 圆角。
- 手机端默认 `sheet`（底部滑出），桌面端 `dialog`（居中弹层）。
- 基于 Radix UI Primitives。需新增依赖：`@radix-ui/react-dialog`（已确认未在当前 `package.json`）。

#### Skeleton — 新增

- 淡灰条 + 1500ms shimmer 动画（CSS keyframes）。

### 4.2 学术感专用组件

#### `ChapterNumber` — 章节编号

- 一道横线 + 数字 + 文字（全部 italic + 全大写 + tracking 0.18em）。
- 例：`——— CHAPTER 01 · WELCOME`。
- 用于每个页面 / 区块的 h1 上方作为小引子。

#### `NamePlate` — 考试人名牌

- 形态：`圆形头像（含 Z 圈或姓名首字）+ 姓名（font-display 600）+ 副标（employee_no · department，italic caption）`。
- 用于顶栏右侧、登录成功后、考试结果页。
- 替身头像用 pastel 圆圈 + 大写首字。pastel 配色：`#fef3c7` (黄) / `#dbeafe` (蓝) / `#dcfce7` (绿) / `#fce7f3` (粉) / `#e0e7ff` (靛)。

#### `Timer` — 倒计时

- 大号 Manrope 600，**tabular-nums**，字号 32px。
- 上方一道 `REMAINING · 剩余时间` 全大写小标签。
- 倒计时 ≤ 5 分钟时数字变 `--error` 颜色，配合 1000ms `pulse` 动画。

#### `ProgressCapsule` — 进度胶囊

- 形态：`Q 03 / 10 · 30%`，pill 形标签，内含 1px hairline 分割的进度条。

#### `OptionCard` — 考试选项卡

- 整张可点击的卡片：左侧 24×24 圆形单选 / 多选指示器 + 右侧选项文字。
- 选中态：bg `--surface-card` + border `--ink`。
- 未选态：白底 + hairline 边。
- 圆角 `rounded-md`（8px），高度自适应，手机端最小 56px。

#### `StatusPill` — 状态徽章

- 替换 shadcn Badge 圆胶囊形态；用印章感 badge。
- 颜色语义：`var(--success)` 答对 / 进行中、`var(--warning)` 即将开始、`var(--error)` 答错 / 必填、`var(--ink)` 默认。

#### `QuestionNavigator` — 题号导航

- 重做：左侧一道垂直 hairline + 数字（24px mono tabular），右侧"已答 / 未答"dot 指示。
- 移动端改成底部 sticky 的 BottomSheet：FAB 按钮唤起，半屏弹层。
- 桌面端保留右侧悬浮固定，但视觉变成"目录式"——题号按题型分章节，章节标题 italic caps + 题号 mono。

#### `TopNav`（候选端）

- 64px 高，bg `--canvas`，底部 `1px --hairline-soft` 分割。
- 左侧：`Wordmark` 组件（Z 圈 28×28 + "知试" Manrope 600 18px + 副标 "— internal exam platform" italic 11px muted）。
- 中部：导航 pills，active 态用下划线（不用 bg 胶囊）。
- 右侧：`NamePlate` + 登出 icon-only button。
- 移动端：汉堡按钮唤起底部 sheet。

#### `AdminSideRail`（管理端）

- 240px 宽，bg `#0a0a0a`，文字 `#a1a1aa`，active 项文字 `#fff`。
- 顶栏：`Wordmark` 组件（白底 Z 圈 + 白色 Manrope 600 + 副标 "admin"）。
- 移动端：折叠成底部 sheet（FAB 唤起）。

#### `Footer`

- bg `#0a0a0a`，文字 `#a1a1aa`，padding 32–48px。
- 所有页面共享（除登录页）。

## 5. 信息架构

### 5.1 路由表（沿用现状，不改）

```
/                                        → 重定向到 /login
/login                                   候选人登录
/practice                                练习模式
/exams                                   可参加考试列表
/exams/:examId/start                     考试说明
/exams/:examId/taking                    考试作答（Focus Mode）
/exams/:examId/result                    考试结果
/exams/:examId/ranking                   成绩排名

/admin/login                             管理员登录
/admin/dashboard                         仪表盘
/admin/questions                         题库列表
/admin/questions/import                  题库导入
/admin/exams                             考试配置列表
/admin/exams/:examId/edit                考试编辑
/admin/exams/:examId/candidates          应考名单导入
/admin/reports/scores                    个人成绩
/admin/reports/questions                 题目正确率
/admin/reports/wrong                     错题排行
/admin/reports/absent                    未参加人员
```

### 5.2 用户旅程

候选端：登录 → 看到欢迎语 + 当前考试概览 → 练习流（不计入成绩）/ 正式考试流（说明 → Focus Mode 作答 → 暂存 / 提前交卷 / 到时自动交卷 → 结果 → 排名）。

管理端：登录 → 仪表盘（4 核心指标 + 最近活动）→ 准备考试（题库 → 导入 → 考试编辑 → 应考名单）→ 监控（仪表盘）→ 报表（4 报表页）。

### 5.3 页面优先级

- **P0（深度打磨）**：`/login`、`/practice`、`/exams/:id/taking`、`/exams/:id/result`
- **P1（标准打磨）**：`/exams`、`/exams/:id/start`、`/exams/:id/ranking`、`/admin/dashboard`、`/admin/exams/:id/edit`、`/admin/questions/import`
- **P2（功能完整）**：4 个报表页、`/admin/questions`、`/admin/exams`

## 6. 关键页面规范

### 6.1 登录页（候选人）

- 64px 顶栏（Z 圈 + wordmark + italic 副标）+ 主体居中卡片。
- 主体布局：单列居中（手机）/ 单列居中 + 左侧 chapter 头（桌面）。
- 内容：
  - `ChapterNumber` `CHAPTER 01 · WELCOME`
  - h1（Manrope 600 italic，使用 `text-display-2xl`——桌面 72px / 手机 40px）"坐下来，开始考试。"
  - 描述段（`text-body-lg` 16–17px / 1.7 行距 / `text-muted`）
  - 卡片（米色 `var(--canvas-warm)` + 16px 圆角 + 1px hairline）：
    - 姓名（必填）· 中英双语 label
    - 员工号（可选）· 中英双语 label
    - 提交按钮（pill 高 48px，bg `var(--ink)`）
  - 错误态：卡片底部红色 caption 段
  - 成功后：导航到 `/exams`

### 6.2 考试作答页（Focus Mode）

- **桌面端（≥1024px）**：
  - 顶栏 64px（wordmark + 考试名 + 退出按钮）
  - 主区布局：`grid-cols-[1fr_240px]`
  - 进度胶囊（顶部）：左侧 `PROGRESS Q 03 / 10` + 进度条 + 右侧 `REMAINING 24:18`（mono tabular）
  - 题干卡（米色 `--canvas-warm` + 16px 圆角）：
    - 顶部 chapter：题型（italic caps）+ 分值
    - h2（Manrope 600 26px / -0.02em）
    - `OptionCard` 列表（每张至少 56px 高）
    - 底部一行：上一题 / 暂存 / 下一题（pill 按钮）
  - 右侧 `QuestionNavigator`（米色卡 + 16px 圆角）：
    - 章节分组（CHAPTER A · SINGLE 等 italic caps）
    - 5 列题号按钮（mono 数字）
    - 已答：`bg #166534`；未答：白底 hairline；当前：黑色边框 + 2px ring
    - 底部"提前交卷"按钮（pill 黑底）

- **手机端（<768px）**：
  - 顶栏极简：进度 + 倒计时单行
  - 进度条（3px）
  - 章节 + 题干 + `OptionCard`（h ≥ 48px）
  - 底部一行：上一题 / 下一题
  - **底部 sticky 进度胶囊**（黑底 capsule，超出屏幕底部 12px）：
    - `Q 03 / 10` + 进度条 + `24:18` + ≡ 唤起图标
    - 点击 ≡ 唤起半屏 sheet 显示完整 `QuestionNavigator`

- 倒计时计算：基于 attempt.started_at + duration_minutes，1 秒 1 tick。
- 倒计时 ≤ 5 分钟：数字 `--error` + 1000ms pulse 动画 + `aria-live="polite"` 提示。
- 题目切换支持键盘 ← / →。

### 6.3 考试结果页

- **桌面端**：
  - 顶栏（wordmark + 当前 Tab：结果）
  - 主区布局：`grid-cols-[320px_1fr]`
  - 左侧成绩卡（全黑 `#0a0a0a` + 16px 圆角 + 白字）：
    - `CHAPTER 99 · RESULT`
    - h1 italic "考试结束。"
    - `YOUR SCORE 85 / 100`（大号 Manrope 64px / -0.04em）
    - 正确 / 错误计数（caption + 20px 数字）
    - "查看排名" pill 按钮（白底黑字）
  - 右侧答案列表：
    - 顶部一行：章节标签 + 切换按钮（全部 / 只看错题）
    - 每条答案卡（白底 hairline / 米色 hairline）：
      - 题号（mono 12px，绿或红）
      - 题干前 30 字（body 14px）
      - 对错状态（caption，绿或红）
      - 你的答案 / 正确答案

- **手机端**：左侧成绩卡占整宽（黑色），下方答案列表单列。

### 6.4 练习页

- 桌面端布局与作答页同结构，但顶部右侧改 `SubmitQuestion` 按钮组，提交后即时显示对错 + 解析。
- 题目提交后不需要计时。
- 题号导航已答题目按对错着色（绿 / 红）+ 颜色语义同作答页。

### 6.5 排名页

- 顶部 chapter 头 + h1 italic。
- 表格（按 desktop / mobile 切换）：
  - 桌面端：5 列（RANK / NAME / DEPT / SCORE / TOTAL），第 1 名整行翻黑（白字），2-3 名白底。
  - 手机端：每行独立卡片，1-3 名差异用左侧色条（黑 / 米 / 白）而非整行翻黑。
- 题号 / 分数列用 `JetBrains Mono` + tabular-nums。

### 6.6 管理员登录

- 与候选人登录同布局语言（chapter 头 + italic h1 + 米色卡 + pill 按钮）。
- 桌面端右侧改全黑列（呼应"唯一暗色表面"），叠 0.08 alpha 白色 radial 点阵做"安静后台"纹理。
- 副标 wordmark 后跟 `— admin console` 斜体。

### 6.7 仪表盘

- 黑色 240px 侧栏（`AdminSideRail`）+ 右侧主体。
- 主体背景 `--canvas-warm`，padding 32px。
- 顶部：chapter 头 + italic h1 "一切就绪。"
- 4 个 `MetricCard`（白底 hairline 卡 + 16px 圆角）：
  - 顶部 italic caps 标签（QUESTIONS / EXAMS LIVE / SUBMITTED / ABSENT）
  - 28–40px 数字（Manrope 600）
  - 底部 caption 描述
  - 颜色语义：EXAMS LIVE 数字用 `--success`、ABSENT 数字用 `--warning`、其余 `--ink`
- 最近活动列表（白底 hairline 卡），每行左侧 6×6 圆点（绿 / 橙 / 红）+ 考试名 + caption + 右侧"X 分钟前"。

### 6.8 考试编辑

- 左侧黑侧栏（与仪表盘同）+ 右侧主体（米色背景）。
- 顶部：chapter 头 + italic h1 + 右侧"取消 / 保存配置"按钮组。
- 主体卡（白底 hairline + 24px padding）：
  - 考试名称（中英 label，input 默认值）
  - 时长（number input） + 状态（自定义 dropdown，显示 LIVE 状态点 + 文字）
  - 抽题规则（JSON 编辑器：黑底 + JetBrains Mono 12px + 语法高亮）
  - 应考人员条（米色内嵌行：左侧 CANDIDATES 标签 + 中间人数描述 + 右侧"管理应考"按钮）

### 6.9 报表页（4 张）

- 4 张报表（个人成绩 / 题目正确率 / 错题排行 / 未参加人员）共享 `ReportPage` 容器。
- 顶部 chapter 头 + italic h1 + 描述段。
- 主体表格（与排名页同规则：桌面表格 / 手机 card list）。
- 数字列用 mono tabular；排名列用 mono；分数列用 mono + 颜色语义。

### 6.10 共享状态

- **空态**（`EmptyState`）：居中布局 + chapter 小引子 + italic h2 + 描述段 + 主操作按钮。
- **错态**：同空态布局但 chapter 用 `--error` 色 + h2 用 italic + "返回 / 重试" 双按钮。
- **加载态**（`Skeleton`）：淡灰条 + 1500ms shimmer + 底部 `LOADING · 加载中…` 标签。

## 7. 响应式策略

### 7.1 断点

沿用 Tailwind 3.4 默认：

```
sm  ≥ 640px
md  ≥ 768px
lg  ≥ 1024px
xl  ≥ 1280px
2xl ≥ 1536px
```

按"移动优先"写 utility。

### 7.2 关键折叠点

| 元素 | 手机 | 桌面 |
|---|---|---|
| 顶栏 | Z 圈 + wordmark + 汉堡 | Z 圈 + wordmark + italic 副标 + 横向 nav + NamePlate |
| 侧栏（管理） | 隐藏，FAB → 底部 sheet | 240px 固定黑栏 |
| 考试导航 | 底部 sticky 进度条 + FAB 唤起 sheet | 右侧 240px 固定"目录式"卡 |
| 表格 | Card 列表（mobile renderer） | 横向表格 |
| 字号（display-2xl） | 40px | 72px |
| 卡片 padding | p-5 | p-8 |

## 8. 动效

| 动效 | 时长 | easing | 触发 |
|---|---|---|---|
| 按钮 press 颜色翻转 | 80ms | ease-out | `:active` |
| 按钮 hover bg | 120ms | ease-out | `:hover` |
| 输入框 focus ring | 120ms | ease-out | `:focus-visible` |
| 页面 enter stagger | 子项 60ms 错开 | ease-out | 路由切换 / `data-stagger` |
| 倒计时 ≤ 5min 数字 pulse | 1000ms 一次 | ease-in-out | `useEffect` 监听 |
| Bottom sheet 滑入 | 240ms | cubic-bezier(0.16, 1, 0.3, 1) | 唤起 / 关闭 |
| Skeleton shimmer | 1500ms | linear | 数据加载 |

**禁用**：360° 旋转、splash 类全屏渐显、>300ms 列表入场、轮播 / marquee、题目切换翻页。

### 键盘交互

- 考试作答：← / → 切换题目，1-9 / A-D 直接选答案
- 弹层：ESC 关闭，Tab 焦点环
- 侧栏 / Sheet：方向键移动焦点

### 可访问性

- 所有文字与背景对比度 ≥ 4.5:1（正文）/ 3:1（大字号）
- focus-visible ring 始终 2px `#111` + 2px 偏移
- 图标按钮必有 `aria-label`
- 倒计时 ≤ 5min 时额外加 `aria-live="polite"` 提示
- 暗色 footer 内文字 `#a1a1aa` 在 `#0a0a0a` 上对比度 7.4:1

## 9. 落地结构

### 9.1 目录改造

```
frontend/src/
├── app/
│   └── router.tsx                          # 不变
├── components/
│   ├── ui/                                 # shadcn 风格基础组件，全部重做
│   │   ├── button.tsx                      # 重写：pill 形态 + Manrope 600
│   │   ├── card.tsx                        # 重写：chapter 三行 header
│   │   ├── input.tsx                       # 重写：8px 圆角、focus ink ring
│   │   ├── label.tsx                       # 重写：中英双语 + tracking
│   │   ├── badge.tsx                       # 重写：印章感（4px 圆角 + 全大写）
│   │   ├── table.tsx                       # 重写：无斑马 + mobile card renderer
│   │   ├── dialog.tsx                      # 新增（基于 Radix）
│   │   ├── sheet.tsx                       # 新增（基于 Radix Dialog 变体）
│   │   ├── skeleton.tsx                    # 新增
│   │   └── index.ts                        # barrel export
│   ├── layout/
│   │   ├── CandidateLayout.tsx             # 重写：wordmark + Z 圈 + 移动端汉堡
│   │   ├── AdminLayout.tsx                 # 重写：黑色侧栏 + 移动端 sheet
│   │   ├── TopNav.tsx                      # 新增（从 CandidateLayout 抽出）
│   │   ├── AdminSideRail.tsx               # 新增（从 AdminLayout 抽出）
│   │   └── Footer.tsx                      # 新增（#0a0a0a + #a1a1aa）
│   ├── exam/
│   │   ├── OptionCard.tsx                  # 新增
│   │   ├── ProgressCapsule.tsx             # 新增
│   │   ├── Timer.tsx                       # 新增（含 ≤5min pulse 逻辑）
│   │   ├── ExamFocusMode.tsx               # 新增：单题全屏容器
│   │   └── ExamNavigator.tsx               # 重写 QuestionNavigator
│   ├── admin/
│   │   ├── ReportPage.tsx                  # 重写：chapter 头 + 印章感 badge
│   │   ├── SimpleDataTable.tsx             # 重写：含 mobile card renderer
│   │   └── MetricCard.tsx                  # 新增：仪表盘 4 指标卡
│   ├── editorial/
│   │   ├── ChapterNumber.tsx               # 新增：italic + 全大写 + tracking
│   │   ├── NamePlate.tsx                   # 新增：头像 + 姓名 + 副标
│   │   ├── StatusPill.tsx                  # 新增：LIVE / DRAFT / ENDED
│   │   ├── Wordmark.tsx                    # 新增：Z 圈 + 知试 + 可选副标
│   │   └── EmptyState.tsx                  # 新增：chapter + italic + CTA
│   └── QuestionNavigator.tsx               # 删除（迁入 components/exam/）
├── lib/
│   ├── utils.ts                            # 不变
│   ├── candidateSession.ts                 # 不变
│   ├── questionNavigation.ts               # 不变
│   └── design-tokens.ts                    # 新增：所有 token 集中处（types/常量）
├── pages/                                  # 全部重写
│   ├── LoginPage.tsx
│   ├── ExamListPage.tsx
│   ├── ExamStartPage.tsx
│   ├── ExamTakingPage.tsx
│   ├── ExamResultPage.tsx
│   ├── PracticePage.tsx
│   ├── RankingPage.tsx
│   └── admin/                              # 全部 10 个 admin 页重写
├── api/                                    # 全部不变
├── types/                                  # 全部不变
├── index.css                               # 重写：CSS 变量 + 字体 + 全局样式
└── main.tsx                                # 不变
```

### 9.2 Token 落点

`index.css` 用 CSS 变量定义所有 token；`tailwind.config.ts` 把这些变量映射成 utility class。

```css
/* index.css 关键节选 */
:root {
  --canvas: #ffffff;
  --canvas-warm: #fafaf7;
  --ink: #111111;
  --ink-soft: #2a2a2a;
  --body: #374151;
  --muted: #6b7280;
  --hairline: #e5e7eb;
  --hairline-soft: #f3f4f6;
  --surface-card: #f5f3ee;
  --footer: #0a0a0a;
  --footer-soft: #a1a1aa;
  --success: #166534;
  --warning: #b45309;
  --error: #b91c1c;
  --radius-pill: 9999px;
  --radius-lg: 16px;
  --radius-md: 8px;
  --radius-sm: 4px;
  --shadow-card: 0 1px 2px rgba(17,17,17,.04), 0 4px 12px rgba(17,17,17,.04);
  --shadow-pop: 0 8px 24px rgba(17,17,17,.08);
  --shadow-elevate: 0 16px 40px rgba(17,17,17,.10);
  --font-display: "Manrope", "Inter", system-ui, sans-serif;
  --font-body: "Inter", system-ui, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, monospace;
}
```

```ts
// tailwind.config.ts 关键节选
theme: {
  extend: {
    colors: {
      canvas: "var(--canvas)",
      "canvas-warm": "var(--canvas-warm)",
      ink: "var(--ink)",
      body: "var(--body)",
      muted: "var(--muted)",
      hairline: "var(--hairline)",
      "surface-card": "var(--surface-card)",
      footer: "var(--footer)",
      "footer-soft": "var(--footer-soft)",
      success: "var(--success)",
      warning: "var(--warning)",
      error: "var(--error)",
    },
    borderRadius: {
      pill: "var(--radius-pill)",
      lg: "var(--radius-lg)",
      md: "var(--radius-md)",
      sm: "var(--radius-sm)",
    },
    fontFamily: {
      display: ["var(--font-display)"],
      body: ["var(--font-body)"],
      mono: ["var(--font-mono)"],
    },
    boxShadow: {
      card: "var(--shadow-card)",
      pop: "var(--shadow-pop)",
    },
  },
},
```

`bg-primary` / `text-foreground` 等 shadcn 已有 HSL 变量（`--primary: 176 60% 28%` 茶色）**整段移除**——这套设计不用 HSL。

### 9.3 字体加载

在 `index.html` 加 Google Fonts 链接：

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Manrope:ital,wght@0,400;0,500;0,600;0,700;1,600&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
```

## 10. 实现顺序

| Phase | 内容 | 工作量 |
|---|---|---|
| 1 | `index.css` + `tailwind.config.ts` + 字体引入 | 1 天 |
| 2 | 基础组件（Button / Card / Input / Label / Badge / Table / Dialog / Sheet / Skeleton） | 2 天 |
| 3 | 学术感专用组件（ChapterNumber / NamePlate / Wordmark / StatusPill / EmptyState） | 0.5 天 |
| 4 | 布局（TopNav / CandidateLayout / AdminSideRail / AdminLayout / Footer） | 1 天 |
| 5 | P0 页面（Login / ExamTaking Focus Mode / ExamResult / Practice） | 2 天 |
| 6 | P1 / P2 页面（考试列表 / 说明 / 排名 / 仪表盘 / 编辑 / 导入 / 4 报表） | 1.5 天 |
| 7 | 状态与精修（空 / 错 / 加载 / 动效 / 键盘 / 可访问性 / lint+format+typecheck） | 1 天 |
| **合计** | | **9 天** |

## 11. 不在范围

- 暗色模式
- 国际化 i18n（保持中文）
- 答题实时同步（保留现有"暂存"模型）
- 简历 / 题库搜索
- 第三方登录、SSO
- 富文本编辑器
- 通知中心
- 后端 API 变更

## 12. 验收

- 桌面 ≥1024px 与手机 <768px 两端的所有 P0/P1 页面在浏览器中目视与本 spec 第 6 节描述一致
- `npm run build` 成功（`tsc --noEmit` + Vite build）
- `npm run lint` 0 warning
- `npm run format:check` 0 diff
- 关键页面（登录 / 考试作答 / 结果 / 仪表盘 / 报表）的 TypeScript 类型零 `any`
- 倒计时逻辑与现有 `ExamTakingPage` 行为兼容：基于 `attempt.started_at` 计算、不被暂存暂停、到时自动交卷
- 题目快照语义未破坏：所有题目 / 选项 / 答案 / 解析 / 分值 / 顺序来自 `attempt.questions[].*_snapshot`
- 排名计算与后端 `/exams/:id/ranking` 接口一致
- 暂存（saveAttemptAnswers）与提交（submitAttempt）请求参数、返回结构与现状一致
- 所有图标按钮带 `aria-label`
- 颜色对比度满足 WCAG AA

## 13. 风险与开放问题

1. **字体加载抖动**：Manrope / Inter / JetBrains Mono 同时引入可能拖慢首屏。缓解：Google Fonts URL 自带 `display=swap`（FOIT → FOUT 替换），关键 h1 在 `<link>` 用 `rel="preload" as="font"` 提前加载。
2. **手机端 Bottom sheet 与 iOS Safari 滑动冲突**：sheet 容器用 `overscroll-contain` 限制滚动链；唤起时用 `document.body.style.overflow = 'hidden'` 锁住 body scroll（关闭时恢复）。
3. **考试作答页键盘快捷键与浏览器冲突**：← / → 在 input/textarea/select 聚焦时禁用；切换到题目视图时启用。监听 `e.target` 标签判断。
4. **数据快照兼容性**：不动后端，必须保证新 UI 渲染 `attempt.questions[].*_snapshot` 字段不变；如果某些字段缺失需要 EmptyState。
5. **TanStack Table mobile renderer 与 column 顺序**：需要在 `SimpleDataTable` 内置"desktop / mobile" 两种渲染分支，而不是改每张报表的 column 定义。每张报表的 column 需额外声明 `meta.mobilePriority` 决定手机端显示哪些字段。
