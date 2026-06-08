---
title: Render-Time Silent Drop 失败类（VN Pipeline v4.1-v4.11 同构族）
updated: 2026-04-22
tags:
  - vn-pipeline
  - failure-pattern
  - branch-architect
  - episode-writer
  - no-rules
source_specs:
  - /Users/august/MobAI/norules-vn/docs/superpowers/specs/2026-04-21-flavor-choice-gate-design.md
  - /Users/august/MobAI/norules-vn/docs/superpowers/specs/2026-04-21-first-contact-seed-choice-design.md
  - /Users/august/MobAI/norules-vn/docs/superpowers/specs/2026-04-22-route-commitment-choice-design.md
  - /Users/august/MobAI/norules-vn/docs/superpowers/specs/2026-04-22-choice-variant-weight-gate-design.md
  - /Users/august/MobAI/norules-vn/docs/superpowers/specs/2026-04-22-character-first-appearance-intro-design.md
  - /Users/august/MobAI/norules-vn/docs/superpowers/specs/2026-04-22-scene-continuity-gate-design.md
  - /Users/august/MobAI/norules-vn/docs/superpowers/specs/2026-04-22-scene-transition-gate-design.md
  - /Users/august/MobAI/norules-vn/docs/superpowers/specs/2026-04-22-speaker-tier-floor-gate-design.md
  - /Users/august/MobAI/norules-vn/docs/superpowers/specs/2026-04-22-fake-delta-prose-gate-design.md
  - /Users/august/MobAI/norules-vn/skills/episode-writer/references/conditional-insert-signal-strength.md
  - /Users/august/MobAI/norules-vn/skills/episode-writer/references/outline-coverage-gate.md
  - /Users/august/MobAI/norules-vn/skills/episode-writer/references/route-commitment-choice.md
  - /Users/august/MobAI/norules-vn/skills/episode-writer/references/choice-weight-gate.md
  - /Users/august/MobAI/norules-vn/skills/episode-writer/references/character-first-appearance-gate.md
  - /Users/august/MobAI/norules-vn/skills/episode-writer/references/scene-continuity-gate.md
  - /Users/august/MobAI/norules-vn/skills/episode-writer/references/scene-transition-gate.md
  - /Users/august/MobAI/norules-vn/skills/episode-writer/references/fake-delta-prose-gate.md
---

# Render-Time Silent Drop 失败类

> **一句话定义**：pipeline schema 正确 + render 阶段静默收敛 / 丢规则 = 玩家感知为 0。
>
> **处理模式**：每次出现都沉淀为**四件套**（spec + case-study reference + verify 脚本或 checklist + SKILL.md step 0-N gate）。

这是 no-rules VN 管线上反复出现的一类 bug。schema 层（partition / branch taxonomy / merge-map）看起来完美，但在 outline writing 或 demo rendering 阶段，某条隐性规则被静默违反，玩家端感受不到设计意图。自评时由"写 outline 的同一 agent"执行，它读自己写的 outline 时假设 header 声称的内容真的被覆盖，读自己写的 CHOICE 块时假设 render 类型合适——不会去读 vault 原文 / branch frontmatter 做机械比对。

## 同构族谱（2026-04-20 ~ 2026-04-22，共 11 个 isomorph）

