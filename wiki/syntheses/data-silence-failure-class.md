---
title: Data-Silence 失败类（VN Pipeline · 作者漏 render 家族）
updated: 2026-04-22T17:00
tags:
  - vn-pipeline
  - failure-pattern
  - character-architect
  - cast-coverage-auditor
  - episode-writer
  - no-rules
source_specs:
  - /Users/august/MobAI/norules-vn/docs/superpowers/specs/2026-04-22-character-first-appearance-intro-design.md
sibling_family: syntheses/render-time-silent-drop-failure-class
---

# Data-Silence 失败类

> **一句话定义**：上游数据完整，下游**作者**在 outline prose 中未 render 给玩家 = 玩家感知为 0。
>
> 区别于 [[syntheses/render-time-silent-drop-failure-class]]（v4.1-v4.5 agency-silence 家族，**系统代玩家选**），本家族是**作者漏写**的同源变体。两者共根：**玩家应看见的信息未传递**。

## 命名和定位

| 家族 | 失败主体 | 代表 skill 干预点 |
|---|---|---|
| **Agency-silence** (v4.1-v4.5) | **系统**在玩家应表态位置做替代判断 | episode-writer render 层 gate |
| **Data-silence** (v1+，2026-04-22 新增) | **作者**在玩家应看见位置未 render 数据 | character-architect (数据) + cast-coverage-auditor (sanity) + episode-writer (prose 层 gate) |

两个家族的根因都是**render** — 区别在渲染主体（系统代码 vs 作者 prose）。

## 已知变体

### v1 · character-intro-silence（2026-04-22）

**症状**：玩家在 demo / outline 里看到 "Josie / Jacinda / JT / Mamá / Papá" 等角色名直接出现，没有足够语境知道他们是谁。

**根因**：
- `character-architect` 输出的 bible 对每个角色都有完整描述（身份、与 MC 关系、辨识细节）
- `entity-normalizer` 输出的 entities.json 有 aliases + role + notes
- **但 outline script 作者从未承担"把这些信息转成玩家可见 prose"的责任**
- 结果：数据完整存在于上游 artifact，但玩家从未接收

**失败位**：outline → 玩家眼睛之间的 prose render 动作，完全依赖作者自觉。

**沉淀物（四件套）**：
1. **Spec**：`docs/superpowers/specs/2026-04-22-character-first-appearance-intro-design.md`
2. **Reference**：`skills/episode-writer/references/character-first-appearance-gate.md`
3. **Verify 脚本（双层）**：
   - 上游 schema 校验：`skills/cast-coverage-auditor/tools/verify_intro_registry_schema.py`
   - 下游 prose 校验：`skills/episode-writer/tools/verify_character_first_appearance.py`
4. **SKILL.md Step**：
   - `character-architect` 输出清单新增 deliverable 8（intro-registry）+ 自检 Q6
   - `cast-coverage-auditor` Step 9（intro registry sanity check）
   - `episode-writer` Step 0-e（首次出场 gate 人工 checklist）

**分级策略**（5-tier，按重要性决定 intro 深度）：

| Tier | 来源 | 深度要求 | Gate 严重度 |
|---|---|---|---|
| T1（MC）| `role: MC` 机器自动 | 开场独白自介 | skip |
| T2（LI）| `route_visibility: visible-main-route/hidden-route` 机器自动 | identity + relation + detail | BLOCK if miss |
| T3（recurring 配角）| 作者在 registry 显式 `tier: T3` | identity + relation | BLOCK if miss |
| T4（named walk-on）| 作者显式 `tier: T4` | identity | WARN if miss |
| T5（仅闪回提及）| 显式 `skip_intro_gate: true` + reason | 无 | 跳过 |

**Registry schema**（JSON，独立文件）：

```json
{
  "<character_id>": {
    "tier": "T2|T3|T4|T5",
    "identity_tokens": ["身份标签同义词"],
    "relation_tokens": ["与 MC 关系同义词"],
    "detail_token": ["辨识细节同义词"],
    "reference_text": "作者预写的 prose 范式",
    "skip_intro_gate": false,
    "skip_reason": ""
  }
}
```

**Gate 机制**：窗口 ±10 行，first-mention 检测基于 entities.json aliases，token 匹配 case-insensitive 子串（ASCII 用词边界、CJK 用字面子串）。

**首轮落地**（no-rules EP1-4）：9 处 BLOCK → 2 处假阳性修（NARRATIVE-START marker + ASCII 词边界）+ 6 处真修（4 处改 outline prose，2 处调 registry tokens 匹配 hidden-route 特殊 context）→ 首轮 8 角色扫描 PASS。

### 二轮加固（2026-04-22 晚 · Mamá/Papá Hernandez 静默漏检）

**症状**：首轮 gate PASS，但 demo（Scene 2.3 周日晚餐）player 反馈 Mamá/Papá/Mark 首次说话没看到人物介绍——gate 说"通过"、player 眼睛说"没看见"。

**根因诊断**（三层咬合 bug）：

