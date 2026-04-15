# MobAI ALL-IN-ONE 新人入门指南

读完这份文档，你应该能清楚说出：我们在做什么、游戏怎么玩、数值怎么运转、代码在哪里。

飞书文档看完整版，这里给你讲清楚最关键的东西。

---

## 目录

1. [为什么要做这件事](#一为什么要做这件事)
2. [先跟着玩一遍：新玩家的完整旅程](#二先跟着玩一遍新玩家的完整旅程)
3. [游戏设计详解](#三游戏设计详解)
   - 3.1 单集流程（Game → Plot）
   - 3.2 检定系统
   - 3.3 付费系统
   - 3.4 内容从哪里来：Dramatizer 洗文平台
   - 3.5 视频是怎么生成的：Agent-Forge 平台
   - 3.6 Remix 系统
   - 3.7 成就系统
   - 3.8 蝴蝶效应系统（过去的影响）
4. [数值速查表](#四数值速查表)
5. [项目信息与代码在哪里](#五项目信息与代码在哪里)
   - 核心服务列表
   - 代码结构
   - **本地跑游戏 Demo（新人必读）**

---

## 一、为什么要做这件事

> 飞书：[市场调研](https://xcn662409uz0.feishu.cn/wiki/UXC3wRhiWi9P2IkQY5jct1iAn4f) · [愿景与思考](https://xcn662409uz0.feishu.cn/wiki/QwkwmuCnQiZUKYkI78GchT33n5e) · [模态 MIX 思考](https://xcn662409uz0.feishu.cn/wiki/BgOnwVniXiNJCPknfiecaNMbnZe)

### 这个市场真实存在

互动剧情游戏（选项推剧情类）是一个真实的赛道。Episode、Chapters、Choices、MeChat，这几款产品年收入都在千万美金量级，用户主要是欧美年轻女性，用 Episode 举例，周流水约 $26 万，估算年收入 $1352 万。

但这些产品的体验极差，原因很集中。我们用 Gemini 分析了 Episode 在 Google Play 的 740 条评论，结论如下：

**最大的问题是宝石经济**（约 75% 的差评都在骂这个）：每章结尾只奖励 1 颗宝石，但选一个好选项要花 19-29 颗。没钱的玩家被迫在游戏里"穿破衣服去婚礼"、"拒绝心仪男生"——不是选不到最好的选项，而是免费选项本身带有惩罚性和羞辱感。

**第二个问题是供给成本太高**：传统剧本创作成本极高，平台跑了多年才累积 100 部内容，必须靠逼氪才能回本，头部公司枫叶互动至今还没盈利。

**我们的机会在哪里：**

- 消费侧：玩法比他们丰富（内嵌小游戏 + D20 检定 + 角色聊天），玩家自由度更高（AI 驱动）
- 供给侧：AI 洗稿大幅降低内容成本。洗稿的核心价值不是文字质量，而是从网文里提炼出来的**叙事节奏**，这是内容的灵魂

**我们的终极愿景是 AI 抖音 + AI 红果短剧**——用户打开 App 刷 Feed 流，找到想玩的，免费钩子拉进去，卡点付费或者换下一个，像刷抖音一样上瘾。从 PGC 平台做成 UGC 平台，形成规模效应。

---

## 二、先跟着玩一遍：新玩家的完整旅程

在看设计文档之前，先跟着走一遍游戏。这是最快理解我们在做什么的方式。

---

### 第一步：选小说，建角色

玩家进来，选一部洗好的网文（比如一部言情短剧《Marchetti 家族》）。

进入后要分配属性点。系统给你一个标准数组：**10 / 13 / 14 / 15**，加上 2 个额外的自由点，把这些数值分配到四个属性上：

| 属性 | 代码里叫什么 | 代表什么 |
|---|---|---|
| ATK（身手） | `combat` | 打架、体能、物理对抗 |
| INT（智识） | `intelligence` | 推理、解谜、信息分析 |
| CHA（魅力） | `charisma` | 说服、社交、感染力 |
| WIL（意志） | `will` | 心理抗压、耐力、承压 |

你可以把 15 放到 CHA，变成一个擅长社交的角色；也可以全压 combat，变成一个横冲直撞的打手。这个选择会影响你整个游戏的通过率。

---

### 第二步：开始第一集——先玩小游戏（Game 阶段）

进入第一集，系统先推给你一个**小游戏**。

这个小游戏不是随机的，它跟这集剧情将要发生的事情挂钩。比如这集你要正面刚男主，系统就推给你一个 ATK 类的小游戏——比如「QTE挑战」，限时点击屏幕上的序列；或者「打地鼠」，看谁反应快。

你玩完，系统给你一个评级：

- **S（完美）**：下次检定 +3，外加 +2 XP
- **A（优秀）**：下次检定 +1，外加 +1 XP
- **B（普通）**：检定没加成，+1 XP
- **C / D**：检定 -1，没有 XP

评级会被带进接下来的剧情检定里，玩得好就是给自己加 buff 备战，玩得烂就是给自己挂 debuff。

---

### 第三步：剧情来了——做出选择（Plot 阶段）

小游戏结束，进入剧情。一段 Intro 视频，镜头切进来，你看到了当前的情景。

然后出现了**两个选项**，你必须选一个：

> **[CHA] 冷冷地看着他，开口说："你以为你是谁？"**（勇敢选项，触发魅力检定）
>
> **低下头，沉默着走过去**（安全选项，跳过检定）

**选安全**：剧情平稳推进，你拿到 +1 XP，SAN 值不变，但剧情分支比较平淡。

**选勇敢**：系统在后台掷一颗 D20 骰子，然后算：

```
D20 骰子值（1-20随机） + 你的 CHA 修正值 + 小游戏的修正 ≥ DC（本集难度值）
```

如果你的 CHA 是 15，修正是 +2；小游戏拿了 A，修正是 +1；骰子投出了 13：
```
13 + 2 + 1 = 16 ≥ DC 11（铺垫期的典型难度）→ 成功
```

成功了，+3 XP，SAN +5，剧情走精彩分支，NPC 被你怼得哑口无言。

---

### 第四步：检定失败了，然后呢？

假设骰子只投出了 3：
```
3 + 2 + 1 = 6 < DC 11 → 失败
```

屏幕上弹出来：**"检定失败（6/11）！只差 5 点！"**

SAN 值 -20（SAN 从 100 开始，最多承受 5 次失败就归零）。你拿到 +1 XP。

然后系统问你：**要不要花 30 Gems 重投骰子？**

这就是核心的付费点。骰子差一点点的时候，30 Gems（约 $0.30）重投一次非常诱人——沉没成本加上再来一次的冲动，绝大多数玩家都会考虑。

重投成功的话，结果替换为成功，XP +3，SAN +5；重投还是失败，XP +1，SAN -20。

---

### 第五步：SAN 归零之后

你连续失败了 5 次，SAN 归零，角色进入昏迷/死亡结局。

系统给你三个选择：

- **重开**：免费，但从头来
- **复活到上一个关键存档点（Key Plot）**：花 100 Gems
- **立即原地复活**：花 500 Gems，所有状态回满

---

### 第六步：60 集打完了，成长了什么？

每集你都在积累 XP，XP 用来升级，每次升级给你一个属性点自由分配。

普通玩家（F2P，不氪金）在打完 55-56 集的时候会升到 19 级，属性变得越来越强。同样是 DC 17 的高潮期检定，1 级时通过率可能只有 30%，19 级的专精玩家通过率能到 71%。

这就是养成的核心感——随着游戏进行，你越来越强，高难度的剧情越来越有把握去挑战，而不是一直在乞求骰子。

---

### 第七步：Remix Tab——这里是二创广场

玩完剧情，玩家还可以切到 **Remix Tab**。

这是一个完全独立的 Feed 流，专门放玩家的二创内容，和主线剧情的 Classic Tab 分开放。里面有：

- **改剧情**：在任意剧情节点输入你自己的指令，替换预置的选项。比如在男主准备跟你告白的场景，你输入"我掏出手机问他有没有吃饭"，系统判定是什么检定，你去骰子，骰过了就生成一段这个脑洞的剧情文字。如果你愿意花胶卷，还能生成对应的图片或视频。
- **改角色卡（CCR）**：把剧里的角色卡拿出来，改人设、改记忆、改立绘，然后直接和这个改过的角色实时聊天。聊到精彩的地方截图发出去，别人扫截图里的二维码可以直接和这张角色卡对话。

Remix 的设计哲学：官方做的是 60 分的精品内容，但成本极低；玩家的创意能让内容上到 80 分，形成规模效应。这是我们跟所有竞品本质上不同的地方。

---

## 三、游戏设计详解

> 飞书：[游戏主体 PRD v2（最新版）](https://xcn662409uz0.feishu.cn/wiki/OdghwzlysijBy6k4cyTcU1SCnsc) · [REMIX 玩法 PRD](https://xcn662409uz0.feishu.cn/wiki/EhYcwnP7aipDqTkzlW2cuyAnnzg) · [成就系统 PRD](https://xcn662409uz0.feishu.cn/wiki/OTsswKQJPio3fJkBJjUc8WUBn5d) · [CCR 角色卡 PRD](https://xcn662409uz0.feishu.cn/wiki/TojswXxzYirIGOk9c3Rc82hTn4f)

### 3.1 单集流程

每集约 130 秒（2.2 分钟），分为两个阶段，代码里叫 `GamePhase = "GAME" | "PLOT"`：

```
GAME（小游戏，40s）→ PLOT（剧情+选择+结算，90s）→ 下一集 GAME ...
```

**GAME 阶段**：系统根据下一集要检定的属性，推对应类型的小游戏。目前共有 **50 个 H5 小游戏**，全都是独立的 `index.html`，通过 WebView 内嵌在 Cocos 游戏里。

按属性分类：

| 属性 | 数量 | 代表游戏 |
|---|---|---|
| ATK（combat） | 16 个 | QTE挑战、Boss格挡、打地鼠、变道冲刺、守门员、闪避流星... |
| INT（intelligence） | 21 个 | 拆弹专家、密码破解、迷宫逃脱、记忆翻牌、速算挑战... |
| WIL（will） | 11 个 | 30秒生存、平衡木、钓鱼、节拍维持、轨道闪避... |
| CHA（charisma） | 2 个 | 下落节奏、老虎机 |

CHA 类小游戏目前只有 2 个，是待补充的方向。

**PLOT 阶段**内部的状态机流转（`PlotFlowPhase`）：

```
NARRATIVE_LOADING（加载剧情）
  → SHOWING_OPTIONS（展示两个选项）
  → CHECK_ROLLING（D20骰子动画）
  → SETTLEMENT（结算 XP、SAN、升级）
  → 下一集
```

---

### 3.2 检定系统

公式就一行：

```
D20（1-20）+ 属性修正 + 小游戏修正 ≥ DC → 成功
```

- **属性修正** = `floor((min(属性值, 24) - 10) / 2)`，属性 15 就是 +2，属性 18 就是 +4
- **小游戏修正**：S=+3，A=+1，B=0，C=-1，D=-1
- **DC（难度值）**：每集一个，按叙事阶段采样，所有玩家共用同一序列（seed=42）

DC 按剧情阶段走：

| 阶段 | 集数 | DC 均值 | DC 范围 |
|---|---|---|---|
| 开篇 | Ep 1–6 | 10 | 8–12 |
| 铺垫 | Ep 7–20 | 11 | 8–13 |
| 转折 | Ep 21–35 | 14 | 11–16 |
| 高潮 | Ep 36–55 | 17 | 15–20 |
| 结局 | Ep 56–60 | 12 | 10–14 |

高潮期（Ep 36-55）是整部游戏最硬的阶段，DC 均值 17，Reroll 消费也在这里最集中。

---

### 3.3 付费系统

**Gems（钻石）** 是硬通货，充值获取。主要用途：

| 用途 | 花费 |
|---|---|
| Reroll 重投骰子 | 30 Gems（$0.30） |
| 理智崩溃恢复 | 50 Gems |
| 复活到上一存档点 | 100 Gems |
| 立即原地复活 | 500 Gems |
| 小游戏跳过（直接S） | 50 Gems |

**充值档位：**

| 档位 | Gems | 价格 |
|---|---|---|
| 入门包 | 100 | $0.99 |
| 价值包 | 550 | $4.99 |
| 超值包 | 1200 | $9.99 |
| 鲸鱼包 | 2800 | $19.99 |

**Coins（金币）** 是软通货，代表体力。每集消耗 10 Coins，每日免费 400 Coins（签到 200 + 时间恢复 200），等于每天免费玩 40 集、约 87 分钟。

---

### 3.4 内容从哪里来：Dramatizer 洗文平台

> 仓库：[AugustZAD/Dramatizer](https://github.com/AugustZAD/Dramatizer) · 访问地址：http://47.98.225.71:38188/

一部网文少则几百章，多则上千章。我们不可能手动改编，全靠 Dramatizer 来做。

它做一件事：**把一部长篇小说自动变成 60 集互动短剧的完整剧本**，含分支选项和属性检定点。

整个流程是三个阶段的流水线：

**Phase 1：素材提取**（把原著读懂）

| 步骤 | 干了什么 |
|---|---|
| skeleton | 全书抽样扫描，抽出主角、配角、主要关系 |
| extract | 逐章并发提取关键场景（默认 10 章并发） |
| resolve | 把不同章节里的同一个人名统一归一（比如"陆总"和"陆沉"是同一个人） |
| bible | 生成这部剧的"Show Bible"——角色弧线、情感走向、剧情纲要 |
| judge | 给每个场景打分：KEEP / DELETE / NEEDS_REVIEW，决定哪些进最终剧本 |

**Phase 2：剧本生成**（把素材变成剧本）

- **refine-map**：设计 60 集的集级大纲，每集对应哪些场景、在哪个叙事阶段
- **refine-write**：按大纲逐集生成完整短剧剧本。用"黄金五段式"——把所有场景按 20% 切为 5 批，每批 25% 重叠，保证前后剧情连贯不跳跃

**Phase 3：互动化**（把剧本变成游戏节点）

- **ludify-map**：规划每集的分支点在哪里（哪里放勇敢/安全选项，哪里触发检定）
- **ludify-generate**：生成含选择点的互动剧本
- **ludify-generate-growth**：扩展角色心理成长路线（属性检定对应的内心变化）
- **ludify-fusion**：把以上三个结果合并，输出游戏引擎可以直接读取的数据格式

**技术栈**：Node.js + TypeScript + Koa，LLM 走 ZenMux（默认 GLM-5，支持 Claude/DeepSeek/Gemini 切换），任务队列用 BullMQ + Redis，数据库 PostgreSQL，前端 React + Vite。

**怎么用**：打开 http://47.98.225.71:38188/，上传小说文本，选模型，点开始，等流水线跑完。各阶段进度实时显示，每个 Phase 产出的中间结果都可以单独查看和手动干预。

---

### 3.5 视频是怎么生成的：Agent-Forge 平台

> 仓库：[Rydia-China/Agent-Forge](https://github.com/Rydia-China/Agent-Forge) · 访问地址：https://agent.mob-ai.cn · 视频模块：https://agent.mob-ai.cn/video

游戏里的 intro/outro 视频，以及 Remix 花胶卷生成的图片和视频，都经过这个平台。

**它是什么**：一个以 MCP 协议为核心的 Agent 后台，对外暴露为标准 MCP Server（`POST /mcp`，端口 8001），内部跑着一套小说转视频的工作流。

**当前主要模块** (`src/app/video/`)：小说转视频工作流。流程大致是：
1. 输入剧情文本或分镜描述
2. 调 Gemini 生成角色/场景图片（用 Nano Banana Pro）
3. 调即梦（Jimeng）生成视频片段
4. 拼合、加 TTS 配音、输出成品

**两个核心云函数**（部署在阿里云 FC）：
- `generate-image`：调 Gemini 生成图片
- `generate-video`：调即梦 Jimeng 生成视频

**怎么用**：打开 https://agent.mob-ai.cn/video，输入剧情内容和风格描述，系统自动走工作流。支持通过 chatbot 交互式调整（可以说"换一个更暗的色调"、"让角色站在左边"这类指令）。生成过程中可以看到每一步的中间产物（角色图、分镜图、成品视频）。

---

### 3.6 Remix 系统

> 完整 PRD：[REMIX 玩法 PRD](https://xcn662409uz0.feishu.cn/wiki/EhYcwnP7aipDqTkzlW2cuyAnnzg)

**为什么要有 Remix，以及为什么要单独放一个 Tab？**

玩梗、恶搞、脑洞大开的 UGC 内容，跟高质量正经叙事的内容完全是两种调性，混在一个 Feed 里会互相伤害。解法就是做两个 Feed，分开放——Classic Tab 是主线正剧，Remix Tab 是二创广场。

```
┌────────────┬──────────────┬────────────┐
│  Classic   │   Remix ✨   │   Profile  │
│  （主线）   │  （二创广场） │   （个人）  │
└────────────┴──────────────┴────────────┘
```

**Remix 怎么玩：**

在任意 Plot 节点，玩家可以不选预置选项，而是输入自己的指令。比如在反派冗长演说的场景里，输入"我掏出手机给他点了一份外卖"。

后台的 Remix 管线（三阶段）：
1. **Planner**：LLM 评估这个操作影响几集，生成即时的 50 字文字反馈
2. **Script**：基于大纲生成完整剧情长文
3. **Executor**：把长文转成游戏引擎可以渲染的 JSON 节点树

文字结果是免费的。玩家如果想要图片或视频，花胶卷解锁：
- 单节点图片：6 胶卷（≈60 Gems）
- 单节点视频：20 胶卷（≈200 Gems）

**CCR 角色卡 Remix** 是 Remix 的一个子功能：把剧里的角色卡单独拿出来，改人设/记忆/立绘，然后直接和改过的角色实时聊天。聊天截图是核心传播格式，截图底部内嵌二维码，别人扫码直接跳进和这张卡对话。成本极低（约 $0.001-0.003/条消息），但用户停留时长最长。

---

### 3.7 成就系统

> 完整 PRD：[成就系统 PRD](https://xcn662409uz0.feishu.cn/wiki/OTsswKQJPio3fJkBJjUc8WUBn5d)

成就不是普通的进度记录，是**社交货币的产出地**。分三类：

**第一类：通用机制成就**（策划 hardcode，跨所有剧本）

围绕游戏的核心循环，作为情绪保底：
- 【六边形战士】：Game 小游戏连续 5 次 S 评级
- 【西西弗斯的挣扎】：同一节点连续买 5 次 Reroll 还是失败
- 【命悬一线】：SAN 降至 1 点时，惊险通过下一次生死检定

**第二类：预置剧情成就**（每部剧上线前，AI 自动生成）

新剧上线前，成就生成 Agent 自动读剧本、提取关键节点、预置成就表。这是我们能扩展到几百部剧的前提。

**第三类：Remix 实时衍生成就**（AI 动态生成，最有意思的部分）

玩家输入足够有趣/荒诞的 Remix 指令时，AI 实时生成一个独一无二的成就，并把触发规则沉淀到成就库里——后来的玩家输入语义相似的操作，能触发同一个成就。

例子：玩家 A 在枪战场景输入"我掏出手机点了麦当劳疯狂星期四"，AI 生成成就【V我50：枪战不如吃鸡】。后来玩家 B 输入"我问杀手要不要一起吃披萨"，命中规则，同款成就解锁。

### 3.8 蝴蝶效应系统（过去的影响）

> 代码入口：`plot-generator.ts` → `branch-evaluator.ts` → `fate-narrator.ts`

蝴蝶效应是这个游戏最有"养成感"的系统。你在第 3 集做的一个选择，可能在第 40 集把你送上一条完全不同的路线。

#### 它是什么

每当你在剧情节点做了选择并且通过/失败了检定，系统会根据这个结果生成一条"过去的影响"（PastInfluence），挂在你的存档上。

一条影响长这样：

```typescript
{
  type: "good" | "bad",        // 正面还是负面
  description: "在悬崖边救了师妹", // 结构化描述（剧本预埋）
  nodeIndex: 12,                // 来自第几个叙事节点
  narrativeText: "悬崖之上的抉择", // LLM 生成的 6-10 字叙事短语
  chapterLabel: "第13章的回响"    // 章节标签
}
```

注意 `description` 是剧本里预埋的——Dramatizer 洗文的时候，每个关键节点的 outcome 里都会写好 `butterflyEffect` 字段。不是运行时瞎编的，是有内容设计的。

#### 它怎么影响游戏

**影响一：分支路由（最核心的作用）**

游戏里的分支有三种准入条件：

| 条件类型 | 怎么判断 | 例子 |
|---|---|---|
| NUMERIC（硬条件） | 直接比属性值 | `combat >= 18` |
| CHOICE（选择记录） | 查你在特定节点选了哪个选项 | 节点 #5 选了选项 2 |
| INFLUENCE（软条件） | **LLM 读你所有的过去影响，判断是否满足一段自然语言描述** | "玩家展现过对弱者的同情" |

INFLUENCE 条件是最有意思的。它不是死板的标签匹配——不是检查你有没有 `tag:善良`。它把你所有的过去影响（带描述文本）喂给 LLM，问它：这个玩家的经历，是否满足"展现过对弱者的同情"这个条件？

LLM 会综合判断。你在第 3 集救了师妹、第 15 集放走了乞丐、第 22 集把药留给了伤兵——这些合在一起，够不够"同情弱者"？LLM 说够，这条分支就对你开放。

**影响二：DC 修正**

剧情生成的时候，系统会把你的过去影响列表注入 prompt。好的影响多的玩家，在相关场景里可能获得更有利的叙事展开。这部分目前还比较隐性，但管线已经搭好。

#### 命运日记

所有影响积累到一定程度后，`fate-narrator.ts` 里的 `generateFateSummary()` 会把它们合成一段**主角视角的第一人称日记**——3-5 句话，概括你这一路走来的命运轨迹。

这不是给玩家看的花哨 UI，是一个内容资产：它可以展示在结局画面、分享卡片、或者作为 Remix 的输入上下文。

#### 为什么这么设计（这是最关键的部分）

表面上看，蝴蝶效应就是"过去选择影响未来"，很多游戏都做了。但我们的设计有一个超前考量：

**问题：** 如果未来有几百部剧，每部剧又有大量 Remix 分支，你怎么做跨剧本的内容路由？

传统方案是打标签——`善良`、`冷酷`、`武力派`。但标签是有限的、僵硬的，覆盖不了无限的 Remix 创意。

我们的方案：每条过去影响都带着 `description`（结构化语义描述）和 `narrativeText`（LLM 叙事化文本）。这些不是标签，是**带有完整语义的内容钩子**。

它们天然适合做向量化。把所有玩家的影响做 embedding，Remix 的分支条件也做 embedding，两边一算相似度——就能在海量分支中精准找到"适合这个玩家经历"的内容。不需要预定义任何标签体系，也不需要人工维护映射关系。

现在这个能力还没上线，但管线从数据结构到 LLM 叙事化已经全部就位。当 Remix 内容多到一定量级的时候，这套东西就是检索和路由的基础设施。

---

## 四、数值速查表

> 完整文档：[数值系统设计报告 v7.1](https://xcn662409uz0.feishu.cn/wiki/MMmQwoyMmidqQ6kVHt5cgnEQndM)（已通过 20,000 次蒙特卡洛验证）

### 属性修正速查

| 属性值 | 修正 | 属性值 | 修正 |
|---|---|---|---|
| 10–11 | +0 | 18–19 | +4 |
| 12–13 | +1 | 20–21 | +5 |
| 14–15 | +2 | 22–23 | +6 |
| 16–17 | +3 | 24（上限） | +7 |

### 一集能拿多少 XP

| 情况 | XP |
|---|---|
| 选勇敢 + 成功 | +3 |
| 选勇敢 + 失败 | +1 |
| 选安全（不检定） | +1 |
| 小游戏 S | 额外 +2 |
| 小游戏 A 或 B | 额外 +1 |

→ 普通玩家每集期望约 **2.7 XP**，打完 56 集左右升到 19 级（满级体验）。

### 关键升级里程碑

| 等级 | 累计 XP | F2P 大约在第几集 |
|---|---|---|
| LV 5 | 28 | Ep 9（铺垫期开始） |
| LV 10 | 74 | Ep 25（转折期） |
| LV 15 | 117 | Ep 42（高潮期） |
| **LV 19** | **149** | **Ep 56（结局期）** |
| LV 20 | 156 | Ep 62（超出60集，买不到） |

### Build 一眼看懂

| 玩法 | 属性分配（14点） | 强项修正 | 适合谁 |
|---|---|---|---|
| 极端专精 | 8 / 3 / 2 / 1 | +7 | 接受大量 Reroll，追求某一属性的极致 |
| 双修 | 6 / 6 / 1 / 1 | +6 | 两个属性稳健，弱项直接选安全 |
| 均衡 | 4 / 4 / 3 / 3 | +5 | 每集都敢冒险，但天花板低 |

### 高潮期的 Reroll 消费参考

高潮期 DC 均值 17，是整部游戏 Reroll 消费最集中的阶段：

| 玩家类型 | Reroll 次数 | 花费 Gems | 约合美元 |
|---|---|---|---|
| 重氪（均衡 Build） | ~13 次 | ~398 G | ~$3.94 |
| 重氪（专精 Build） | ~12 次 | ~355 G | $3.52 |
| 中氪（专精） | ~6 次 | ~181 G | $1.79 |
| 微氪（均衡） | ~3 次 | ~83 G | $0.82 |

---

## 五、项目信息与代码在哪里

> 飞书：[新人入门指引导航帖](https://xcn662409uz0.feishu.cn/wiki/WRyzw1Whei2ipsk7QZGcQyDjn5b)

### 核心服务

| 服务 | 地址 | 仓库 |
|---|---|---|
| 游戏（Cocos H5） | http://47.254.93.15/ | [Rydia-China/moonshort](https://github.com/Rydia-China/moonshort) |
| 游戏后台 | http://47.254.93.15/admin/123456 | [Rydia-China/noval.demo.2](https://github.com/Rydia-China/noval.demo.2) |
| 健康检查 | http://47.254.93.15/api/health | — |
| 通用后台（含视频） | https://agent.mob-ai.cn | [Rydia-China/Agent-Forge](https://github.com/Rydia-China/Agent-Forge) |
| Dramatizer 洗文后台 | http://47.98.225.71:38188/ | [AugustZAD/Dramatizer](https://github.com/AugustZAD/Dramatizer/) |
| Prompt 管理（Langfuse） | https://prompt.mobai-game.com/ | — |
| 角色卡 RAG 接口 | http://47.98.225.71:8092/docs | [cdotlock/character-card-rag](https://github.com/cdotlock/character-card-rag) |

所有服务均在 **47.254.93.15** 或 **47.98.225.71** 上用 Docker Compose 管理。

### 代码结构（后端）

后端是 **Next.js + Prisma + PostgreSQL**，关键文件在 `backend/app/lib/`：

| 文件 | 是什么 |
|---|---|
| `numerical-system.ts` | 所有数值常量和公式，唯一数值来源 |
| `game-state-machine.ts` | GAME/PLOT 两阶段状态机的类型定义 |
| `game-engine.ts` | XP、升级、SAN、Gems 的结算计算 |
| `minigame-registry.ts` | 50 个小游戏的注册表，按属性分类 |
| `remix/dc-checker.ts` | Remix 的 D20 检定，LLM 动态判定 |
| `remix/pipeline.ts` | Remix 三阶段管线（Planner/Script/Executor） |
| `achievement/` | 成就三类体系的各自实现 |

小游戏代码在独立仓库 `moonshort-minigame-skill`，每个游戏是一个 `games/<id>/index.html`，通过 WebView 桥接协议和 Cocos 游戏通信。

### 团队成员

| 成员 | 邮箱 |
|---|---|
| Rydia | 1992155807@qq.com |
| Vito | 853583725@qq.com |
| Kaito | mlrswang9229@gmail.com |
| August | s98081096@gmail.com |
| mubobeibei | mubobeibei@gmail.com |
| Eureka | eruekakakayzha@gmail.com |

### 所有飞书文档

| 文档 | 链接 |
|---|---|
| 新人入门导航帖 | [打开](https://xcn662409uz0.feishu.cn/wiki/WRyzw1Whei2ipsk7QZGcQyDjn5b) |
| 市场调研 | [打开](https://xcn662409uz0.feishu.cn/wiki/UXC3wRhiWi9P2IkQY5jct1iAn4f) |
| 愿景与思考 | [打开](https://xcn662409uz0.feishu.cn/wiki/QwkwmuCnQiZUKYkI78GchT33n5e) |
| 模态 MIX 思考 | [打开](https://xcn662409uz0.feishu.cn/wiki/BgOnwVniXiNJCPknfiecaNMbnZe) |
| Remix & 创作者平台调研 | [打开](https://xcn662409uz0.feishu.cn/wiki/EfOSwnJ4Xi0mS6krCgYcQ7BtnTg) |
| 游戏主体 PRD v2（最新版） | [打开](https://xcn662409uz0.feishu.cn/wiki/OdghwzlysijBy6k4cyTcU1SCnsc) |
| REMIX 玩法框架 PRD | [打开](https://xcn662409uz0.feishu.cn/wiki/EhYcwnP7aipDqTkzlW2cuyAnnzg) |
| 成就系统 PRD | [打开](https://xcn662409uz0.feishu.cn/wiki/OTsswKQJPio3fJkBJjUc8WUBn5d) |
| CCR 角色卡 Remix PRD | [打开](https://xcn662409uz0.feishu.cn/wiki/TojswXxzYirIGOk9c3Rc82hTn4f) |
| 数值系统设计报告 v7.1 | [打开](https://xcn662409uz0.feishu.cn/wiki/MMmQwoyMmidqQ6kVHt5cgnEQndM) |

---

### 本地跑游戏 Demo

> 仓库：[Rydia-China/noval.demo.2](https://github.com/Rydia-China/noval.demo.2)

游戏 Demo 是 Next.js + Prisma (PostgreSQL) + WebSocket。本地跑起来只需要两步。

**第一步：克隆仓库，装依赖**

```bash
git clone https://github.com/Rydia-China/noval.demo.2.git
cd noval.demo.2
pnpm install
```

**第二步：启动数据库（Docker）**

项目提供了 `docker-compose.dev.yml`，里面只有 PostgreSQL 和 Redis，不需要装本地数据库：

```bash
docker compose -f docker-compose.dev.yml up -d
```

**第三步：配置环境变量**

复制 `.env.example` 为 `.env`，关键字段填好：

```
DATABASE_URL="postgresql://postgres:password@localhost:5432/moonshort"
NEXTAUTH_URL="http://localhost:3000"
NEXTAUTH_SECRET="随便填一个字符串"

# LLM（必填，走 ZenMux）
ZENMUX_BASE_URL="..."
ZENMUX_API_KEY="..."

# Prompt 管理（Langfuse）
LANGFUSE_PUBLIC_KEY="..."
LANGFUSE_SECRET_KEY="..."
LANGFUSE_BASE_URL="https://prompt.mobai-game.com"
```

LLM 和 Langfuse 的 key 问 Rydia 或 Kaito 要，不要自己去注册。

**第四步：初始化数据库，跑起来**

```bash
pnpm dlx prisma migrate dev   # 跑数据库迁移
pnpm dlx prisma db seed       # 导入初始数据（小说节点等）
pnpm dev                       # 启动开发服务器
```

打开 http://localhost:3000 就能看到游戏。

**生产部署**用 `docker-compose.prod.yml`，包含 app（Next.js standalone）+ db + nginx 三个服务，环境变量比开发环境多了 Stripe 支付、火山引擎 TTS、阿里云 OSS 等配置，部署前找 Rydia 对齐。

---

*文档基于代码（`numerical-system.ts` v7.1、`minigame-registry.ts` 50个游戏）及 PRD 原文整理，2026-04。以飞书原文为准。*