| 次序 | 时间 | 症状 | 失败位 | 沉淀物 |
|------|------|------|--------|--------|
| **v4.1** | 04-20 | partition 列 X + Y，outline header 声称覆盖，body 只写 X；自评 9.5 却实际丢 Y | outline header-vs-body 完整性 | `verify-outline-coverage.py` + `outline-coverage-gate.md` |
| **v4.2** | 04-21 AM | 9 个 flavor 分支被错当可点击 CHOICE 渲染，玩家："开头全是选择但像没选过" | flavor taxonomy 语义丢失 | `verify-flavor-choice-gate.py` + `flavor-choice-gate.md` + 3-测试 |
| **v4.3** | 04-21 noon | merge-map 列 payoff 但下游渲染为 stage-meta (T1) 或完全缺失 (T0)；玩家："选择没感觉到被记住" | 信号强度收敛 | BG10 + `conditional-insert-signal-strength.md` + T0-T4 分级 |
| **v4.4** | 04-21 PM | v4.2 规则对首次接触位置用力过猛，4 处开场 attitude CHOICE 被塌回 canonical；玩家："从来没对 LI 表达过 attitude" | 首次接触语义被一刀切（first-contact agency 丢失） | `flavor_subtype: seed` + `seed_evidence` frontmatter 合约 + verify 扩展 |
| **v4.5** | 04-22 | EP4 Hook 多 gate 同时满足时固定优先级替玩家选路线；玩家："既然都 ENTRY MET 了，剧情会怎么走呢" | 终点承诺语义被固定优先级覆盖（last-contact agency 丢失）| `route-commitment-choice.md` + BG12 (route-commitment-gate) + commitment CHOICE schema + Step 0-d checklist |
| **v4.6** | 04-22 PM | 21 branch 的 63 variant body 普遍萎缩到 3-4 行对白；玩家："选完等于没选"，CHOICE 3 变体 B "speechless" 设 Mauricio route 入口必需 flag 但当下只 3 行戏剧 5-8 秒屏读 | 变体当下戏剧密度静默收敛（drama-density agency 丢失）| `choice-weight-gate.md` + `verify_choice_weight_gate.py` + `weight_tier` / `weight_evidence` frontmatter 合约 + 三档饱和阈值 + Step 0-f gate |
| **v4.7** | 04-22 early PM | demo 里 Josie / Jacinda / JT / Mamá / Papá 等人名出现玩家不认识 | 作者 prose 层漏 render bible 数据（data-silence 子家族）| `character-first-appearance-gate.md` + `verify_character_first_appearance.py` (v1.0→v1.2 三轮加固 forward+coverage 双扫描) + intro-registry schema + Step 0-e checklist |
| **v4.8** | 04-22 evening | CHOICE option 的 `consequence` 字段塌缩成 `"Mark +2 · Easton 不爽 +2"` 纯 flag 速记，或跨时空跳切无过渡锚 | CHOICE 选后承接（intra-option consequence 的戏剧合约）| `scene-continuity-gate.md` + `verify_scene_continuity.py` + 四段锚（玩家回应 / 角色反应 / 场景过渡 / 情感锚+tag）≥ 3/4 机械验证 + Step 0-g gate |
| **v4.9** | 04-22 late | EP1 Hook 开头 "球赛结束，人群散去" 但 ep 内无球赛 setup；inter-scene 跨时空跳切无桥接、POV 悄切换无 `POV 切换:` 标记 | scene-to-scene 衔接（phantom event / unbridged time-space jump / unmarked POV switch）| `scene-transition-gate.md` + `verify_scene_transition.py` + 四查（temporal bridge / spatial bridge / phantom event / POV marker）机械验证 + Step 0-h gate |
| **v4.10** | 04-22 night | VIKKI 在 Scene 3.4 作为唯一 speaker 传递剧情关键信息（Samuel 发疯+找 Malia）但 registry 标 T4 walk-on，v1.2 gate 发 IDENTITY-MISSED WARN 被作者忽略；Owen 同类（king-miller gossip 传播者） | **严重度校准错误**（gate 检测到但 tier 分类过低 → severity 降 WARN → 作者忽略）| `character-first-appearance-gate.md` v1.3 (speaker-tier-floor 第三扫描) + `verify_character_first_appearance.py` v1.3 + SPEAKER_TIER_FLOOR=T3 常量 + TIER-TOO-LOW-FOR-SPEAKER BLOCK 码 + Step 0-e 扩展 checklist |
| **v4.11** | 04-22 night | outline-viewer-v4.html `ep3_c4` CHOICE consequence 尾部挂 `— Mark -1 · Easton +1 · Mauricio 情绪暗流 +2` 看似 gameplay HUD 速记，但项目无对应 counter flag；玩家："以为在追 Mark 关系分，实际什么都没写" | **authoring-intent 误渲染**（作者 editorial 散文被误抄成玩家可见 UI data）| `fake-delta-prose-gate.md` + `verify_fake_delta_prose.py` + `CHAR_NAMES` 白名单正则 + `FAKE-DELTA-IN-PROSE` BLOCK 码 + `branch-templates.md` 加 `<!-- EDITORIAL-NOTE-SECTION -->` marker + SKILL.md Step 0-i gate |

## 为什么会反复出现

同构的**根本原因**：