1. **Entities 漏登**：registry 登记 `mama-hernandez`，entities.v2 **不存在** Mama Hernandez 条目
2. **char_id ↔ canonical_name 错位**：registry 用昵称 key `papa-hernandez`，entities 用真名 `Samuel Hernandez`——两侧 kebab 不对齐
3. **Kebab 规则不一致**：gate 用 `re.sub(r"\s+", "-", ...)` 把 "Mrs. Reyes" 变 `mrs.-reyes`，registry 手写 `mrs-reyes`——全员不匹配

→ 这些角色的 canonical_name 在 alias lookup 回退到 char_id 字面串 → outline 里找不到 → **gate 静默跳过，既不 BLOCK 也不 WARN**。扫描数 8/18，delta 过去被忽略。

**加固策略**（上游 cross-check + 规则统一 + 作者侧规范）：

| 位置 | v1 → v1.1 改动 |
|---|---|
| `verify_intro_registry_schema.py` | 接受可选 entities arg，加 `ENTITY-MISSING` cross-check（v1.3） |
| 两个 verifier 共用 `_kebab(name)` | `re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")` |
| `character-architect` SKILL.md | 新增 **Alias hygiene** 与 **Tier 判定** 原则（v1.1） |
| `cast-coverage-auditor/references/intro-field-check.md` | v1.3 gate doc + registry↔entities cross-check section |
| `episode-writer/references/character-first-appearance-gate.md` | v1.1，加二轮案例 + Diagnostic flow + Alias hygiene |

**Alias hygiene 规则（新增硬约束）**：

- entities `aliases`/`aliases_zh` **禁止**含泛化代词：`我妈`、`我爸`、`妈`、`爸`、`dad`、`mom`、`mother`、`father`
- 原因：
  - **POV 假阳性**：Mauricio 独白 "I become my dad" 里 word-boundary 命中 → Samuel Hernandez 的 first-mention 被锁到 Mauricio 台词行
  - **first-mention 锁死**：Malia EP1 独白 "我妈把他当儿子看" 把 Mama Hernandez 锁在 EP1 exposition，EP2 真正出场时 gate 不再检查
- 正确位置：泛化代词只进 `identity_tokens`（描述性 prose 匹配），不进 aliases（名字匹配）

**Tier 判定补充规则**：父母/继父母/recurring 家人 → **T3**，不是 T4。T4 是真正意义的 walk-on（≤1 场、一句台词）。违反此原则的代价：T4 是 WARN 不 BLOCK，漏检不会被强制。

**修复后**：扫描从 8 升到 11，Scene 2.3 加 3 句 MALIA 内心独白 intro Mamá/Papá/Mark，schema verifier（含 entity cross-check）+ first-appearance gate 双 PASS，25 tests all green。

### 三轮加固（2026-04-22 · Easton 家 registry-coverage-gap · 影子 bug 根治）

**症状**：二轮 v1.1 gate PASS，但新 demo（Scene 3.4 Easton 家周二早晨）player 反馈 Denzel / Rafferty King / Mrs. King 3 位 hidden-route 家人突然出现没任何介绍——gate 再次说"通过"、player 眼睛再次说"没看见"。

**根因诊断**（比二轮 Mamá/Papá 更深一层）：

| 层 | 情况 | v1.1 修了吗？|
|---|---|---|
| registry 登了但 kebab 不齐 / aliases 错 | silent-skip：gate 找不到 first-mention | ✅ v1.1 修 |
| **registry 根本没登记** | silent-skip：gate 完全看不到该角色 | ❌ v1.1 没覆盖 |
| entities 都没登（entity-normalizer 漏）| gate 视野完全外 | ❌ v1.1 没覆盖 |

Easton 家 3 人：entities.v2 里有（v2 baseline 就登了），但 registry v1 **完全没 entry**——forward scan 遍历的是 `registry.characters`，registry 里没的角色 gate **看都看不见**。扫描数 11 / 18（非 T5）的 7 人 delta 被忽略。

更严重：**Owen** 作为 EP4 Scene 4.3 关键 gossip 传播者，entities.v2 里**根本无条目**——上游 entity-normalizer 漏登，registry 自然没可能登，outline 引用整个在 gate 外。

**加固方案（v1.2 · coverage-scan · 双向合围）**：

| 方向 | 任务 | 工具 |
|---|---|---|
| registry → entities（v1.1）| registry 登了但 entities 没有 | schema verifier `ENTITY-MISSING` BLOCK |
| **outline → registry（v1.2 新增）**| entity 出现在 outline 但 registry 没登 | first-appearance gate `_coverage_scan` → `OUTLINE-ENTITY-NOT-IN-REGISTRY` BLOCK |

具体实现：在 first-appearance gate 的 `main()` 里加反向遍历 `entities.key_character_db`，对每个 canonical 按 aliases 搜 outline；若 found 但 kebab(name) 不在 registry → BLOCK。

**Entity aliases hygiene v2 扩展**：
- v1.1 规则"禁 generic 代词"继续有效
- v1.2 新增"必有 first-name alias"—— Rafferty King / Tyler Garcia / Vikki Hernandez / Jacinda Thomas / Denzel King（以及 entities 里任何 full_name 超一个词的角色）都要补 first-name 作为 alias，因为 outline 常用 single-name 引用

