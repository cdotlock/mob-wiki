---
title: Lunaria Web — Agent v2（渐进式技能加载 + 双模式 + 持久化大纲 + AI 写提示词）
description: lunaria-web 写作 Agent 重构（2026-07-01/02）：技能目录 + read_skill 按需加载、create/adapt 双模式、持久化故事大纲 + 实体表注入、回合末自评打分、AI 只帮写生图 prompt；gateway-free 审计验到占 IDE 质量 87%（过 80% 线）。
updated: 2026-07-02
---

# Lunaria Web — Agent v2（渐进式技能加载 + 双模式 + 持久化大纲 + AI 写提示词）

> 决策记录 2026-07-01/02。Lunaria Web（网页端 VN 剧本创作台，`AugustZAD/lunaria-web`）的写作 Agent 重构。
> 仓库内权威源：`AGENT.md`（架构，§2.7 持久化大纲 / §2.8 自评）+ `docs/design/2026-06-30-lunaria-web-v2-design.md` §7.G/§6.4。本页是团队 KB 的决策快照 + 复用要点。

## 背景 / 为什么

网页端要让一个被严格限权的「剧本作者」Agent 既能熟练写 LunaScript(.ls)、又能改编小说，且质量要接近 IDE。约束：只用 `@earendil-works/pi-agent-core`；LLM 走现有网关（用户登录 token）；**没有任何生成图/音/视频的工具**；省 token。

## 核心决策

1. **渐进式技能加载（progressive disclosure）**——不再把技能正文全盘塞进系统提示。系统提示只放技能**目录**（`name — 一句话描述`），Agent 判定描述匹配当前任务时，用 `read_skill(name)` 工具现拉正文。这正是 IDE `adaptation/AGENTS.md §6`「描述匹配当前工作再读正文」的做法，也对齐 [[concepts/four-layer-philosophy]] 的 SKILL 层。磁盘布局 `.claude/skills/{shared,create,adapt}/<name>/SKILL.md`，`loadModeSkills = shared + <mode>`。
2. **两个模式**：`create`（`/agent`，原创一集）与 `adapt`（`/adapt`，小说章→一集）。每个模式只看得到自己的技能目录，系统提示按模式区分。
3. **技能是 web 化 fork 的 IDE 技能**：shared 有 lunascript / character-architect / episode-writer / entity-planner，create 有 asset-prompt-generator，adapt 有 novel-evaluator。去掉 IDE 的 sub-agent / python 校验 / MCP / GO-NO-GO / entity-normalizer 等重机制（参 [[entities/lunaverse-ide]]、[[concepts/ls-format]]）。
4. **持久化故事大纲 + 实体表注入（`story-plan.ts`）**——跨集一致性的脊柱（owner 明确要求：不做会「效果太差」）。每项目一份 `<project>/plan.json`（`StoryPlan` = 前提 + 角色实体表 [id/name/role/trope/人设/外貌渲染契约/poses] + 地点 + 分集大纲 [segment/routes/beats/choices/affection/signals/hook]），把 IDE 拆散的 `characters.json` + Canonical Wardrobe 契约 + `00-structure-decision` 分集计划**融成一份**。`normalizePlan` 防御式归一（丢无 id 条目、限长限量），模型乱写也毁不了存储。**注入是服务端做的**：`streamAgent` 每回合起始 `readPlan`，非空就把 `formatPlanForContext(plan)` 作为 `<context label="story-plan">` 块喂进当轮 user 消息——不依赖 agent 记得调 `read_plan`。工具 `read_plan`/`write_plan` 在白名单内。
5. **AI 帮写生图提示词**：独立的 `POST /assets/suggest-prompt`，一次非 agentic 的 `llm.chat`（无工具），用 asset-prompt-generator 技能作系统指引，只**产出 prompt 交用户确认**——模型永不触发生成，生成始终是用户在素材页对确认过的 prompt 的显式点击。
6. **回合末自评打分（`report_quality` → `score` 事件）**：owner 决策——**不做独立评审 agent**，但收尾要有个分数反馈、用户自己手改。实现为**环内**自评：编译通过后 agent 调 `report_quality { score 0–100, strengths?, improvements? }`，经 `ctx.onQualityReport` 回调交 HTTP 层，在终结的 `done`/`error` 前补发 `score` SSE 事件；前端渲染一张分数分档配色的「AI 质量自评」卡。
7. **质量护栏**：`read_skill` 软门（首次未读技能就写会被弹回一次，读后放行，不死锁）；`compile_scene` 是语法唯一裁判；步数预算按模式（create 20 / adapt 32）。

## 质量验证方法（可复用）

用**不烧网关**的多 Agent workflow 静态审计：各维度读代码+技能对照 IDE 打分，综合成「占 IDE 质量的百分比」对 80% 标尺判定；每个分数再过一道对抗式 verify（重开文件核对证据，不信claim）。不靠真跑 Agent（省网关 token、不落测试账号密码）。轨迹：首轮 **72%**（知识层强、交付层弱）→ 接线级修复后 **85%** → 加持久化大纲 + 自评后复审 **87%**（语法 96 / 技能保真 91 / 生图 85 / 机制 **78→83** / 改编 **76→84**）。两个最弱维度正是被这次改动抬起来的。

## 已知遗留（scoped 未来工作）

- **最大的改编抬升杠杆**：`plan.json` 把 IDE 的结构化契约压成了自由文本——Canonical Wardrobe（每主角 4–7 行 id/text/when、逐字稳定、下游渲染唯一来源）塌成一个 `appearance` 字符串；`@signal 分配 / 成就 / CG / 传奇 gate` 等跨集状态账本没有 schema 字段，只能活在 `beats`/`signals[]` 的散文里。多套服装 + 跨集连续性因此仍靠模型自觉而非结构。下一步：把 wardrobe 行与 signal/gate 账本升成 `StoryPlan` 一等字段。
- 自审是同模型同上下文的自评，不是 IDE 那种独立评分 reviewer 门（刻意如此，分数交用户手改）。
- 预算护栏边界：`report_quality` 若恰好落在步数上限那一步，收尾轮会被判 harness error——分数现在 error 时也会补发，用户仍看得到。
- `read_skill` 软门只保证「读了某个技能」，不校验读的是不是最相关那个。