1. **自评 agent 盲区** — 写 outline 的 agent 做 self-review 时会假设自己遵守了规则；它不读上游 branch frontmatter，不读 vault scene body，不对机械验证
2. **规则隐性化** — branch taxonomy（flavor / minor / route）的语义只存在于 README 和作者大脑里，没有 frontmatter 级别的显式声明
3. **Render 阶段缺少 gate** — outline 写完到玩家看见中间有很多转换层（outline-writer / demo-renderer / player-flags 推算），任何一层丢规则都会导致最终表现与设计脱节
4. **Agency 替代倾向** — 系统在玩家应该表态的位置做"贴心的默认判断"是反复出现的陷阱。v4.4（first-contact 默认）和 v4.5（last-contact 优先级）是这一根因的结构对偶
5. **严重度校准错误（v4.10 新增子类）** — gate 规则正确、检测到了问题，但根据可配置分类（如 tier）做了过宽松的 severity 判定，作者/审稿者在海量 WARN 中忽略，结果与"gate 没检测到"效果等同。这类失败的根因不是"规则缺失"而是"规则的严重度配置与实际影响不匹配"——需要 cross-check（例如 registry tier vs outline usage 作为 speaker）
6. **Authoring-intent 误渲染（v4.11 新增子类）** — branch 源文件里的 section 语义没有显式标记，作者写给自己看的 editorial 散文（如 `### 情感影响` 里的 `mark 好感 +2（他意识到她愿意玩这个游戏）`）被下游 episode-writer 误识别为 machine-readable metadata，reformat（大写 + 去括号注释 + 速记化）后抄进玩家可见 prose。**与 data-silence 相反**：data-silence 是"上游有数据下游没 render"；authoring-intent-mis-rendered 是"上游的 editorial note 被当成 data 强行 render"。修复处方：上游 section 加显式 editorial-marker + 下游白名单 gate（prose 里的所有 HUD-like token 必须真对应 counter flag）

## 四件套沉淀模式

每次新 bug 识别后，固定产出 4 个物件以防同类复发：

1. **Spec 文档** — `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`
2. **Case-study reference** — `skills/<skill>/references/<topic>.md`，含规则定义 + 通过/失败范例
3. **Verify 脚本或人工 checklist** — `skills/<skill>/tools/verify-<topic>.py` 或 SKILL.md 里的 Step 0-N 人工清单
4. **SKILL.md Step 0-N gate** — 在自评流程最前端加硬门禁，verify FAIL → 回到 writing step，不得进入 subjective 8-dim 评分

v4.1-v4.11 十一次全部遵守这个模式。未来 v4.12+ 如果出现新同构 bug，继续按这个模式加。

## 具体规则摘要

### v4.2 · flavor-choice-gate 3-测试

flavor 默认渲染为 canonical 旁白；升级为可点击 CHOICE 必须同时通过：
- **T1 · 行动差异**：variant 的 Malia 在 1-2 拍内做不同的事
- **T2 · 即时可见**：其他 NPC / 场景在 2 分钟内反应不同
- **T3 · 赌注清晰**：3 个选项有不同人格/立场/关系定位

外加 **LI POV 硬约束**：`source_scene.pov != MC` 的 flavor 永远塌回，无论 T1/T2/T3。

### v4.3 · conditionalInsert 信号强度 T0-T4 分级

| 级别 | 形式 | 玩家感知 |
|------|------|---------|
| T0 | 无 payoff / 仅在 choice consequence | 0（silent drop）|
| T1 | stage-meta 叙述（告诉差异）| 10-20% |
| T2 | 可见身体动作（演出差异）| 40-60% |
| T3 | MC 内心回扣（显式点名上游）| 60-80% |
| T4 | 差异化对白（NPC 说不同的话）| 90%+ |

**最小合规**：T2 + T3（MC POV）/ T2 + T4（LI POV）/ T4 单独。

### v4.4 · seed subtype 5 合规条件

flavor 升格为 `flavor_subtype: seed`（强制 CHOICE）必须满足：

1. `source_scene.pov = malia-hernandez`（MC POV）
2. per-flag first-contact（variant 的 `sets_flags` 中至少一个 flag 首次设立）
3. 至少 2 个变体 `sets_flags` 输出不同
4. T3 通过
5. `hidden_route: false`

seed **跳过 T1/T2**（开场没有前置 flag / 没有后续 beat 可差异化是自然的），但必须附 `seed_evidence` 块（first_contact_flags / variant_differs / t3_stances）。