**首轮修复（no-rules EP1-4 三轮落地）**：
- entities.v2 补 Owen（新增）+ 5 first-name aliases（Rafferty / Denzel / Tyler / Vikki / Jacinda）
- registry v1 补 5 entry：mrs-king / rafferty-king / denzel-king（T3）+ tyler-garcia / owen（T4）
- outline Scene 3.4 加 3 句 MALIA 内心独白 intro King 家
- registry token 微调：Mrs. King 的 `relation_tokens` 加"坚持让她留下"匹配 line 1064 原文
- Jacinda token 补"Joseph 的现任妻子"匹配 Scene 1.0.B 餐厅 flashback
- 扫描 11 → 18（所有非 T5 active entries 全覆盖）
- 29/29 pytest green（first-appearance 14 + schema 15）

**Tier 判定原则 v1.2 补充**：
- Hidden route 家人（Easton 家父母/妹妹）→ T3
- 队友朋友圈支线 walk-on（Tyler / Owen）→ T4
- EP5+ 预计升格的角色可在 registry entry 加 `tier_note: "EP1-4 仅 X 场，预计 EP5+ 升级"`

## 与 agency-silence 家族的交叉

同一 outline 可能同时触发两个家族的 gate：
- 作者忘写 flavor CHOICE → **agency-silence**（系统 inline canonical）
- 作者忘写 Josie intro → **data-silence**（玩家不认识涂指甲油的那个）

两类 gate **独立运行、独立通过**；审稿时串联检查，顺序无关紧要。

## 失败模式识别

**谁没告诉玩家？**
- 如果是"系统没给玩家选"→ agency-silence family → 查 [[syntheses/render-time-silent-drop-failure-class]]
- 如果是"作者 prose 没写"→ data-silence family（本页）

## 四件套沉淀模式（共通）

无论哪个家族，识别新 bug 后都产出 4 个 artifact 防复发：
1. **Spec** — `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`
2. **Reference** — `skills/<skill>/references/<topic>.md`
3. **Verify 脚本 / checklist** — `skills/<skill>/tools/verify-<topic>.py` 或 SKILL.md Step 0-N
4. **SKILL.md Step 0-N gate** — 在 self-review 最前端加硬门禁

## v1.2 coverage-scan 的可迁移价值

**Coverage-scan 本质是"反向全量防影子 bug"**——适用于任何"上游 A 全量 → 下游 B 登记 → 下游 C 验证" 的 pipeline：

- **A**（上游全量，e.g., entities）可能比 **B**（下游登记，e.g., registry）多
- 若 **C**（验证，e.g., gate）只遍历 **B**，就会漏检"**A 里有但 B 没登**"的条目
- 修复：**C** 额外反向扫描 **A**，对每个 item 检查是否在 **B**，不在则 BLOCK

类似模式可迁移到：
- **locations**：entities.location_map 全量 → outline 引用的 location（作者用"Ground Coffee"/"Elites Club"是否都 location-intro？）
- **items**：entities.item_map 全量 → outline 引用的道具（蝴蝶手链 / 1960 Impala）
- **flags**：partition.yaml flags 全量 → outline 里 `[FLAG: xxx]` 操作（是否有未定义 flag？）

## 未来 data-silence 变体预案

候选 bug 位置：
- **Location 漏 intro**：玩家第一次到 "Ground Coffee" / "Joseph's Restaurant" / "Morhills Academy Locker Area" 时，有没有自然 prose 描述这是什么地方？→ 可能需要 `location-first-appearance-gate`（复用本 gate 的 token 匹配算法）
- **Flag 含义漂移**：某个 flag（e.g., `mauricio_self_awareness_count`）在不同 scene 被赋值，但 prose 没体现其含义 → `flag-semantic-anchor-gate`
- **Item 漏 intro**：道具首次出现（蝴蝶手链 / 1960 Impala）玩家不知道意义 → `item-first-appearance-gate`

每个新 variant 都遵循四件套 + registry-driven token match 模式。

## 引用

- **v1 spec**：`docs/superpowers/specs/2026-04-22-character-first-appearance-intro-design.md`
- **v1 plan**：`docs/superpowers/plans/2026-04-22-character-first-appearance-intro.md`
- **v1 upstream check**：`skills/cast-coverage-auditor/tools/verify_intro_registry_schema.py` + `references/intro-field-check.md`
- **v1 downstream gate**：`skills/episode-writer/tools/verify_character_first_appearance.py` + `references/character-first-appearance-gate.md`
- **v1 registry example**：`ips/no-rules/characters/no-rules-intro-registry-v1.json`（18 角色，T2-T5 全 tier 示例）
- **Sibling family**：[[syntheses/render-time-silent-drop-failure-class]]（agency-silence，v4.1-v4.5）

## 相关

- [[concepts/unfolded-visual-novel]] — VN 展示形态与素材管线
- [[concepts/mss-format]] — MSS 脚本格式
