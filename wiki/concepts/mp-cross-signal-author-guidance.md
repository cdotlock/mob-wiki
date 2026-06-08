---
title: MP Cross-Signal Author Guidance
description: 多人模式（MP）小说写作 Agent 的设计指引：什么时候让一方的选择通过 cross-signal 跨过去影响另一方 → 产生 checkpoint，什么时候不要；附完整因果链、节奏建议、模板、常见错误
updated: 2026-06-08
---

# MP Cross-Signal Author Guidance（多人模式写作指引）

> **对象**：多人模式（MP）小说写作 Agent。
> **目的**：告诉 agent"什么时候让一方的选择跨过去影响另一方"（→ 产生 checkpoint），以及"什么时候不要"。
> **背景**：2026-06-08 [[entities/lunaverse-backend]] save/checkpoint/revival/MP redesign spec 把死亡复活收敛为统一 50 宝石 SKU，复活点 = 最近的 checkpoint。Checkpoint 的产生由 agent 的写法决定。

---

## 1. 一句话告诉机制

**Agent 每写一个 `@choice` 都会自动铸造一个跨角色信号（cross-signal）。但只有当另一个角色的剧本用 `@if` 引用了这个信号，这个选择才会被"晋升"为 checkpoint —— 玩家死亡时的复活锚点。**

所以 agent 的设计权落在"对方剧本要不要 `@if` 引用我方这个选择"：

- **引用** → 此 choice = checkpoint = 死亡复活点
- **不引用** → 此 choice 只是普通选择 → 玩家死了直接跳过、回退到更早的 checkpoint

cross-signal 命名格式见 [[concepts/ls-format]] §MP 跨角色信号命名 / 上游 LS-SPEC §4.7（content-addressed `mp_<role>_a<actIndex>_c<choiceIndex>_<optionId>`，2026-06-08 PR #1 [[entities/lunascripts]] 落地）。

---

## 2. 为什么这件事重要：玩家的体验账

死了花 50 宝石复活到最近的 checkpoint。Checkpoint 密度直接决定死亡惩罚力度：

| Checkpoint 密度 | 玩家体验 |
|---|---|
| **太密**（每幕 3+ 个） | 死了几乎不倒退、紧张感稀释、宝石被 nickel-and-dime 持续消耗 |
| **健康**（每幕 1-2 个） | 死了回退半幕到一幕、节奏稳、宝石支出有节制 |
| **太稀**（隔幕一个） | 死了倒退两幕、玩家流失、被觉得"不公平" |

Agent 写的"对方剧本是否 `@if` 引用我方选择"，本质上是在设计**玩家的死亡惩罚力度**。

---

## 3. ✅ 应该 cross-reference 的场景

让 Role B 的剧本通过 `@if (mp_<role-a>_a<X>_c<Y>_<opt>)` 引用 Role A 的选择，**当且仅当以下其一**：

### 3.1 关系拐点
一方对另一方表达信任、承诺、距离、背叛。对方下一幕的开场情绪、对话姿态、互动密度需要反映这一刻。

> 例：Diego 在 act 2 的某个 joint choice 上选"对 Seiya 摊牌"。Seiya 下一段 `@if` 引用 → Seiya 坦诚回应 vs Seiya 闭口拉开距离。

### 3.2 道德选择且对方需要回应
一方做了带道德重量的决定（救谁、藏什么、揭穿什么），对方很自然地会问、会评、会因此重估关系。

> 例：Ryu 选"瞒着 Seiya 这件事"。Seiya 下一幕里有人无意泄密 → Seiya 的反应分两种：直接面对 vs 被绕过的羞愧。

### 3.3 关键剧情走向分歧
一方决定能让对方进入完全不同的 scene、地点、对话伙伴。

> 例：Ryu 选"去码头" vs "去工地"。Seiya 在对应 act 的开场被叫去同一地点 → 两条线在地点上汇合，cross-signal 决定汇合地点。

---

## 4. ❌ 不该 cross-reference 的场景

写 `@choice` 但**不让对方剧本引用** cross-signal：

### 4.1 内心戏 / 独白
一方独自做的内心选择，对方根本没看见、没参与。

> 例：Ryu 一个人翻旧照片，选"留下" vs "撕掉"。Seiya 那边正做完全无关的事 → **不引用**。这选择影响 Ryu 自己后续触发哪段回忆 scene，不影响 Seiya。

### 4.2 风味选择 / 情感色彩
塑造角色个性但不门控走向：穿什么、吃什么、买什么。

> 例：Ryu 选"咖啡" vs "茶"。对 Seiya 的剧本进度毫无影响 → **不引用**。

### 4.3 节奏休息 / 早期铺垫
故事早期（前 1-2 幕）建立世界观、关系基线的选择。这里不该有重量。

> 例：第 1 幕末尾的"先听 A 还是 B 介绍背景"。两边都是必经信息 → **不引用**。

### 4.4 已经在 SP fork-checkpoint 范围内
如果某 joint choice 已经是自己一方的 SP fork-checkpoint（routing-forking gate 引用了它），别同时让对方再 cross-reference 它。一个 choice 同时产生两个 anchor → 玩家死了不知道应退到哪个。让 SP fork 独占。

---

## 5. 节奏建议

| 剧本规模 | 推荐 cross-referenced choices 总数 |
|---|---|
| 一方 4 幕（共 8 幕双人） | 4-6 个 |
| 一方 6 幕（共 12 幕双人） | 6-9 个 |
| 一方 8 幕（共 16 幕双人） | 8-12 个 |