### v4.5 · route commitment choice schema

路线入口 Hook 处按 **gate satisfaction count** 三分支渲染：

| 满足 gate 数 | 渲染形式 | 原因 |
|---|---|---|
| **0** | 兜底独白（根据偏向 flag 动态）| 无路线可承诺，无冲突 |
| **1** | 该路线独白 + 自动 set commitment flag | 玩家已默认承诺该 LI，无决策冲突 |
| **≥2** | **强制 commitment CHOICE（5 固定槽位）** | 多条 gate 满足 = 跨 LI 投入，必须显式选 |

**固定 5 槽位**：4 LI（含 hidden route 三段式显示）+ 1 独自消化。Hidden route 永远展示 `🔒 ???`（第一周目）/ `🔒 Jared Karson`（meta 已解锁但 gate 未达）/ 亮色可点击（都满足），服务 replay 驱动。锁定槽位用 in-character 暗示（不暴露 flag mechanics）。

**Commitment flag schema**：`committed_to_{li}` boolean + `flag_type: commitment`；设立时触发 route-arc 的 `locks_out` 其他所有浪漫路线。`commitment_deferred` 用于"独自"槽，EP5+ 继续 shared-main。

**Branch-architect BG12**：populated route 的 `commitment_scene` / `commitment_flag` 不得为 null。

### v4.6 · choice-variant-weight-gate 三档饱和阈值

**前因**：v4.2/v4.4 管"flavor 能否升格为 CHOICE"（向上门槛），v4.3 管"合并后 payoff 最低合规"（下游 callback T2+T3 最小组合）。全都**没有管** variant 当下本身够不够重。结果 21 branch × 63 variant 普遍萎缩到 3-4 行对白 + 1 行 flag —— CHOICE 3 变体 B "speechless" 设 Mauricio route 入口必需 flag 但当下只 3 行戏剧 / 5-8 秒屏读，玩家"做了一个重决定但收到轻飘飘的戏剧反馈"。

**修复**：三档戏剧合约各自饱和点（`weight_tier` frontmatter 字段 + `weight_evidence` 声明合约 + 机械 gate）：

| weight_tier | 戏剧合约 | 行数下限/上限 | 结构要素最低命中 |
|---|---|---|---|
| `minor` | 完整 mini-scene，MC 真行动真后果 | 14-18 | 5/5（scene + dialogue + body-tell + environment + inner-monologue 全部必须）|
| `tone-shader` | 叙述 tone 深化，MC 行动不变 | 8-12 | 3/4（tone + environment + inner-monologue 必须，optional-npc 可选）|
| `seed` | 一瞥定性，快速人格锚定 | 5-7 | 2/3（physical-anchor + tone-closure 必须，hidden-knowledge-or-contrast 可选）|

**防矫枉过正**：下限机械 gate（防偷懒）+ 上限机械 gate（防 seed 写成传记 / minor 写成两场戏）+ 结构要素正文文本匹配（防灌水）。三者 AND。

### v4.7 · character-first-appearance-gate 三档 tier + 双扫描

**Tier 规则**（默认 severity 判定）：

| Tier | 要求命中 | 缺失后果 |
|---|---|---|
| T2（LI）| identity + relation + detail | BLOCK |
| T3（recurring）| identity + relation | BLOCK |
| T4（walk-on）| identity | WARN |
| T5（skip）| 无 | 跳过（`skip_intro_gate: true`）|

**双扫描（v1.0 → v1.2）**：
- **Forward scan**：对 registry 登记的每个 T2-T4 角色，在 outline 里找 first-mention（经 entities aliases），验证 tier-appropriate tokens 在 ±10 行窗口内命中
- **Coverage scan（v1.2）**：对 entities.key_character_db 每个 canonical，若出现在 outline 但 kebab(name) **不在 registry** → BLOCK `OUTLINE-ENTITY-NOT-IN-REGISTRY`（堵住 registry 漏登致 forward scan 静默跳过的影子 bug）

**支撑 schema**：`ips/{ip}/characters/{ip}-intro-registry-v{N}.json`——character-architect 新增输出，per-角色的 identity_tokens / relation_tokens / detail_token / reference_text 结构化数据源。

### v4.8 · scene-continuity-gate 四段锚（intra-CHOICE option consequence）

