---
title: 乙女小说写作 Benchmark 调研 + 自建指标草案（2026-06-04）
updated: 2026-06-04
tags: [benchmark, evaluation, otome, llm-as-judge, model-selection]
---

# 乙女小说写作 Benchmark 调研 + 自建指标草案

> 来源：2026-06-04 deep-research（109 agent / 660+ 工具调用 / 127 论断抽 25 条 3 票对抗核查，21 confirmed）+ 一轮定向补搜（IF / 视觉小说 / 角色扮演专用 benchmark）。
> 目的三重：(1) 选底座模型、(2) 测我们自己的乙女剧情产出、(3) 借鉴评分维度。语言以英文资源为主。

## TL;DR

- **成熟的"小说 / 创意写作 benchmark"有一批且活跃维护；专门"适合乙女"（互动 + 恋爱 + 分支）的——一个都没有。**
- **选模型**：现成唯一活榜单是 **EQ-Bench Creative Writing v3**（榜首 Grok-4.1 Thinking，Qwen3-235B 系列很高）。
- **测产出 / 方法论**：四套开源 LLM-as-judge 可直接搬——**HelloEval**（加权 yes/no checklist，最适合做逐场景质量门）、**RMTBench**（唯一多轮角色扮演）、**ConStory-Checker**（长剧本一致性回归）、**RPGBench**（客观校验游戏机制 / 变量更新）。
- **缺口（修正版）**：
  - 分支机制正确性（好感度变量更新、门槛触发、路线一致）→ **不再是空白**，RPGBench 的客观校验 + StoryBench 的记忆评测可借 harness。
  - **恋爱弧推进 + 男主魅力 + 路线级浪漫兑现 → 真空白，必须原创。** 这是唯一需要从零造的层。
- **结论**：自建乙女 benchmark = 复用现成 harness/维度 + 只原创"恋爱/魅力"层；不用从零。

## 两层框架：① 测模型 vs ② 测作品

容易混的一点：**benchmark（榜单）测的是模型，不是某一篇剧本的质量。** 自建拆成两层，按需求各取：

- **① Benchmark（榜单）= 测模型**：固定题集 → N 个模型各写一遍 → 排名。选底座用。
- **② Evaluator（评分器）= 测作品**：拿一篇**已写好**的剧本 → 打分 → 质量报告。**source-agnostic**，不挑来源（模型生成 / 手写 / pipeline 产出都行）。**QA / 回归 / 质量门用，这才是"测这个剧本好不好"。**

榜单内部本就是"先逐篇打分(②) 再按模型聚合排名(①)"，所以 ② 的评分核心埋在每个 benchmark 里，拆出来即可单独作用于一篇。**逐剧本质量门的完整可落地设计见 [[concepts/otome-script-quality-evaluator]]。**

## Benchmark 全景

### A. 选模型（有 leaderboard / 排名）

