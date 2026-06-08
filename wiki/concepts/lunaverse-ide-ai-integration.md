---
title: Lunaverse IDE — AI 集成架构(Cline)
tags: [lunaverse-ide, ai-integration, cline, tab-completion, architecture]
sources: []
created: 2026-05-18
updated: 2026-05-18
---

Lunaverse IDE(VS Code 1.119 薄壳 fork)内的 AI 能力。最终形态:**两个表面** —— Tab 预测补全 + Lunaverse Agent。本页记录架构决策,尤其"为什么用 Cline 而不是 VS Code 原生 chat"。

源设计文档:lunaverse-ide 仓库 `docs/superpowers/specs/2026-05-18-ai-integration-ux-design.md`;任务账本 `plan.md` 的 "AI 集成体验 — Topic A" 段。

## 背景与关键发现

原设计把三个 AI 表面(Cmd+I 行内改写、Tab 补全、Agent)都架在 **VS Code 原生 chat** 上(原生 inline chat widget、chat participant、chat-editing)。Phase 0 可行性验证实测发现:

> VS Code 1.119 的原生 chat —— 面板与 inline 两者 —— 被 `product.json#defaultChatAgent` **硬绑定到 GitHub Copilot**。两道闸:① `defaultChatAgent` 指向的扩展是否安装(改 `product.json` 可绕过);② 登录 + Copilot 授权检查 —— 这道闸在 VS Code 核心代码里、与 GitHub 强耦合,改 `product.json` **绕不过**。

**结论:对一个不接 Copilot 的 fork,原生 chat 路线不可行**,除非改 VS Code 核心源码。这条发现适用于任何想复用 VS Code 原生 chat 的非-Copilot fork。

## 重定方案

- **Agent 表面 → 改用 Cline。** Cline 是开源 AI 编程 Agent(Apache-2.0)。它用自己的 webview 侧边栏,完全不碰 VS Code 原生 chat API,因此天然绕过 Copilot 闸。
- **Cmd+I 行内改写 → 取消。** 原生 inline chat 同样被闸;自建一整套行内 diff 体验性价比低。
- **Tab 补全 → 保留、自建。** 走稳定、无闸的 `InlineCompletionItemProvider`,与 chat 闸无关。

## 最终架构

| 表面 | 形态 | 引擎 | 自建部分 |
|---|---|---|---|
| Tab 预测补全 | `ls` 语言的原生幽灵文本 + Tab 接受 | DeepSeek,经 `agent-adapter` 的 `ChatBackend` 单轮 | `ls-workbench` 的 `inline-completion.ts`:防抖、上下文裁剪、取消、设置开关 |
| Lunaverse Agent | Cline 的 webview 侧边栏,rebrand 成「Lunaverse Agent」+ 火箭 | Cline 自带 Agent 循环,provider 配 DeepSeek | 把 Cline 打包进 fork、配 DeepSeek、注入 `.ls` 领域指令 |

## Cline 集成要点

- **版本:** Cline 3.83.0(`saoudrizwan.claude-dev`,Apache-2.0,`engines.vscode ^1.84.0`,兼容 fork 的 1.119.1)。
- **打包:** 预编译 VSIX vendored 进 `fork/vendor-extensions/`;`fork/build.mjs` 的 `bundleClineExtension()` 解压 + 应用 manifest rebrand + 拷进 `extensions/`,VS Code 构建当 built-in 扩展收。不进 `LUNAVERSE_EXTENSIONS` 数组(那是源码包循环)。
- **rebrand(v1):** 只做 manifest 级 —— `displayName` 与活动栏容器改「Lunaverse Agent」+ 火箭图标。webview 内部 UI 仍显示 "Cline";深度 rebrand 需 fork Cline 源码,延后。
- **DeepSeek 配置:** Cline 不贡献 VS Code 设置项,provider 配置存它自己的 `globalState`/`secrets`(按扩展隔离,外部扩展无法跨扩展预写),且 Cline 3.83.0 无环境变量回落。故 v1 为**一次性 UI 设置**(用户首次在面板里选 DeepSeek、填一次 key);零配置注入需 fork Cline 源码,延后。`ls-workbench` 激活时弹一次引导通知。
- **`.ls` 领域指令:** `ls-workbench` 激活时写 `~/Documents/Cline/Rules/ls-domain.md`(Cline 的全局规则目录),给 Agent 注入 `.ls` 编剧领域上下文。
- **遥测:** fork 的 `product.overrides.json` 默认 `telemetry.telemetryLevel: off`,Cline 的 PostHog 遥测随之关闭。

## `.ls` 文件范围

原设计要 Agent 硬性只碰 `.ls`(影子目录 diff 强制)。Cline 是通用 Agent,改为**软引导** —— 经 `.ls` 领域指令导向剧本工作,安全性由 Cline 自带的逐条编辑审批兜底。硬性文件类型限制需 fork Cline 源码。

## 备选:fork Cline 源码

深度 rebrand(webview 内部)、零配置 key、更强控制都需把 Cline 源码 vendored 进仓库、打补丁、自建 VSIX。v1 取预编译 VSIX 路线(快、低维护、可逆),源码 fork 留作未来增强。

## 状态

Phase 0–4 完成并验证(`pnpm lint`/`typecheck`/`build`/`test` 全绿,132/132)。Phase 5(`fork/build.mjs` 全量打包 + CDP 端到端验收)待用户明确放行后执行。

相关:[[concepts/ls-format]] · [[entities/lunascripts]]