CHOICE option 的 `consequence` 字段必须同时命中 4 段锚里的 ≥ 3 段：

1. **玩家回应** — MC 的即时回应（对话或内心）
2. **角色反应** — NPC 的身体 / 对白反应
3. **场景过渡** — 时间 / 空间 / 状态的前后承接
4. **情感锚 + tag** — 情感脉络 + consequence 的 `tone`/`tag` 字段

命中 4/4 = PASS，命中 3/4 = WARNING（可接受），命中 ≤ 2/4 = FAIL。反模式：纯 flag 速记（`"Mark +2 · Easton 不爽 +2"`）、内心独白独唱。

### v4.9 · scene-transition-gate 四查（inter-scene edges）

scene→scene / scene→hook / hook→scene 直接 `next` 边必须通过 4 项独立检查：

1. **Temporal bridge** — opener 的时间段变化是否有 `同一天`/`次日`/`凌晨`/`下午` 等过渡锚
2. **Spatial bridge** — opener 的空间变化是否有 movement anchor（`走出`/`走到`/`往...去`）或同场景延续
3. **Phantom event** — opener 是否提到某完成事件（`球赛结束`/`派对散场`）但前序场景从未铺垫
4. **POV marker** — opener 是否切换 POV 且标明 `POV 切换:` / `镜头切回...`

任一检查 FAIL → 全边 FAIL。

### v4.10 · speaker-tier-floor（第三扫描 · 严重度校准）

**触发条件**：任何在 outline 里作为 `{ s: 'NAME' }` 出现的角色，registry tier 必须 ≥ **T3**（`SPEAKER_TIER_FLOOR` 常量）。

**规则表**：

| 条件 | 后果 |
|---|---|
| speaker 的 registry tier ∈ {T4, T5}（非 skip）| BLOCK `TIER-TOO-LOW-FOR-SPEAKER` + intro 用 T3 规则（identity + relation）重评 |
| speaker 的 registry tier ∈ {T2, T3}| tier floor OK |
| speaker token ∈ `{stage, YOU, MALIA, malia}` | 跳过（MC + stage direction）|
| speaker token 不匹配任何 entities alias（`WAITER` / `VOICE`）| 静默跳过 |
| `skip_intro_gate: true` | 跳过 |

**核心洞察**：T4 walk-on 规则仅 WARN 不 BLOCK，作者忽略 WARN 是高概率事件。speaker 角色意味着至少 recurring 互动，T3 是合理的最低 tier。这是 **cross-check**（registry 分类 vs outline 实际用法）来补 severity 判定。

**实现**：
- `_extract_speakers(scannable) -> set[str]` — 从 `{ s: 'NAME' }` 语法提取 speaker tokens
- `_speaker_to_char_id(entities_data) -> dict[str_cf, char_id]` — 反向 alias 映射（case-folded）
- `_speaker_tier_floor_scan(...)` — 对每个 speaker 的 char_id 查 tier，发 BLOCK
- 主循环：对 promoted char_id，构造 `CharacterEntry(tier=SPEAKER_TIER_FLOOR)` 送 `_evaluate` 重评

**配套 tier_note 字段**：registry entry 升 tier 时加 `tier_note: "EP1-4 Scene X 作为 speaker，从 T4 升 T3"` 作为审计注释，不影响 gate 行为。

### v4.11 · fake-delta-prose-gate（authoring-intent 误渲染）

**触发条件**：outline markdown 和 demo HTML 的 player-facing prose 字段（consequence / lines / nextLines / preview / body）里出现 `Character ±N` pattern 且无对应真 counter flag → BLOCK `FAKE-DELTA-IN-PROSE`。

**规则表**：

| 条件 | 后果 |
|---|---|
| prose 含 `Mark -1` / `Easton +1 · Mauricio 情绪暗流 +2` / `Mark 路线 +2` / `Easton 不爽 +2` 等 pattern | BLOCK |
| `> **好感变化**：Mark +2 / Easton +1 / ...` quote-block shorthand | multi BLOCK（chain 每个 match 各 BLOCK）|
| `flags: { mauricio_attraction_count: 1 }` dict 内 | 豁免（真 counter 声明位置）|
| `<!-- Mark +2 editorial -->` HTML 注释 | 豁免（editorial note）|
| `// Mark +2` JS 行注释（outside string literal）| 豁免 |
| YAML frontmatter / markdown code block | 豁免 |
| `<!-- NARRATIVE-START -->` 之前的 preamble | 豁免（CSS / 脚手架）|
| 小写 `mark_intimacy_count` 等 flag_id | 豁免（CHAR_NAMES 大小写敏感，`Mark ≠ mark`）|