| Benchmark | 测什么 | 开源 | Leaderboard | 维度 | 对乙女 |
|---|---|---|---|---|---|
| **EQ-Bench Creative Writing v3** ([站](https://eqbench.com/creative_writing.html) / [repo](https://github.com/EQ-bench/creative-writing-bench)) | 通用创意写作（单篇散文） | source-available（license=null） | ✅ 活、在维护 | 22 项 rubric + 9 反面项（紫色辞藻 / tell-not-show，越低越好） | **选模型首选**；含 romance 提示；但单篇非互动，明确"Not a Roleplay Eval"，无分支 / 好感判据 |
| **lechmazur/writing** ([repo](https://github.com/lechmazur/writing)) | 短篇里塞入 10 个强制故事元素的能力 | ✅ | ✅ 有排名 | 元素融入度 + 文学质量 | 独立可信第二参考；测"约束下写作"，非互动 |
| **WebNovelBench** ([论文](https://arxiv.org/pdf/2505.14818)) | 中文网文 synopsis→长文 | ✅ GitHub+HF | ⚠️ 仅论文静态表（24 模型） | 8 个 PCA 加权维度（D5 人设一致性权重最高 0.1377、D4 对白辨识度、D8 场景连贯） | 长文 / 人设 / 文笔维度可借；**具体分数表被核查推翻，别信** |

### B. 测产出 / LLM-as-judge 方法论

| Benchmark | 方法 | 开源 | 对乙女价值 |
|---|---|---|---|
| **HelloBench / HelloEval** ([论文](https://arxiv.org/html/2409.16191v1) / [repo](https://github.com/Quehry/HelloBench)) | 每子类 4–6 个 yes/no checklist，权重用**线性回归拟合人工总分**；含 story / screenplay / roleplay 写作子类 | ✅ MIT | **逐场景质量门最佳模板**；与人工相关性远超 ROUGE/BLEU。注：论文从 ICLR 2025 撤稿但仍被广泛引用 |
| **RMTBench** ([论文](https://arxiv.org/pdf/2507.20352) / [HF](https://huggingface.co/datasets/xiangh/RMTBENCH)) | Qwen2.5-72B 当裁判，每维独立打分降长度偏差；双语 EN+ZH，80 角色 / 8156 轮 | ✅ HF | **唯一为多轮角色扮演而生**；情感 + 人设维度直接可用。对齐度 0.78 是二元两两偏好率（非相关系数）、仅覆盖 4 个难维度，作者自评"一般" |
| **ConStory-Bench / Checker** ([论文](https://arxiv.org/abs/2603.05890) / [repo](https://github.com/Picrew/ConStory-Bench)) | 证据绑定的矛盾检测；5 大类 / 19 子类一致性错误 | ✅ MIT | **长剧本连续性回归最佳**（伏笔崩没崩、人设漂没漂）；纯缺陷指标，不测文笔 / 魅力 |
| **LitBench** ([论文](https://arxiv.org/pdf/2507.00769)) | 创意写作可靠评测数据集；评测"哪个裁判模型最像人" | ✅ | **帮你选裁判**：Claude-3.7-Sonnet off-the-shelf 最强裁判，73% 人类一致率 |
| **RPGBench** ([论文](https://arxiv.org/abs/2502.00595)) | LLM 当游戏引擎：Game Creation + Game Simulation；**客观校验事件机制 + 变量更新（无需人工）** + LLM-judge 评趣味 / 动作 / 角色扮演 | 论文未明示 repo（待确认） | **好感度门槛 / signal 变量校验的现成模板**；范围是通用 RPG（世界 / 事件 / 状态），不含恋爱 |

### C. 分支 / 互动叙事载体（补搜新增，修正"零覆盖"结论）

| Benchmark / 工作 | 测什么 | 对乙女 |
|---|---|---|
| **RPGBench** | LLM 驱动分支互动游玩 + 可验证机制 | **最接近路线 / 门槛机制**；客观变量校验可移植到 affection-gate |
| **StoryBench** ([论文](https://arxiv.org/pdf/2506.13356)) | 基于互动小说游戏的分支决策树，量**长期记忆** | 证明"分支 IF 载体"已有 benchmark，但测记忆 / 推理，不碰恋爱情感 |
| **CharacterBox** (NAACL 2025) | 文本虚拟世界里角色行为 / 动作的逻辑一致性 | 人设一致性维度可借 |
| **role-play-bench** (MiniMax, [HF](https://huggingface.co/datasets/MiniMaxAI/role-play-bench)) | 100 轮长上下文 RP 稳定性 | 长程人设保持的压测范式 |
| WHAT-IF / Narrative Studio / Multiverse of Greatness | 分支叙事**生成 / 创作**工具（MCTS / meta-prompting） | 是 authoring 工具不是 benchmark，仅作思路参考 |

### D. 长文 / 长度

| Benchmark | 测什么 | 对乙女 |
|---|---|---|
| **LongWriter / LongBench-Write** ([论文](https://arxiv.org/abs/2408.07055) / [repo](https://github.com/THUDM/LongWriter)) | 超长生成：长度分 S_l + 6 维通用质量分 S_q（GPT-4o judge） | 只覆盖"长文不崩"；长度分是 proxy（达标也可能退化重复） |

## 缺口分析（修正版）

| 乙女核心能力 | 覆盖 | 可借 |
|---|---|---|
| ① 分支机制正确性（好感变量更新 / 门槛触发 / 路线一致） | 🟡 **部分** | RPGBench 客观校验 + StoryBench 记忆评测 |
| ② 长篇连贯 + 文笔 | ✅ 有 | ConStory（一致性）+ WebNovelBench/EQ-Bench（文笔） |
| ③ 角色一致性 / 长程人设 | ✅ 有 | RMTBench CM + CharacterBox + WebNovelBench D5 |
| ④ 恋爱弧推进 / 路线浪漫兑现 | ❌ **真空白** | 无；必须原创 |
| ⑤ 男主魅力 / 吸引力 | ❌ **真空白** | 无；必须原创 |

## 自建乙女 Benchmark 配方

不用从零。建议拼法：

- **客观 harness（机制正确性）** = 仿 RPGBench：对生成剧本跑状态机校验——好感 / [[concepts/signal-int-backend|@signal 变量]]更新是否正确、门槛是否按 affection 触发、路线分叉是否一致。我们 LS（[[entities/lunascripts]]）本就编译成可程序化校验的结构，这块基本是"接现成校验器"。
- **主观骨架（场景质量门）** = 仿 HelloEval：每类场景 4–6 个 yes/no checklist，权重用线性回归拟合人工分，之后自动打分做回归基线。
- **裁判模型** = 按 LitBench，Claude（3.7-Sonnet 起）是最像人的 off-the-shelf 裁判；用 Judgemark 式"裁判质量校验"确认。**注意**：中文亲密恋爱内容 + 安全过滤会压低浪漫强度评分，选裁判要专门验。
- **复用维度**：RMTBench 情感表达 / 情感理解 / 角色保持 + EQ-Bench 反面项（反紫色辞藻）+ WebNovelBench D4/D5/D8 + ConStory 5 大类一致性。
- **➕ 原创维度（市面没有，这是真正要造的部分）**：
  - 好感弧推进（affection-arc progression）：好感增长是否有节奏、可信、不跳变
  - 男主魅力（male-lead appeal）：吸引力 / 心动点 / 人设落地
  - 路线浪漫兑现（route romantic payoff）：到达高好感路线时浪漫高潮是否兑现
  - 选择有意义性（choice meaningfulness）：玩家选择是否真的影响分支、不是伪选项
  - 门槛连贯（gate coherence）：内容亲密度与当前 affection 等级是否匹配

参见我们已有的数值系统 [[concepts/novel-game-config]] 与 otome demo [[concepts/villain-season-demo]]。

## 模型选型现状（Goal 1）

- **强档（创意散文）**：EQ-Bench v3 榜首 Grok-4.1 Thinking（1721.9 Elo），Qwen3-235B 系列 rubric 分很高（~0.875）；中文开源权重（Qwen / DeepSeek）与闭源同档。
- ⚠️ **未能拿到干净的全量活榜**：eqbench.com 活榜是 JS 渲染抓不全，找到的 llm-stats 镜像数据损坏（Elo 与 rubric 混表、只剩 Grok+Qwen）。**要精确知道某个候选底座（Kimi / GLM / MiniMax 等）排第几，需点进活榜实查 + 叉乘 lechmazur/writing。**
- ⚠️ WebNovelBench 那张含具体分数（Kimi 2.54 等）的表**已被核查推翻**，不可引用。

## Caveats / 不可信的数字

1. WebNovelBench 模型分数表（含 Kimi 2.54）被推翻——只有"存在 24 模型排名"为真。
2. EQ-Bench "14 维"是旧版 v2，现行 v3 是 **22 维**。
3. RMTBench 0.78 = 二元两两偏好一致率，非 Pearson/Spearman，仅 4 个难维度有人工标注。
4. HelloEval 论文从 ICLR 2025 撤稿（仍在 arXiv + 广泛引用，未过同行评审）。
5. ConStory 只测"不一致"，不测文笔 / 魅力 / 爽感。
6. RPGBench 开源状态论文摘要未明示，repo / license 待确认。
7. 所有榜单都是快照，选型前重查。

## Open Questions / 下一步

1. 确认 RPGBench 的 repo / license，以及它的 Game-Simulation 校验 harness 能否移植到 affection-gated VN。
2. 给中文亲密恋爱内容定裁判模型——安全过滤对浪漫强度评分的影响要专测。
3. 拟合 HelloEval 式回归权重需要多少条人工标注乙女剧本（HelloEval 按子类标注，RMTBench 用 ~500 对话 / 3 标注者）。
4. 明确我们实际在选哪些候选底座 → 再做一次精确的 EQ-Bench / lechmazur 实查。

## 核心来源

- EQ-Bench Creative Writing v3 — https://eqbench.com/creative_writing.html ; https://github.com/EQ-bench/creative-writing-bench
- RMTBench — https://arxiv.org/pdf/2507.20352 ; https://huggingface.co/datasets/xiangh/RMTBENCH
- HelloBench/HelloEval — https://arxiv.org/html/2409.16191v1 ; https://github.com/Quehry/HelloBench
- ConStory-Bench — https://arxiv.org/abs/2603.05890 ; https://github.com/Picrew/ConStory-Bench
- WebNovelBench — https://arxiv.org/pdf/2505.14818
- RPGBench — https://arxiv.org/abs/2502.00595
- StoryBench — https://arxiv.org/pdf/2506.13356
- LitBench — https://arxiv.org/pdf/2507.00769
- LongWriter / LongBench-Write — https://arxiv.org/abs/2408.07055
- lechmazur/writing — https://github.com/lechmazur/writing
- CharacterBox — https://aclanthology.org/2025.naacl-long.323.pdf

## 相关页面

- [[entities/lunascripts]] — LS 编译产物是可程序化校验的结构（客观 harness 的基础）
- [[concepts/signal-int-backend]] — @signal 作者变量（好感 / 门槛校验对象）
- [[concepts/novel-game-config]] — 每剧本数值系统（affection / 检定变量）
- [[concepts/villain-season-demo]] — 现成 otome 短剧 demo（自建 benchmark 的标注语料候选）
