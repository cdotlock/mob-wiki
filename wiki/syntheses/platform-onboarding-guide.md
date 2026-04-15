---
title: MobAI 平台全景指南
tags: [onboarding, platform, game-design, architecture]
sources: [raw/2026-04-15-platform-onboarding-guide.md]
created: 2026-04-15
updated: 2026-04-15
---

MobAI 是一个 AI 驱动的互动剧情游戏平台，对标抖音 + 红果短剧。本文从玩家视角走一遍完整体验，然后拆解游戏设计、数值系统和技术架构。读完应该能说清楚：产品在做什么、游戏怎么玩、数值怎么转、代码在哪里。

战略决策背景见 [[syntheses/product-strategy-decisions]]。

## 市场机会

互动剧情游戏（选项推剧情类）是一个真实赛道。Episode、Chapters、Choices、MeChat 年收入都在千万美金量级，用户主要是欧美年轻女性。Episode 周流水约 $26 万，年收入估算 $1352 万。

竞品体验极差的原因：宝石经济惩罚免费玩家（75% 差评在骂这个），供给成本太高（头部公司枫叶互动至今没盈利）。

MobAI 的机会：
- **消费侧**：玩法更丰富（小游戏 + D20 检定 + 角色聊天），AI 驱动的玩家自由度
- **供给侧**：AI 洗稿大幅降低内容成本，从网文里提炼叙事节奏

## 玩家完整旅程

### 第一步：选小说，建角色

玩家选一部 AI 洗好的网文。进入后分配属性点——标准数组 10/13/14/15 + 2 自由点，分配到四个属性：

| 属性 | 代码名 | 代表 |
|------|--------|------|
| ATK（身手） | `combat` | 打架、体能、物理对抗 |
| INT（智识） | `intelligence` | 推理、解谜、信息分析 |
| CHA（魅力） | `charisma` | 说服、社交、感染力 |
| WIL（意志） | `will` | 心理抗压、耐力 |

### 第二步：小游戏备战

每集开始推一个小游戏，和本集检定属性挂钩。目前共 50 个 H5 小游戏（ATK 16 个、INT 21 个、WIL 11 个、CHA 2 个），通过 WebView 嵌入。

评级影响后续检定：S = +3 修正 +2 XP、A = +1 修正 +1 XP、B = +0 修正 +1 XP、C/D = -1 修正 +0 XP。

**新版变化**：小游戏嵌入视觉小说阅读流内部（不再是独立阶段），脚本通过 `@minigame` 指令触发。见 [[concepts/mss-format]]。

### 第三步：剧情选择 + D20 检定

剧情出现两个选项：

> **[CHA] "冷冷地看着他"**（勇敢选项，触发魅力检定）
> **"低下头走过去"**（安全选项，跳过检定）

选安全：+1 XP，SAN 不变，剧情平淡。

选勇敢：D20 检定。公式：`D20(1-20) + 属性修正 + 小游戏修正 >= DC → 成功`

属性修正 = `floor((min(属性值, 24) - 10) / 2)`。属性 15 = +2，属性 18 = +4。

成功：+3 XP、SAN +5、精彩分支。失败：+1 XP、SAN -20。

### 第四步：失败后的付费点

"检定失败（6/11），只差 5 点！要不要花 30 Gems 重投？"

这是核心付费点。沉没成本 + 再来一次的冲动。重投成功则替换为成功结果。

### 第五步：SAN 归零

连续失败 5 次 SAN 归零，进入昏迷/死亡结局。三个选择：重开（免费）、复活到上一存档点（100 Gems）、立即原地复活（500 Gems）。

### 第六步：60 集完成后的成长

普通玩家（F2P）打完 55-56 集升到 19 级。属性越来越强，高难度检定通过率从 30% → 71%。

## 付费系统

**Gems（钻石）**：硬通货，充值获取。

| 用途 | 花费 |
|------|------|
| Reroll 重投 | 30 Gems（$0.30） |
| 理智崩溃恢复 | 50 Gems |
| 复活到上一存档点 | 100 Gems |
| 立即原地复活 | 500 Gems |
| 小游戏跳过（直接 S） | 50 Gems |

充值档位：100 Gems/$0.99、550/$4.99、1200/$9.99、2800/$19.99。

**Coins（金币）**：软通货（体力）。每集消耗 10 Coins，每日免费 400 Coins = 40 集/天约 87 分钟。

## DC 难度曲线

| 阶段 | 集数 | DC 均值 | DC 范围 |
|------|------|---------|---------|
| 开篇 | 1-6 | 10 | 8-12 |
| 铺垫 | 7-20 | 11 | 8-13 |
| 转折 | 21-35 | 14 | 11-16 |
| 高潮 | 36-55 | 17 | 15-20 |
| 结局 | 56-60 | 12 | 10-14 |

高潮期（36-55）是 Reroll 消费最集中的阶段。

## 内容生产管线

### Dramatizer（剧本生产）

把一部长篇小说自动变成 60 集互动短剧剧本。三阶段流水线：

