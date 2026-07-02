---
title: Lunaria Web — Agent v2（渐进式技能加载 + 双模式 + 持久化大纲 + AI 写提示词）
description: lunaria-web 写作 Agent 重构（2026-07-01/02）：技能目录 + read_skill 按需加载、create/adapt 双模式、持久化故事大纲（结构化 Canonical Wardrobe 行 + @signal/CG/gate 跨集账本 + romanceStage + STORY-PLAN CONTRACT/planWarnings）+ 实体表注入、回合末自评打分、AI 只帮写生图 prompt、轮转多模型网关回退、邀请码用户注册；真实 AI create+adapt 跑测已验证（本地 + 线上），部署到 Railway。
updated: 2026-07-02
---

# Lunaria Web — Agent v2（渐进式技能加载 + 双模式 + 持久化大纲 + AI 写提示词）

> 决策记录 2026-07-01/02。Lunaria Web（网页端 VN 剧本创作台，`AugustZAD/lunaria-web`）的写作 Agent 重构。
> 仓库内权威源：`AGENT.md`（架构，§2.1 传输/回退 / §2.7 持久化大纲 / §2.8 自评）+ `docs/design/2026-06-30-lunaria-web-v2-design.md` §7.G/§6.4。本页是团队 KB 的决策快照 + 复用要点。

## 背景 / 为什么

网页端要让一个被严格限权的「剧本作者」Agent 既能熟练写 LunaScript(.ls)、又能改编小说，且质量要接近 IDE。约束：只用 `@earendil-works/pi-agent-core`；LLM 走现有网关（用户登录 token）；**没有任何生成图/音/视频的工具**；省 token。

## 核心决策

1. **渐进式技能加载（progressive disclosure）**——系统提示只放技能**目录**（`name — 一句话描述`），Agent 判定描述匹配当前任务时用 `read_skill(name)` 现拉正文。对齐 IDE `adaptation/AGENTS.md §6` 与 [[concepts/four-layer-philosophy]] 的 SKILL 层。磁盘 `.claude/skills/{shared,create,adapt}/<name>/SKILL.md`，`loadModeSkills = shared + <mode>`。
2. **两个模式**：`create`（`/agent`，原创一集）与 `adapt`（`/adapt`，小说章→一集），各只看自己的技能目录。
3. **技能是 web 化 fork 的 IDE 技能**：shared 有 lunascript / character-architect / episode-writer / entity-planner，create 有 asset-prompt-generator，adapt 有 novel-evaluator。去掉 IDE 的 sub-agent / python 校验 / MCP / GO-NO-GO / entity-normalizer 等重机制（参 [[entities/lunaverse-ide]]、[[concepts/ls-format]]）。
4. **持久化故事大纲 + 实体表注入（`story-plan.ts`）**——跨集一致性脊柱。每项目一份 `<project>/plan.json`（`StoryPlan` = 前提 + 角色实体表 + 地点 + 分集大纲 + 三本跨集账本），把 IDE 拆散的 `characters.json` + Canonical Wardrobe 契约 + `00-structure-decision` 融成一份。`normalizePlan` 防御归一。**注入是服务端做的**：`streamAgent` 每回合起始 `readPlan`，非空就把 `formatPlanForContext(plan)` 作为 `<context label="story-plan">` 喂进当轮消息——不依赖 agent 记得调 `read_plan`。
5. **AI 帮写生图提示词**：独立的 `POST /assets/suggest-prompt`，一次非 agentic `llm.chat`（无工具），只**产出 prompt 交用户确认**——模型永不触发生成。
6. **回合末自评打分（`report_quality` → `score` 事件）**：**不做独立评审 agent**，编译通过后 agent 调 `report_quality { score 0–100, strengths?, improvements? }`，经回调在终结 `done`/`error` 前补发 `score` SSE 事件；前端渲染分数分档配色的「AI 质量自评」卡。
7. **质量护栏**：`read_skill` 软门；`compile_scene` 是语法唯一裁判；步数预算按模式（create 20 / adapt 32）。

## 质量验证方法（可复用）

用**不烧网关**的多 Agent workflow 静态审计：各维度读代码+技能对照 IDE 打分，综合成「占 IDE 质量百分比」对 80% 标尺判定；每个分数再过一道对抗式 verify。轨迹：72%（知识强交付弱）→ 接线级修复 85% → 加持久化大纲+自评复审 **87%**（语法 96 / 技能保真 91 / 生图 85 / 机制 78→83 / 改编 76→84）。

