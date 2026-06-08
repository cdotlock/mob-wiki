---
title: MP Cross-Signal Author Guidance
description: 多人模式（MP）小说写作 Agent 设计指引 — block-on-cross-signal 运行时下的同步密度设计。Cross-signal 引用决定双人剧情哪里汇合（旧 every-choice-blocks → 新 block-on-cross-signal），revival anchor 是顺带的二级效果
updated: 2026-06-08
---

# MP Cross-Signal Author Guidance（多人模式写作指引）

> **对象**：多人模式（MP）小说写作 Agent。
> **目的**：告诉 agent"什么时候让一方的选择跨过去影响另一方"（→ 此选择成为**双人同步点**，对方走到对应位置时会停下等你；同时顺带成为死亡复活锚点）。
> **背景**：2026-06-08 [[entities/lunaverse-backend]] spec 把 MP 运行时从"每个 @choice 都是全局 barrier"重做成 **block-on-cross-signal** —— 只有真正被对方引用的选择才阻塞，其余各走各的。这份 guidance 告诉 agent 怎么用好这个机制。

---

## 1. 这次 MP 重做的核心：从"步步同步"到"按需同步"

| 旧设计（已废弃） | 新设计（当前） |
|---|---|
| 每个 MP `@choice` 都是全局 barrier | 只有"被对方 `@if` 引用的 @choice"才阻塞 |
| 双方在每个选项都得互等 | 双方独立推进，只在真正的交叉点汇合 |
| 一方慢半拍 → 对方全程卡 | 一方慢 → 只影响下一个真正交叉点 |
| 玩一会儿就尬住 | 大部分时间各自享受自己的剧情节奏 |

**实现位置**：lunaverse-backend `app/services/multiplayer-room-service.ts:696-755` — `findJointChoiceEntry()` 查 manifest，命中才走阻塞 path，否则直接 `submitChoice` solo 推进，房间状态完全不动。

---

## 2. 一句话告诉机制

Agent 每写一个 `@choice` 都会自动铸造一个跨角色信号（cross-signal）。**只有当对方剧本里有 `@if` 引用了这个信号，这个选择才会变成 joint —— 双方在此汇合**。

所以 agent 的设计权完全落在"对方剧本里要不要 `@if` 引用我方这个选择"这一个动作上：

- **对方有 `@if` 引用** → 此 `@choice` 是 joint sync point → 对方走到对应位置会停下来等你（你也会停下来等对方的对应引用）
- **对方没引用** → 此 `@choice` 是 solo 选择 → 对方该走继续走，你这边也不挡他

**顺带**：joint sync point 同时被登记为死亡复活锚点（玩家死了花 50 宝石复活回这里），但这是次要效果 —— 写的时候按"什么时候该汇合"来想，不要按"什么时候该存档"来想。

cross-signal 命名格式见 [[concepts/ls-format]] §MP 跨角色信号命名 / 上游 [[entities/lunascripts]] LS-SPEC §4.7。

---

## 3. agent 的"@if 决策"在设计什么

写 `@if (mp_<对方-role>_a<X>_c<Y>_<opt>)` 的次数 = **MP 故事的同步密度**：

| 同步密度 | 玩家体验 |
|---|---|
| **太密**（每幕 3+ 个汇合点） | 像旧 MP 一样卡 —— 各走两步就要等对方，节奏崩、对方一旦慢就尬 |
| **健康**（每幕 1-2 个汇合点） | 各玩各的为主，每幕有 1-2 个真正的"关系交叉时刻"汇合一下 |
| **太稀**（隔幕一个甚至没有） | 两条线像两个完全独立的 SP 故事，"多人感"消失 |

这是 **MP 节奏的核心刻度**。写 cross-reference 不是"存个档"，是"在这里两人剧情要真的交汇"。

---

## 4. ✅ 应该让对方 `@if` 引用我方选择的场景

### 4.1 关系拐点
一方对另一方表达信任、承诺、距离、背叛。对方下一幕的开场情绪、对话姿态、互动密度需要反映这一刻。

