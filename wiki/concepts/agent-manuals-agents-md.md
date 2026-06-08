---
title: Agent 手册机制 — per-agent AGENTS.md（codex 项目规则）
updated: 2026-06-08
---

# Agent 手册机制：per-agent `AGENTS.md`

Moonshort IDE 的 Production Workshop 每个 agent（adaptation / asset / audio / minigame）都带一份 `agents/<id>/AGENTS.md` —— 它就是该 agent 的**操作手册**，以 markdown 写，等同 codex 的项目规则（project rules），每次该 agent 跑 codex 时作为 standing instructions 加载。

## 为什么

agent 之前在对话指令里只有一句 `You are the X agent` —— 没有使命、边界、流程。模型手握一堆 skill 却不知道自己是谁、该按什么顺序干、哪些不归自己，于是乱规划、越界（典型：Novel Adaptation 让它写 MSS，它一路规划到素材生成）、甚至假装 / 漏报 skill。手册把这些一次写清。

## 手册结构（6 段）

1. **身份与边界** — 使命 + 你交付什么 + 不归你管（点名移交到正确 agent）
2. **完整流水线** — 本 agent 的阶段顺序 + 每步 gate
3. **每阶段 I/O 契约** — 读哪个上游、写什么、落哪
4. **跨 agent 交接** — 上游谁先跑、下游谁消费（IDE 把源头一条 n2m 流水线拆成 4 个用户手动选的 agent 后，这条最容易漏，也最关键）
5. **方法论 / 质量基线** — 决定 HOW 做得好，不只是 WHAT
6. **依赖 / 参考**

## 怎么加载（代码）

`packages/mss-workshop/src/codex-home.ts`：

- `loadAgentsMd(agentDir, agent)` 优先读 `<agentDir>/AGENTS.md`；没有就退回 `agentsMd(agent)` 生成的极简版（只有标题 + description + “skills 在目录里自己读”）。
- `stageCodexHome` / `stageStableCodexHome` 把结果写进 `$CODEX_HOME/AGENTS.md`（和 `skills/` 一起 staged），codex 原生读取为 standing instructions。对话式 run 用稳定 home `项目根/.moonshort/codex-home/<agentId>/`，每轮 re-stage。
- 若书项目根目录另有 `AGENTS.md`（用户为这本书写的偏好），codex 会叠加在上面 —— 这就是 per-book 的用户引导层（产品定边界靠 agent 手册，用户定偏好靠书项目的 AGENTS.md）。

## 关键决策（2026-06-08）

- **手册 = 单一来源**。早期试过结构化的 manifest `charter` 字段 + per-turn 注入（`renderCharter`），已**退役**并入 `AGENTS.md`（commit `refactor(workshop): retire structured charter in favour of AGENTS.md manuals`）。改 agent 角色 / 流程只改那份 `.md`，markdown 热补即可，不必动代码。
- 4 份手册是对照**源头项目 novels-to-moonscript**（canonical pipeline `docs/pipeline-stage-numbering.md` + `SKILLS-GUIDE.md` + 各 `SKILL.md`）加上 IDE 真实 skill 集，用多 agent workflow **对抗式核验**过的（两条视角：事实正确性 + 能力退化风险）。核出的真问题样例：asset 把已退役的批控制器（asset-prompt-generator / asset-renderer / asset-reviewer）当现役报出；audio 的 `music-spec` 其实是只回显输入的占位 skill；minigame 的 Deep 三层定制核心能力差点被漏写（会严重削弱它）；封面归属 adaptation（书级身份封面）vs asset（集封面 / 宣传）重叠；adaptation 交付应是 `ep_{N}_final.mss` 而非 `.md`。

## 怎么改 / 加新 agent

- **改手册**：直接编辑 `agents/<id>/AGENTS.md`（纯 markdown）。host 端无需重建（每轮从 agentDir 重新 staged）；热补到已装 .app 时拷 `…/extensions/moonshort-mss-workshop/agents/<id>/AGENTS.md`。
- **加新 agent**：在 `agents/<id>/` 放 `agent.json` + `skills/` + 一份 `AGENTS.md`，`loadAgentsMd` 会自动捡起；没写则退回极简版（不报错）。

相关：[[entities/moonshort-ide]] · [[concepts/assetctl-skills-sync-and-staging]]（skill 进 `CODEX_HOME` 的同一条 staging 链）· [[concepts/codex-runtime-and-verification-layers]]（codex 怎么起 + auth 怎么传）