**核心洞察**：branch 源文件有两种语义截然不同的 section —— `### 设立 flag`（machine-readable schema）和 `### 情感影响`（editorial 散文）。episode-writer 缺少 "section type awareness"，把后者误当作前者，reformat 后抄进 outline。关键是 **两层修复**：
1. **上游** branch-templates.md 给 `### 情感影响` section 加 `<!-- EDITORIAL-NOTE-SECTION -->` marker 显式标记语义类型
2. **下游** 白名单 gate 扫 player-facing prose，任何"看似 HUD delta"的 token 必须真对应 counter flag

**首例落地**：`outline-viewer-v4.html:1803,1811` 和 `outline-v4.md:1843,1848` 4 行共 12 个 fake-delta matches（均无 backing counter）。L1 删除、gate 加、reference doc + branch-templates marker + SKILL.md 0-i index 全部沉淀。

**与 v4.8 scene-continuity 的区分**：v4.8 的反模式示例是 `"Mark +2 · Easton 不爽 +2"`，和 v4.11 看起来是同一 pattern——但 v4.8 管的是 "consequence 四段锚是否 ≥3"（戏剧合约），v4.11 管的是 "token 是否对应真 counter"（数据一致性）。两者独立 gate，可以同时 fire：一个 consequence 既四段锚不够 + 又含 fake-delta，会被两个 gate 都 BLOCK。

## v4.4 与 v4.5 的结构对偶

| 维度 | v4.4 (first-contact) | v4.5 (last-contact) |
|---|---|---|
| 位置 | EP1 开场 | EP-N 路线入口 Hook |
| 玩家状态 | 无前置 flag → 无表态依据 | 多前置 flag 满足 → 多路线同时可进 |
| 系统错误 | 默认 inline canonical | 按 canon 优先级替选 |
| 丢失 agency | 起点 attitude | 终点 commitment |
| 修复处方 | seed CHOICE (动态 flag) | commitment CHOICE (显式选路) |

**共同的核心原则**：玩家应表态的位置**必须**是显式 CHOICE，系统不得代选。v4.5 是 v4.4 的**镜像同构**——同一根因在作品两端。

## 子类分布（v4.1-v4.11 四个子类）

| 子类 | 判据 | 成员 | 修复处方 |
|---|---|---|---|
| **规则缺失**（absence-of-check, strict）| gate 没写，问题进入 demo | v4.1, v4.2, v4.3 | 加 gate |
| **规则太弱**（rule-too-weak）| gate 存在但判据漏 case（edge 或新维度）| v4.4, v4.5, v4.6, v4.7, v4.8, v4.9 | 扩规则 / 加维度 |
| **严重度错配**（severity-miscalibration）| gate 检测到，但 severity 分类过宽松导致作者忽略 | v4.10 | 加 **cross-check**：某分类（如 tier）与实际用法（如 outline 是否 speaker）不一致时升严重度 |
| **Authoring-intent 误渲染**（authoring-intent-mis-rendered, NEW）| 上游 editorial note / 散文被下游误识别为 machine-readable metadata 强行 render 为玩家可见 UI data | v4.11 | **上游**加 section-type marker（`<!-- EDITORIAL-NOTE-SECTION -->`）+ **下游**白名单 gate（player-facing prose 里 HUD-like token 必须真对应数据）|

**未来 v4.12+ 检测 heuristic**：
- 看到 gate 输出大量 WARN 但真实影响严重时 → 可能是严重度错配（v4.10 模式）
- 看到玩家读到"看似 gameplay data 的 prose"但实际没功能支撑时 → 可能是 authoring-intent 误渲染（v4.11 模式）
- 看到作者 editorial 风格（括号注释 / 自然语言描述）出现在玩家可见 surface 时 → 一定是 authoring-intent 误渲染

## 与现有管线 skills 的关系