> 例：Diego 在 act 2 某 joint choice 选"对 Seiya 摊牌"。Seiya 下一段 `@if` 引用 → Seiya 坦诚回应 vs Seiya 闭口拉开距离。**此处两人在剧情上必须汇合一次，否则关系拐点不成立。**

### 4.2 道德选择且对方需要回应
一方做了带道德重量的决定（救谁、藏什么、揭穿什么），对方很自然会问、会评、会因此重估关系。

> 例：Ryu 选"瞒着 Seiya 这件事"。Seiya 下一幕里有人无意泄密 → Seiya 反应两种：直接面对 vs 被绕过的羞愧。**Seiya 必须知道 Ryu 怎么选了，否则反应没有依据 → 必须汇合。**

### 4.3 关键剧情走向分歧
一方决定能让对方进入完全不同的 scene、地点、对话伙伴。

> 例：Ryu 选"去码头" vs "去工地"。Seiya 在对应 act 开场被叫去同一地点 → 两条线在地点上汇合，cross-signal 决定汇合地点。**汇合本身就是这个机制要实现的事。**

---

## 5. ❌ 不该让对方引用的场景（保持 solo 节奏）

### 5.1 内心戏 / 独白
一方独自的内心选择，对方根本没看见、没参与。

> 例：Ryu 一个人翻旧照片，选"留下" vs "撕掉"。Seiya 那边正做完全无关的事 → **不引用**。此选择只影响 Ryu 自己后续触发哪段回忆 scene。**对方完全不该停下来等。**

### 5.2 风味选择 / 情感色彩
塑造角色个性但不门控走向：穿什么、吃什么、买什么。

> 例：Ryu 选"咖啡" vs "茶"。对 Seiya 剧本进度毫无影响 → **不引用**。**让对方继续走自己的，不要为这种选择卡住。**

### 5.3 节奏休息 / 早期铺垫
故事早期（前 1-2 幕）建立世界观、关系基线。这里两人还没真正交汇，不该有同步压力。

### 5.4 已经在 SP fork-checkpoint 范围内
如果某 joint choice 已经被自己一方的下游 routing-forking gate 引用了（SP fork-checkpoint），别再让对方也来引用。让 SP fork 独占。

---

## 6. 节奏建议

| 剧本规模 | 推荐 cross-referenced（= sync point）总数 |
|---|---|
| 一方 4 幕（共 8 幕双人） | 4-6 个 |
| 一方 6 幕（共 12 幕双人） | 6-9 个 |
| 一方 8 幕（共 16 幕双人） | 8-12 个 |

**经验法则**：每幕 1-2 个汇合点，平均下来每 4-6 个 joint choice 里挑 1 个被 cross-referenced。其余 joint choice 让它们做个性化、情绪色彩、岔路探索 —— solo 推进、不阻塞对方。

---

## 7. 模板：写 vs 不写

### 7.1 ✅ 让对方引用 → 双方在此汇合

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

→ Diego 的 a2_c2 被 Seiya 引用 → 此处变 joint sync point：Seiya 走到 act 2 后段会等 Diego 先把这里选完。两人在此剧情上真正交汇。（顺带：成为 revival anchor。）

### 7.2 ❌ 不让对方引用 → solo 自由推进

```ls
# Role: diego, act 2, 第 4 个 joint @choice (choiceIndex=3)
@choice "晚上吃什么？"
  - A "拉面"
  - B "便利店"

# Role: seiya — 完全没 @if (mp_diego_a2_c3_*) 引用
# (Seiya 该幕的剧情对 Diego 吃啥无感)
```

→ Diego 的 a2_c3 是 solo 选择。Diego 选完直接走下去，Seiya 那边不停、不等、不卡。

---

## 8. 常见错误

1. **每个 @choice 都让对方引用** → sync 密度回到旧设计，"玩一下就卡"重现。**修正**：每幕只挑 1-2 个真正有汇合意义的 choice。

2. **真正关键的 choice 没让对方引用** → 关键关系拐点变成 solo，对方走过去时浑然不觉，故事失去重量。**修正**：写完一幕后扫一遍，找最重要的 1-2 个"对方应该会有反应"的 choice，让对方剧本 `@if` 它。