## 结构化第三轮（2026-07-02，已完成）

owner：「改编保真度增强，结构化程度做好」。把 `plan.json` 从自由文本升成对齐 IDE 的结构化契约：
- **Canonical Wardrobe 行**：`appearance` 只放**体貌**（字节稳定的基底身份），服装拆进 `wardrobe[]` 行 `{ id, text（逐字出图）, when }`（主角 4–7 套）——立绘渲染唯一来源，换装不漂移。
- **三本跨集账本**升成一等字段：`signals[]`（@signal 总账，读→写纪律）、`cgs[]`（CG 规划）、`gates[]`（@gate/@ending 路由）。分集加 `romanceStage`（meet/falling/crisis/reconciliation）。
- 角色/地点 id slug 成小写 ASCII；`normalizeCg` 容忍中文 CG 标签；scene 存储 id 必须文件名安全（无 `:`/`/`），`@episode`/`@next` 正文保留寻址。
- 一次 26-agent 对抗式上线前审计，取真实项修、跳过越界项（在归一层强制字节稳定/reader 存在会丢有效数据、是技能层的活）。

## 真实 AI 跑测 + 上线前第四轮硬化（2026-07-02，已完成并验证）

owner 给了 `vito` 网关口令（**不落盘**），要求「进行真实测试，保证效果」。用真 token 驱动 `create` 与 `adapt` 两模式**真实 agentic 端到端跑通**（渐进读技能 → write_plan → write_scene → compile 通过 → report_quality ~78），本地 + **线上部署 URL 各验一遍**（线上持久化场景 API 编译 102 步 0 诊断）。真实跑测暴露 4 个真问题，全部修复并复验：

1. **网关间歇 500**：最小请求也 ~50% 失败（纯上游抖动，与 payload 无关）。→ 重试预算默认 2→**4** + 退避封顶 8s + `LUNARIA_LLM_MAX_RETRIES`/`_RETRY_BASE_MS` 环境变量。（**注：** 当时结论「gpt-5.5 整轮跑不通、默认切 opus-4-6」在第五轮被更正——见下，实为无 fallback 时的抽样噪声。）
2. **无参工具被填充参数打挂**：模型给零参工具塞 `{"_noargs":"unused"}`，`additionalProperties:false` 校验失败、白白浪费一轮。→ 无参工具 schema 改 `additionalProperties:true`。
3. **SSE 长静默掉线**：单轮 LLM 期间 SSE 无事件，叠加重试退避可静默数分钟 → undici body 超时 / 代理掐连接。→ `startSseHeartbeat` 每 15s 发 `: keepalive` 注释帧。
4. **大纲被写成骨架**（最关键）：模型写出高质量 `.ls` 却把 `plan.json` 持久化成骨架，schema 空有其表。→ **STORY-PLAN CONTRACT**（注入两模式系统提示）+ `write_plan` 结果的非阻塞 `planWarnings[]`。复验：两模式都正确落 role/appearance/trope/locations/CG/gate/romanceStage，adapt agent 看到 warnings 后二次 `write_plan` 补全。

## 稳定性 + 用户注册（2026-07-02，第五轮，已完成并验证）

owner：「让整体更稳定，不管网关那边出什么问题都稳一点；还是默认用 GPT 5.5 Free，查清它为什么跑不通；加注册用户功能并部署；代码合 main。」