- **`branch-architect`** — 上游作者层。BG9（flavor frontmatter 合约）+ BG10（minor merge_payoff 合约）+ BG12（route commitment-scene 合约，v4.5 新增）+ Step 2/3 饱和点规范（v4.6 新增 `weight_tier` + `weight_evidence`）+ `<!-- EDITORIAL-NOTE-SECTION -->` marker（v4.11 新增在 `branch-templates.md` 的 `### 情感影响` section 前）在 branch 产出时就前置保证声明完整 + 语义类型标记
- **`character-architect`** — 上游人物层。v4.7 新增输出 `intro-registry-v{N}.json`（per-角色 identity/relation/detail tokens）+ v4.10 扩展 registry schema 加 `tier_note` 字段审计 tier 升级
- **`episode-writer`** — 下游 outline 层。Step 0-a（coverage）+ 0-b（flavor-choice）+ 0-c（conditional-insert checklist）+ 0-d（route-commitment checklist，v4.5）+ **0-e（character-first-appearance v1.0→v1.3）** + 0-f（choice-weight，v4.6）+ 0-g（scene-continuity，v4.8）+ 0-h（scene-transition，v4.9）+ **0-i（fake-delta-prose，v4.11 新增）** 九个 gate 在写完 outline 做 subjective 评分前顺序运行。v4.11 新增"Branch 源'情感影响'section 处理约束"写作规则节
- **Demo (tools/outline-viewer-v4.html)** — render 层。v4.5 实装 `computeGateStatus` + `renderCommitmentChoice` + `chooseCommitment/chooseDeferred`。v4.10 顺带加 `<!-- NARRATIVE-START -->` 标记修复 CSS prelude character class name 误伤 5+ pre-existing 隐形 BLOCKs。v4.11 L1 清理 ep3_c4 CHOICE 4 处 fake-delta shorthand

## 未来 v4.12+ 的预案

若下一次 bug 出现在：
- **player-flags 的 counter reachability** 层 → 四件套 = spec + `counter-reachability.md` 参考 + `verify-counter-reachability.py` + branch-architect Step N gate
- **demo-vs-outline 内容漂移** → 四件套 = spec + `demo-outline-parity.md` 参考 + `verify-demo-outline-parity.py` + CI hook
- **character consistency across episodes** → 四件套 = spec + `character-voice-drift.md` 参考 + 人工 checklist + character-architect Step N gate
- **EP5+ cross-route interaction** — v4.5 的 `locks_out` 在 EP5+ 玩家看 LI 互动时可能太死；预案：locks_out 仅锁 route-arc 入口，不锁互动场景（需 spec）
- **严重度校准的其他维度**（v4.10 后续）— tier 之外，其他分类字段（例如 POV narrator 但非 speaker、hidden route 角色是否适用普通 tier 规则）也可能有 cross-check gap；需要遇到时按 v4.10 模式加 cross-check 维度
- **Authoring-intent 误渲染的其他变体**（v4.11 后续）— branch 源的其他 section（例如 `### 合并条件` / `### 关键对白方向`）被误 render；或 character bible 的设计笔记泄漏到 outline prose；按 v4.11 模式加 section marker + 下游 surface-whitelist gate

每次 bug 的共通形态不变，只是**承载规则的 artifact 层级**换了位置。**Agency 替代检查 + 严重度 cross-check + Authoring-intent surface-whitelist** 应该作为所有未来 pipeline gate 的共通维度：任何时候看到"系统根据 flag 状态做默认选择"或"gate 发 WARN 但实际玩家会因此困惑"或"玩家可见 surface 出现作者 editorial-style 内容"，问一句"这是玩家应该表态的地方吗？""这个 WARN 的严重度是否匹配实际影响？""这段 prose 对应的 player-facing 数据真的存在吗？"。

## 引用