3. **forward-reference（对方引用我方未来才会发生的选择）**：引擎不会炸，但 `@if` 永远 false 直到信号铸造前 —— 玩家体验上会出现"对方等我但我那边还没到"的尴尬阻塞。**修正**：只引用对方剧本时间上**早于**自己当前位置的 cross-signal。

4. **以为引用越多 sync 越"强"**：第 1 次 `@if` 就把它变 sync point，后续 `@if` 是免费搭车。多次引用 OK，但 sync point 是 binary 状态。

5. **roleKey 中途改名** → `mp_<role>_a...` 里的 role 是 roleKey，重命名 = 所有 `@if` 引用打废 + 所有 sync point 失效。**修正**：开题敲定 roleKey 命名，别中途改。

---

## 9. 顺带说一下：revival anchor

每个 sync point 同时也是 revival anchor —— 玩家死了花 50 宝石复活回上一个 sync point。这是 **block-on-cross-signal manifest 的二级效果**：

- manifest = 静态分析出来的 sync point 集合（[[concepts/stable-step-id]] 寻址）
- runtime block on this set（主功能：MP 节奏）
- revival snapshot 也 anchor 到这个 set（顺带：死亡惩罚刻度）

写"每幕 1-2 个 sync point"自然也满足"每幕 1-2 个 revival anchor"。**为节奏写，存档自然跟上。**

---

## 10. 命名格式参考（agent 不手写，引擎自动铸造）

```
mp_<role>_a<actIndex>_c<choiceIndex>_<optionId>
```

- `<role>`：被引用方的 roleKey（如 `diego`, `seiya`, `ryu`）
- `<actIndex>`：在该角色 track 内第几集（**0-indexed**）
- `<choiceIndex>`：该集 DFS 文档顺序下第几个 joint `@choice`（**0-indexed**）
- `<optionId>`：选了哪个选项（`A`, `B`, `C` 或自定义 ID）

**示例**：Diego 第 3 集（actIndex=2）里 DFS 第 1 个 joint choice（choiceIndex=0）的 A 选项 → 铸造 `mp_diego_a2_c0_A`。

---

## 11. 完整因果链（agent 的思维模型）

```
agent 写一个 @choice
    ↓
玩家做选择
    ↓
引擎自动铸造 cross-signal: mp_<my-role>_a<X>_c<Y>_<opt>
    ↓
对方剧本里有没有 @if 引用此信号？
    ├─ 有 → 此 @choice 进入静态 manifest
    │       ├─ runtime: sync point — 对方走到对应位置停下等你（block-on-cross-signal）
    │       └─ revival: anchor — 玩家死了花 50 宝石复活回这里（顺带）
    └─ 无 → 此 @choice 是 solo 选择
            ├─ runtime: 对方不停、不等、自由推进
            └─ revival: 玩家死了跳过此点回更早 sync point（顺带）
```

**agent 的判断权完全落在那个 `@if` 上。** 这是 narrative + pacing 判断："这一步两人剧情真的要在此交汇吗？" —— 不是 mechanical / 存档 判断。

---

## 12. 上下文锚点

- **上游真理**：[github.com/cdotlock/lunascripts `LS-SPEC.md` §4.7 MP 跨角色信号命名](https://github.com/cdotlock/lunascripts/blob/main/LS-SPEC.md) (PR #1 merged 2026-06-08)
- **Spec 来源**：lunaverse-backend `docs/superpowers/specs/2026-06-08-save-checkpoint-revival-mp-redesign-design.md` §5（manifest 静态分析）+ §7（block-on-cross-signal 运行时）
- **运行时实现**：lunaverse-backend `app/services/multiplayer-room-service.ts:696-755` — solo vs joint routing + `findJointChoiceEntry()` 查 manifest 决定阻塞 vs 直推
- **静态分析实现**：lunaverse-backend `app/core/checkpoints.ts` — 哪些 @choice 进 manifest
- **Handoff 源文档**：lunaverse-backend `docs/mp-cross-signal-author-guidance.md` (git commit db04fe75)
- **相关 wiki**：[[concepts/ls-format]]、[[concepts/signal-int-backend]]、[[concepts/stable-step-id]]、[[entities/lunascripts]]
