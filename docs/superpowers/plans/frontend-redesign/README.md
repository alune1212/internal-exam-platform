---
title: 知试前端重构 — 实现计划
date: 2026-06-12
status: ready-for-execution
total-phases: 7
---

# 知试前端重构实现计划

> **For agentic workers:** 每个 phase 独立成文件。文件内自带 `> REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans` 头部。

**Goal:** 把内部考试平台前端按「知试 · 现代学术风」重做，对照 [`docs/superpowers/specs/2026-06-12-frontend-redesign-design.md`](../../specs/2026-06-12-frontend-redesign-design.md) 的 13 个章节。

**Architecture:** 7 个 phase 顺序执行。前一 phase 落地的 token / 组件 / 布局是后续 phase 的依赖。所有 phase 不修改后端、不改路由。

**Tech Stack:** React 19 / Tailwind 3.4 / Radix UI Slot+Dialog（新增）/ TanStack Query+Table / React Hook Form+Zod / lucide-react / Manrope+Inter+JetBrains Mono / Vitest+Testing Library（新增）

---

## Phase 索引

| # | 文件 | 任务数 | 关键产出 | 状态 |
|---|---|---|---|---|
| 1 | [phase-1-tokens-and-fonts.md](phase-1-tokens-and-fonts.md) | 5 | `index.css` CSS 变量 + `tailwind.config.ts` 映射 + Google Fonts 链接 + `lib/design-tokens.ts` | ✅ ready |
| 2 | [phase-2-ui-primitives.md](phase-2-ui-primitives.md) | 12 | 9 个 shadcn 风格基础组件全部重做（pill Button、米色 Card、新增 Dialog/Sheet/Skeleton） | ✅ ready |
| 3 | [phase-3-editorial-components.md](phase-3-editorial-components.md) | 7 | 5 个学术风专用组件（ChapterNumber / NamePlate / Wordmark / StatusPill / EmptyState） | ✅ ready |
| 4 | [phase-4-layout-and-navigation.md](phase-4-layout-and-navigation.md) | 8 | TopNav + AdminSideRail + Footer + 重写 CandidateLayout / AdminLayout + useMediaQuery | ✅ ready |
| 5 | [phase-5-p0-pages.md](phase-5-p0-pages.md) | 11 | 4 个 P0 页面（Login / ExamTaking Focus Mode / ExamResult / Practice）+ 5 个 exam 组件 | ✅ ready |
| 6 | [phase-6-p1-p2-pages.md](phase-6-p1-p2-pages.md) | 16 | 13 个 P1/P2 页面 + MetricCard / SimpleDataTable（mobile renderer） / ReportPage | ✅ ready |
| 7 | [phase-7-states-and-polish.md](phase-7-states-and-polish.md) | 12 | 共享空/错/加载态、键盘快捷键、可访问性、lint+format+typecheck+build 全绿 | ✅ ready |
| **合计** | | **71** | | |

---

## Phase 依赖图

```
Phase 1 (tokens + fonts)
  ├─→ Phase 2 (9 UI primitives)
  │     ├─→ Phase 3 (5 editorial)
  │     │     └─→ Phase 4 (TopNav / SideRail / Footer / Layouts)
  │     │           └─→ Phase 5 (4 P0 pages + 5 exam components)
  │     │                 └─→ Phase 6 (13 P1/P2 pages + 3 admin components)
  │     │                       └─→ Phase 7 (states / motion / a11y / verification)
  │     └─────────────────────────────┘
```

每个 phase 文件头部都明确写出"前置 phase"清单。

---

## Phase 间共享约定

### 新增依赖（仅一次，Phase 1 / Phase 2 引入）

| Phase | 依赖 | 用途 |
|---|---|---|
| 1 | `vitest@^1.6.0` `jsdom` `@testing-library/react` `@testing-library/jest-dom` | 测试运行器 + DOM 环境（项目当前零测试） |
| 2 | `@radix-ui/react-dialog` | Dialog / Sheet 弹层 |
| 2 | `tailwindcss-animate` | Radix 内置动画所需的 Tailwind 插件 |

`package.json` 由 Phase 1 和 Phase 2 各自任务里的 `npm install` 步骤处理。

### Token 引用约定

- CSS 类：`bg-ink` `bg-canvas-warm` `text-muted` `rounded-pill` `shadow-card` `font-display` `font-mono` 等
- 偶尔需要的原始值：从 `lib/design-tokens.ts` 导入（仅当确实不能写成 utility class 时，例如给 `style` prop 赋值）

### Commit 规范

- `<type>(<scope>): <中文描述>` 全部按 `frontend/DESIGN.md` 上方 CLAUDE.md 的格式
- type: `feat` / `fix` / `refactor` / `chore` / `test`
- scope: `frontend`（默认）/ `ui` / `editorial` / `layout` / `exam` / `admin` / `pages` / 组件名

### TDD 范围

- **强制 TDD**（先写失败测试再写实现）：tokens（type-shape）、Button variant、Card chapter header、Input focus、Badge variant、QuestionNavigator 状态、Timer pulse、useMediaQuery、OptionCard 选中态、ProgressCapsule 计算、MetricCard tone、SimpleDataTable mobile renderer
- **不做 TDD**（仅 visual smoke + commit）：纯 layout 组件（TopNav / SideRail / Footer / layouts / pages）—— 这些的"测试"是手动视觉验证 + 启动 dev server 看一眼

---

## 执行选项

整个计划写完保存到 `docs/superpowers/plans/frontend-redesign/`，共 7 个 phase 文件 + 1 个 README。两种执行方式：

**1. Subagent-Driven（推荐）** — 我对每个 phase 调度一个新的 subagent，按 phase 串行执行、phase 间 review。优点：单 phase 上下文干净，bug 不会跨 phase 累积。

**2. Inline Execution** — 在当前会话里用 executing-plans 串行执行，phase 间设检查点让你 review。优点：上下文不切换；缺点：长会话会接近 token 上限。

如果你打算自己实现，最直接的方式是按 phase 1 → 7 顺序打开对应文件，每完成一个 phase 的全部任务再进下一个。

---

## 完成后

- 全部 7 phase 落地后，运行 `git log --oneline` 应有 60+ commit
- `npm run build` / `npm run lint` / `npm run format:check` / `vitest` 全绿
- 桌面 ≥1024px 与手机 <768px 两端目视对照 spec section 6
- 最后调用 `superpowers:finishing-a-development-branch` 决定如何收尾（merge / PR / cleanup）