**A. 查清 gpt-5.5 + 轮转多模型回退。** 用真 token 拿真实 tool-calling payload 复探网关两轮，得到**更正性结论**：
- `gpt-5.5:free` 与 `claude-opus-4-6:free` **可靠性完全相同**（各 ~50% 成功；请求一旦落地**两者都完美 tool-call**）。第四轮「opus 更稳、gpt-5.5 跑不通」是**抽样噪声 + 当时没有模型回退**——不是模型问题，也不是「不好用」。
- `gpt-5:free` 与 `claude-opus-4-8:free` **稳定死**（0/14，瞬时 ~550ms 500 = 网关未 provision；区别于慢速 ~1.5s 抖动 500）。
- 结论：**稳定性来自模型多样性，不是选「更好的模型」**。`GatewayLlmClient` 改成接受有序 `models` 回退链，每次瞬时重试**轮转到链上下一个模型**（`chain[attempt % len]`，共享重试预算）；任一模型 500 被另一个兜住，死主模型下一跳即被救；非瞬时错（4xx/鉴权）立即抛。默认链 **`gpt-5.5:free → claude-opus-4-6:free`**（主模型回到 owner 指定的 gpt-5.5），`LUNARIA_MODELS`（整链）/ `LUNARIA_MODEL`（仅主）覆盖。**实测：默认链（gpt-5.5 主）在 ~50% 网关 500 下完整跑通 create 一集（compile ok=true 69 步 0 诊断、self-score 78）**——gpt-5.5 单模型曾「跑不通」，轮转后稳定完成，本地 + 线上各验一遍。

**B. 邀请码用户注册（对齐 IDE `registerWithInvite`）。** 服务端 `GatewayAuth.register` → 网关 `POST /api/ide/register {username,password,inviteCode}` → 直接返 token（自动登录，与 login 同 token 形状）；新增**公开** `POST /api/auth/register` 路由 + `handleRegister`（三字段校验，**邀请码强制**=网关闭测门；网关逻辑失败如错误/已用邀请码、重复用户名以 HTTP 200 `code!==0` 回来 → 透传 400）。Web `client.register` + `LoginScreen` 加登录/注册模式切换（邀请码输入框、切换时清旧错误）。**线上验证**：无效邀请码 → 网关 "Invalid or already-used IDE invite code" 经代理透传（未创建账号）；部署包内含注册 UI。

**C. 对抗式复审。** 一个 4 维（可靠性 / 认证安全 / IDE 保真 / Web-UX）workflow 复审改动，每条 finding 独立 verify：12 条 findings、10 条被驳、**2 条确认**（均降为 low 并已修）——(1) `gatewayMessage` 漏了网关的嵌套 `{error:{message}}` 形状（IDE 的 responseMessage 处理，403/429/上游会用）→ 补齐，login/register 同受益；(2) 模式切换未清旧错误 → 切换时清。

server 单测 **264** / web **302** 全绿；构建 + 全仓 typecheck 通过。5 个原子提交合到 `origin/main`（ff），本地 `main` 同步。生图按 owner 要求不测。

## 上线（2026-07-02，首次生产部署 + 两轮硬化重部署）

部署到 **Railway**，服务 `lunaria-webide`（与 `playlunaverse.com` 官网服务隔离，挂 50GB volume 于 `/data`）。公网 URL 已上线并**真实验证**：guest E2E（含真 `lsc` 编译）+ 真 token 线上 AI create 跑通 + 注册路由线上透传网关邀请码错误 + 注册 UI 已随包发布。自定义域 `webide.playlunaverse.com` 已在 Railway 挂好，等 owner 在 Cloudflare 加一条 CNAME。构建踩坑：`@earendil-works/pi-ai` + `typebox` 被直接 import 但没声明，Docker 干净装 `--frozen-lockfile` 挂 —— 补成直接依赖修好。

## 已知遗留（scoped 未来工作）
- 自审是同模型同上下文的自评，不是独立评分 reviewer 门（刻意如此，分数交用户手改）。
- 预算护栏边界：`report_quality` 若落在步数上限那一步，收尾轮会被判 harness error——分数现在 error 时也会补发。
- `read_skill` 软门只保证「读了某个技能」，不校验读的是不是最相关那个。
- **大纲软缺口**：`wardrobe[]` 行 + `signals[]`/`locations[]` 账本登记，模型内联用了却不总回登（CONTRACT + warnings 已把 role/appearance/CG/gate 抬起来，这几项待进一步引导，不宜强逼模型为第一集臆造整套衣橱）。
- **网关可靠性**：免费网关间歇 500 是上游问题；已由轮转多模型回退 + 重试预算 + SSE 心跳缓解（gpt-5.5 主链实测稳定跑通）。若上游持续恶化，下一步可加更多在营模型进链或直连 provider。
- **注册限流**：`/api/auth/register` 公开无鉴权（与 login 同姿态），暂无应用层限流；开放公测前建议按 `docs/deploy-access-limits.md` 的 L0 白名单 + L1 配额收紧。
