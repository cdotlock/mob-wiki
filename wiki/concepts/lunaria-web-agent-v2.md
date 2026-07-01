---
title: Lunaria Web — Agent v2（渐进式技能加载 + 双模式 + AI 写提示词）
description: lunaria-web 写作 Agent 重构（2026-07-01）：技能目录 + read_skill 按需加载、create/adapt 双模式、AI 只帮写生图 prompt；gateway-free 审计验到占 IDE 质量 85%（过 80% 线）。
updated: 2026-07-01
---

# Lunaria Web — Agent v2（渐进式技能加载 + 双模式 + AI 写提示词）

> 决策记录 2026-07-01。Lunaria Web（网页端 VN 剧本创作台，`AugustZAD/lunaria-web`）的写作 Agent 重构。
> 仓库内权威源：`AGENT.md`（架构）+ `docs/design/2026-06-30-lunaria-web-v2-design.md` §7.G/§6.4。本页是团队 KB 的决策快照 + 复用要点。

## 背景 / 为什么

网页端要让一个被严格限权的「剧本作者」Agent 既能熟练写 LunaScript(.ls)、又能改编小说，且质量要接近 IDE。约束：只用 `@earendil-works/pi-agent-core`；LLM 走现有网关（用户登录 token）；**没有任何生成图/音/视频的工具**；省 token。

## 核心决策

1. **渐进式技能加载（progressive disclosure）**——不再把技能正文全盘塞进系统提示。系统提示只放技能**目录**（`name — 一句话描述`），Agent 判定描述匹配当前任务时，用 `read_skill(name)` 工具现拉正文。这正是 IDE `adaptation/AGENTS.md §6`「描述匹配当前工作再读正文」的做法，也对齐 [[concepts/four-layer-philosophy]] 的 SKILL 层。磁盘布局 `.claude/skills/{shared,create,adapt}/<name>/SKILL.md`，`loadModeSkills = shared + <mode>`。
2. **两个模式**：`create`（`/agent`，原创一集）与 `adapt`（`/adapt`，小说章→一集）。每个模式只看得到自己的技能目录，系统提示按模式区分。
3. **技能是 web 化 fork 的 IDE 技能**：shared 有 lunascript / character-architect / episode-writer / entity-planner，create 有 asset-prompt-generator，adapt 有 novel-evaluator。去掉 IDE 的 sub-agent / python 校验 / MCP / GO-NO-GO / entity-normalizer 等重机制（参 [[entities/lunaverse-ide]]、[[concepts/ls-format]]）。
4. **AI 帮写生图提示词**：独立的 `POST /assets/suggest-prompt`，一次非 agentic 的 `llm.chat`（无工具），用 asset-prompt-generator 技能作系统指引，只**产出 prompt 交用户确认**——模型永不触发生成，生成始终是用户在素材页对确认过的 prompt 的显式点击。
5. **质量护栏**：`read_skill` 软门（首次未读技能就写会被弹回一次，读后放行，不死锁）；写完对照「创作品味」自审一遍；`compile_scene` 是语法唯一裁判；步数预算按模式（create 20 / adapt 28）。

## 质量验证方法（可复用）

用**不烧网关**的多 Agent workflow 静态审计：5 个维度（语法正确性 / 技能保真度 / 机制健全度 / 改编流水线保真度 / 生图提示词）各读代码+技能对照 IDE 打分，再综合成「占 IDE 质量的百分比」对 80% 标尺判定。不靠真跑 Agent（省网关 token、不落测试账号密码）。首轮 **72%**（知识层强、交付层弱）→ 修一批「便宜的接线级」缺口后复审 **85%，过线**（语法 96 / 技能保真 91 / 生图 85 / 机制 78 / 改编 76）。

## 已知遗留（scoped 未来工作）

- 改编模式仍是「一章→一集」，无持久化 plan/entities.json 注入（design §6.3 的分步 HITL 是未来工作）——跨集连续性靠 `read_scene` 上一集，比结构化实体表弱。
- 自审是同模型同上下文的轻量检查，不是 IDE 那种独立评分 reviewer 门。
- `read_skill` 软门只保证「读了某个技能」，不校验读的是不是最相关那个。