- **v4.1 reference**：`skills/episode-writer/references/outline-coverage-gate.md`
- **v4.2 spec**：`docs/superpowers/specs/2026-04-21-flavor-choice-gate-design.md`
- **v4.2 reference**：`skills/episode-writer/references/flavor-choice-gate.md`
- **v4.3 reference**：`skills/episode-writer/references/conditional-insert-signal-strength.md`
- **v4.4 spec**：`docs/superpowers/specs/2026-04-21-first-contact-seed-choice-design.md`
- **v4.4 reference**：`skills/episode-writer/references/flavor-choice-gate.md` § Seed subtype
- **v4.5 spec**：`docs/superpowers/specs/2026-04-22-route-commitment-choice-design.md`
- **v4.5 reference**：`skills/episode-writer/references/route-commitment-choice.md`
- **v4.6 spec**：`docs/superpowers/specs/2026-04-22-choice-variant-weight-gate-design.md`
- **v4.6 reference**：`skills/episode-writer/references/choice-weight-gate.md`
- **v4.6 verify script**：`skills/episode-writer/tools/verify_choice_weight_gate.py`（14/14 tests pass, 92% coverage）
- **v4.7 spec**：`docs/superpowers/specs/2026-04-22-character-first-appearance-intro-design.md`
- **v4.7 reference**：`skills/episode-writer/references/character-first-appearance-gate.md`（含 v1.0→v1.3 迭代 history）
- **v4.7 verify script**：`skills/episode-writer/tools/verify_character_first_appearance.py`（24/24 tests pass 包含 v4.10 扩展的 10 个 speaker-tier-floor tests）
- **v4.8 spec**：`docs/superpowers/specs/2026-04-22-scene-continuity-gate-design.md`
- **v4.8 reference**：`skills/episode-writer/references/scene-continuity-gate.md`
- **v4.8 verify script**：`skills/episode-writer/tools/verify_scene_continuity.py`（55/55 PASS on outline-v4 demo）
- **v4.9 spec**：`docs/superpowers/specs/2026-04-22-scene-transition-gate-design.md`
- **v4.9 reference**：`skills/episode-writer/references/scene-transition-gate.md`
- **v4.9 verify script**：`skills/episode-writer/tools/verify_scene_transition.py`（10/10 PASS on outline-v4 demo）
- **v4.10 spec**：`docs/superpowers/specs/2026-04-22-speaker-tier-floor-gate-design.md`
- **v4.10 reference**：`skills/episode-writer/references/character-first-appearance-gate.md` § 四轮落地（v1.3 speaker-tier-floor）
- **v4.10 verify script**：`skills/episode-writer/tools/verify_character_first_appearance.py` v1.3（扩展前 14 个 tests + 新增 10 个 speaker-tier-floor tests = 24/24 green；outline-v4 demo 前 10 BLOCKs 降至 2 unrelated BLOCKs，VIKKI + Owen 完全 clean）
- **v4.11 spec**：`docs/superpowers/specs/2026-04-22-fake-delta-prose-gate-design.md`
- **v4.11 plan**：`docs/superpowers/plans/2026-04-22-fake-delta-prose-gate.md`
- **v4.11 reference**：`skills/episode-writer/references/fake-delta-prose-gate.md`
- **v4.11 verify script**：`skills/episode-writer/tools/verify_fake_delta_prose.py`（14/14 new tests green；outline-v4 demo 前 12 fake-delta BLOCKs 降至 0；全 pytest 131/131 green）
- **v4.11 branch-architect patch**：`skills/branch-architect/references/branch-templates.md` §`### 情感影响` 前新增 `<!-- EDITORIAL-NOTE-SECTION -->` marker
- **Quality gates**：`skills/branch-architect/references/quality-gates.md`（BG9 / BG10 / BG12）
- **Commits**: norules-vn `b1fc94d` (v4.1-v4.4 sedimentation) · `03311cc` (v4.5 route commitment choice) · `a5a16d9` + `723fe1d` (v4.6 spec + plan) · v4.7-v4.9 commits batch · v4.10 commits `0d30627` (RED) + `c387289` (GREEN) + `b45eb6b` (registry+outline fixes) + `2c30f92` (sediment spec + plan + reference + SKILL.md) · **v4.11 commits `7a75bc7` (spec) + `0b14d31` (plan) + `0705b46` (RED 14 tests) + `87e5891` (GREEN gate) + `2915c77` (L1 4-prose cleanup) + `6dfc3a7` (L2a branch-templates marker) + `639742b` (L2b SKILL.md writing constraint) + `202eb74` (L3c reference doc) + `f6dcfec` (L3d SKILL.md 0-i gate index)**

## 相关

- [[concepts/unfolded-visual-novel]] — Unfolded 展示形态与素材管线
- [[concepts/ls-format]] — LS 脚本格式
- [[entities/dramatizer]] — Go binary for novel-to-screenplay conversion（上游相关）
- [[syntheses/data-silence-failure-class]] — data-silence 子家族（v4.7 是其首个实例；v4.11 是其反向对偶 authoring-intent-mis-rendered 子家族的首个实例）