**Phase 1 素材提取**：skeleton（抽主角配角）→ extract（逐章提取场景）→ resolve（人名归一）→ bible（Show Bible）→ judge（场景评分 KEEP/DELETE）

**Phase 2 剧本生成**：refine-map（60 集大纲）→ refine-write（逐集完整剧本）

**Phase 3 互动化**：ludify 系列（分支点规划、互动剧本生成、角色成长路线、最终合并）

输出格式为 MSS（MoonShort Script），见 [[concepts/mss-format]]。解释器见 [[entities/moonshort-script]]。

详细架构见 [[entities/dramatizer]]。

### Agent-Forge（素材生产）

以 MCP 协议为核心的 Agent 后台，负责素材生成工作流：角色立绘（LoRA + Inpainting）、背景图、CG 短视频、idle 动画。

核心云函数：generate-image（调 Gemini）、generate-video（调即梦 Jimeng）。

详细架构见 [[entities/agent-forge]]。

## Remix 系统

在任意剧情节点，玩家可以不选预置选项，输入自己的指令。后台三阶段管线：

1. **Planner**：评估操作影响几集，生成即时文字反馈
2. **Script**：基于大纲生成完整剧情长文
3. **Executor**：转成游戏引擎可渲染的 MSS 格式

文字免费。图片 6 胶卷（≈60 Gems），视频 20 胶卷（≈200 Gems）。

**CCR 角色卡 Remix**：把角色卡拿出来改人设/记忆/立绘，实时聊天。截图是核心传播格式（底部内嵌二维码）。成本 $0.001-0.003/条消息。

## 成就系统

三类：

| 类型 | 说明 | 生成方式 |
|------|------|---------|
| Type 1 通用机制 | 跨剧本游戏行为（连续 S 评级、连续 Reroll 失败等） | 策划 hardcode |
| Type 2 预置剧情 | 每部剧上线前自动生成 | AI 读剧本提取 |
| Type 3 Remix 实时 | 玩家输入足够有趣的 Remix 指令时动态生成 | AI 实时生成 + 规则沉淀 |

## 蝴蝶效应系统

每次选择生成一条 PastInfluence 记录（type: good/bad、description、narrativeText）。影响方式：

1. **分支路由**：三种准入条件——NUMERIC（属性值）、CHOICE（选择记录）、INFLUENCE（LLM 读所有影响判断是否满足自然语言条件）
2. **DC 修正**：好的影响多的玩家在相关场景获得更有利展开
3. **命运日记**：影响积累后合成主角视角的第一人称日记

INFLUENCE 条件是最有意思的——不是标签匹配，是把所有影响描述喂给 LLM 问"是否满足这个条件"。MSS 脚本中通过 `@butterfly` 记录、`@gate type: influence` 判定。

## 技术架构

### 核心服务

| 服务 | 技术栈 | 说明 |
|------|--------|------|
| [[entities/moonshort-backend]] | Next.js + Prisma + PostgreSQL | 游戏后端（API、Remix 管线、成就系统） |
| [[entities/moonshort-client]] | Cocos Creator H5 | 游戏前端 |
| [[entities/dramatizer]] | Go 单二进制 | 剧本生产（15 阶段 LLM 管线） |
| [[entities/agent-forge]] | Next.js + MCP | 素材生产（Agent 平台） |
| [[entities/moonshort-script]] | Go 单二进制 | MSS 脚本解释器 |
| [[entities/mobai-agent]] | Node.js | Master Agent 调度器 |

### 后端关键文件

| 文件 | 职责 |
|------|------|
| `numerical-system.ts` | 所有数值常量和公式 |
| `game-state-machine.ts` | GAME/PLOT 两阶段状态机 |
| `game-engine.ts` | XP、升级、SAN、Gems 结算 |
| `minigame-registry.ts` | 50 个小游戏注册表 |
| `remix/pipeline.ts` | Remix 三阶段管线 |
| `achievement/` | 成就三类体系实现 |

### 数值速查

属性修正：10-11 = +0、12-13 = +1、14-15 = +2、16-17 = +3、18-19 = +4、20-21 = +5、22-23 = +6、24(上限) = +7。

每集 XP：勇敢成功 +3、勇敢失败 +1、安全 +1、小游戏 S 额外 +2、A/B 额外 +1。普通玩家每集期望约 2.7 XP，56 集左右升到 19 级。

## 新版视觉形态

产品形态已从视频驱动的互动短剧转向 **Unfolded 风格互动视觉小说**：

- 竖屏全屏阅读，点击推进
- 整屏背景图 + 放大角色 cutout + 悬浮式文本容器
- 5 种叙事容器：对白、旁白、内心独白、短信、选择
- D20 检定和小游戏机制保留，嵌入阅读流
- 脚本格式统一为 MSS（[[concepts/mss-format]]）

视觉资产管线：LoRA 训练 → 表情 Inpainting → LivePortrait idle 动画 → 背景生成 → CG 短视频。每部小说 $36-137（vs 传统 $15K-84K）。