**经验法则**：每幕 1-2 个 cross-reference，平均下来每 4-6 个 joint choice 里挑 1 个被 cross-referenced。其余 joint choice 做个性化、情绪色彩、岔路探索就好 —— 不必都拔成 checkpoint。

---

## 6. 模板：写 vs 不写

### 6.1 ✅ 让对方引用 → 产生 checkpoint

```ls
# Role: diego, act 2, 第 3 个 joint @choice (choiceIndex=2)
@choice "你要不要告诉 Seiya 你看到的事？"
  - A "告诉她"
  - B "瞒着"

# Role: seiya, act 2 后段
@if (mp_diego_a2_c2_A)
  seiya: "你早说啊。" 她突然不再拐弯。
@elif (mp_diego_a2_c2_B)
  seiya: "你最近怪怪的。" 她不动声色但拉开了距离。
```

→ Diego 的 a2_c2 此刻被 Seiya `@if` 引用 → 晋升 checkpoint → 玩家死了花 50 宝石复活到这里。

### 6.2 ❌ 不让对方引用 → flavor choice 而已

```ls
# Role: diego, act 2, 第 4 个 joint @choice (choiceIndex=3)
@choice "晚上吃什么？"
  - A "拉面"
  - B "便利店"

# Role: seiya — 完全没 @if (mp_diego_a2_c3_*) 引用
# (Seiya 该幕的剧情对 Diego 吃啥无感)
```

→ Diego 的 a2_c3 不会成为 checkpoint。死了复活会跳过此处，回到更早的 cross-referenced choice。

---

## 7. 常见错误

1. **每个 @choice 都让对方引用** → checkpoint 密度过高、紧张感稀释、宝石经济崩坏。**修正**：每幕只挑 1-2 个真正有关系重量的 choice 让对方引用。

2. **真正关键的 choice 没让对方引用** → 玩家死了倒退很远，路过明显的分水岭却没存档点。**修正**：写完一幕后扫一遍，找最重要的 1-2 个"对方应该会有反应"的 choice，让对方剧本 `@if` 它。

3. **forward-reference（对方引用我方未来才会发生的选择）**：引擎不会炸，但 `@if` 永远 false 直到信号铸造前 —— 玩家体验上会出现"突然解锁的对话"。**修正**：只引用对方剧本时间上**早于**自己当前位置的 cross-signal。

4. **以为引用越多 checkpoint 越"强"**：第 1 次 `@if` 就把它晋升为 checkpoint，后续 `@if` 是免费搭车。多次引用本身没问题，但 checkpoint 是 binary 状态，不存在"强弱"。

5. **roleKey 中途改名** → `mp_<role>_a...` 里的 role 是 roleKey，重命名等于把所有 `@if` 引用打废。**修正**：开题时敲定 roleKey 命名（ryu / seiya / diego / ...），别中途改。

---

## 8. 命名格式参考（agent 不手写，引擎自动铸造）

```
mp_<role>_a<actIndex>_c<choiceIndex>_<optionId>
```

- `<role>`：被引用方的 roleKey（如 `diego`, `seiya`, `ryu`）
- `<actIndex>`：在该角色 track 内第几集（**0-indexed**）
- `<choiceIndex>`：该集 DFS 文档顺序下第几个 joint `@choice`（**0-indexed**）
- `<optionId>`：选了哪个选项（`A`, `B`, `C` 或自定义 ID）

**示例**：Diego 第 3 集（actIndex=2）里 DFS 第 1 个 joint choice（choiceIndex=0）的 A 选项 → 铸造 `mp_diego_a2_c0_A`。

Seiya 引用：`@if (mp_diego_a2_c0_A)` ... → Diego 的 a2_c0 被晋升为 checkpoint。

---

## 9. 完整因果链（agent 的思维模型）

```
agent 写一个 @choice
    ↓
玩家做选择
    ↓
引擎自动铸造 cross-signal: mp_<my-role>_a<X>_c<Y>_<opt>
    ↓
对方剧本里有没有 @if 引用此信号？
    ├─ 有 → 此 choice 晋升 checkpoint → 玩家死了花 50 宝石复活到这里
    └─ 无 → 此 choice 是普通选择，玩家死了跳过此点回到更早的 checkpoint
```

**Agent 的判断权完全落在那个 `@if` 上。** 一个 choice 值不值得让对方反应是 narrative 判断，不是 mechanical 判断 —— 别恐惧、别求多。

---

## 10. 上下文锚点

- **上游真理**：[github.com/cdotlock/lunascripts `LS-SPEC.md` §4.7 MP 跨角色信号命名](https://github.com/cdotlock/lunascripts/blob/main/LS-SPEC.md) (PR #1 merged 2026-06-08)
- **Spec 来源**：lunaverse-backend `docs/superpowers/specs/2026-06-08-save-checkpoint-revival-mp-redesign-design.md` §5 (checkpoint 静态分析) + §6 (revival 收敛)
- **静态分析实现**：lunaverse-backend `app/core/checkpoints.ts` — checkpoint 怎么从 cross-signal 引用算出来
- **Handoff 源文档**：lunaverse-backend `docs/mp-cross-signal-author-guidance.md` (git commit 12538261)
- **相关 wiki**：[[concepts/ls-format]]、[[concepts/signal-int-backend]]、[[concepts/stable-step-id]]、[[entities/lunascripts]]
