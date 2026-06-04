---
title: 乙女逐剧本质量评分器设计（per-script quality gate）
updated: 2026-06-04
tags: [evaluation, otome, llm-as-judge, quality-gate, mss]
---

# 乙女逐剧本质量评分器设计

> 配套 [[concepts/otome-writing-benchmark-survey-2026-06]]。把"自建乙女 benchmark"拆成两层，本页只讲 **② 逐剧本质量门**。

## 定位：① benchmark ≠ ② evaluator

- **① Benchmark（榜单）= 测模型**：固定题集 → N 个模型各写一遍 → 打分 → 排名。单位是"模型"。只在模型之间比才有意义（EQ-Bench / WebNovelBench）。→ 选底座用。
- **② Evaluator（评分器）= 测作品**：拿一篇**已写好**的剧本 → rubric/checklist/裁判打分 → 输出这一篇的质量报告。单位是"这一篇文本"。**source-agnostic**：不在乎是模型生成、手写、还是 pipeline 产出的。→ **QA / 回归 / 质量门用，本页讲这个。**

榜单内部本来就是"先对每篇单独打分(②)，再按模型聚合排名(①)"。所以 ② 的能力埋在每个 benchmark 里，拆出来即可单独作用于一篇，不需要别的模型陪跑。

## 输入 / 输出

- **输入**：一篇 MSS 剧本（.md）。两种表示并用：
  - 编译后 JSON（[[entities/moonshort-script]] 产出，含 step / 分支 / `@signal` op / `@gate` 条件 / episode-scoped step ID）→ 客观层用
  - 原始散文 / 对白文本 → 主观层用
- **输出**：
  - 分维度评分（0–5）
  - 问题清单（每条**定位到 step ID**，可点回原文）
  - 判定：**PASS / WARN / FAIL**

## 架构：3 层 + 聚合

```
MSS .md ──compile(moonshort-script)──► 结构化 JSON
   │
   ▼
L0 结构客观校验  (确定性, 无 LLM, 仿 RPGBench)
   好感变量逻辑 / @gate 可达性 / 分支完整 / 伪选择
   → 硬门：结构坏了直接 FAIL，省下后面 LLM 的钱
   │ (结构通过)
   ▼
L1 逐场景主观评分  (LLM-as-judge, 仿 HelloEval + RMTBench + EQ-Bench)
   每场 4–6 个 yes/no checklist × N 维度
   → 分维度 0–5 + 命中的问题
   │
   ▼
L2 全篇一致性检测  (LLM, evidence-grounded, 仿 ConStory-Checker)
   人设漂移 / 伏笔未回收 / 矛盾，带原文双锚点
   → 矛盾清单(severity)
   │
   ▼
聚合 + 判定 → PASS / WARN / FAIL + 定位问题清单
```

把**确定性、最便宜、最可靠**的 L0 放最前面当硬门：结构性 bug（门进不去、变量逻辑错、伪选择）先一票否决，省下 L1/L2 的 LLM token。

## L0 — 结构客观校验（确定性，无 LLM）

对编译后分支图 + 变量 op 做静态分析。`@gate` 是"变量 ≥ 整数"形式（见 [[concepts/mss-gate-no-variable-comparison]]），所以可达性是可判定的。

| 检查 | 判什么 |
|---|---|
| 好感 / `@signal` 变量逻辑 | 变量是否声明；增减是否合法；死变量（声明从不用 / 用了从不设）；见 [[concepts/signal-int-backend]] |
| `@gate` 可达性 | 沿某条路径累加 `@signal` op，该门槛整数值是否真的可达；有没有玩家永远进不去的门 / 设得不可能达到的阈值 |
| 分支完整性 | 孤儿 step、无出口分支、不可达 ending |
| 伪选择（结构层） | 两个选项是否导向结构上相同的后续 step |

输出确定，100% 可靠，**是唯一可以立刻当硬门的层**（不需要标注数据）。

## L1 — 逐场景主观评分（LLM-as-judge）

方法 = HelloEval 式：每个维度 4–6 个 yes/no checklist，权重用线性回归拟合人工分（冷启动先等权/手设）；每维独立打分降长度偏差（RMTBench 技巧）。

### 复用维度（现成 benchmark 直接搬）

| 维度 | 作用对象 | 来源 |
|---|---|---|
| 文笔质感（反紫色辞藻 / 反 tell-not-show） | 散文 | EQ-Bench 负向项 |
| 情感表达 / 情感理解 | 对白 | RMTBench EE/EC |
| 角色保持 / 一致性 | 全篇 | RMTBench CM + WebNovelBench D5 |
| 对白辨识度（男主嗓音区别于路人） | 对白 | WebNovelBench D4 |

### 原创乙女维度（市面没有，这是真正要造的部分）

每条给 2–3 个示例 checklist（落地按 4–6 条）：

- **好感弧推进**
  - 好感提升是否由具体互动事件驱动（非凭空跳升）？
  - 单场好感变化幅度是否与情节强度匹配（小事不大涨）？
  - 是否有波折 / 回落（纯单调上升会假）？
- **男主魅力**
  - 这一场是否至少有一个"心动点"（反差 / 温柔 / 强势 / 脆弱瞬间）？
  - 台词是否有记忆度、有个人特征（不是路人腔）？
  - 是否避免"工具人"——他有独立动机，不只围着玩家转？
- **路线浪漫兑现**
  - 高好感节点是否有与铺垫匹配的浪漫高潮？
  - 是否兑现了前面埋的期待（承诺—兑现闭环）？
  - 不同路线的浪漫兑现是否差异化（不是换名字的同一场戏）？
- **门槛连贯**（横跨 L1+L0）
  - 高亲密内容（牵手 / 拥抱 / 告白）是否只在对应好感门槛之后出现？
  - 跨过门槛后的关系阶段是否匹配（不会跨初识门就直接老夫老妻）？
- **选择有意义性**（语义层，结构层在 L0）
  - 选项之间是否有真实的情感 / 性格 / 价值取向差异（不是"好的" vs "嗯"）？
  - 选择后果是否在后续被体现（选了什么影响了什么）？

## L2 — 全篇一致性检测（evidence-grounded）

仿 ConStory-Checker：扫全篇长程，输出矛盾清单，每条绑定**两个原文锚点**（铺垫处 + 违反处）。覆盖 5 类：时间线 / 剧情逻辑、人设（记忆矛盾、能力漂移）、世界观设定、事实细节、叙事与风格（视角 / 语气突变）。对应乙女最痛的"人设漂移 + 伏笔没回收"。

## 聚合 + 判定

- **L0** → 硬门：任一结构性失败 = **FAIL**（fail fast，不进 LLM 层）。
- **L1** → 各维度加权汇总：任一维度低于地板分 或 总分低于 bar = **FAIL**；接近 = **WARN**。
- **L2** → 有 CRITICAL 矛盾 = **FAIL**；有 minor = **WARN**。
- 最终 **PASS / WARN / FAIL** + 定位到 step 的问题清单。

## 裁判模型 + 校准

- **裁判选型**：按 LitBench，Claude（3.7-Sonnet 起）off-the-shelf 最像人（73% 一致率）。用 Judgemark 式"裁判质量校验"在样本上确认。
- ⚠️ **中文亲密恋爱内容风险**：安全过滤可能压低"浪漫强度 / 男主魅力"评分，选裁判要专门在亲密场景样本上验，必要时换容忍度合适的裁判。
- **信任曲线**：
  - 冷启动（无标注）：手设 rubric 锚点 + 等权，L1/L2 只做 **WARN**（建议），**L0 是唯一硬门**。
  - 校准后：标注 M 篇剧本人工总分 → 回归拟合维度权重（HelloEval 式）→ 裁判过 Judgemark 校验 → L1 升级为硬门。
- 标注语料种子：恶人季 demo（[[concepts/villain-season-demo]]）+ 既有产出剧本。

## 落地分期

- **Phase 0**（先上，高 ROI）：L0 纯静态分析，无 LLM、无标注，接 moonshort-script 编译产物即可跑。立刻抓结构 bug。
- **Phase 1**：L1 + L2 接 Claude 裁判 + 手设锚点，做 **WARN** 软信号。
- **Phase 2**：标注 + 回归拟合权重 + 裁判校验 → L1 升硬门。
- **Phase 3**（可选）：建真人乙女网文参考语料 → 加 WebNovelBench 式"百分位 / 有没有真人水准"模式。

## 待定 / 依赖

- 确认 RPGBench 的 Game-Simulation 校验 harness 能否直接移植（repo / license 待查）。
- L0 静态分析具体接 moonshort-script 哪个产物字段（step 图 + signal op 表）。
- 校准需要多少标注样本才稳（HelloEval 按子类标注；RMTBench ~500 对话 / 3 标注者）。
- 中文亲密内容的裁判选型 + 安全过滤实测。

## 相关页面

- [[concepts/otome-writing-benchmark-survey-2026-06]] — 全景调研 + ① 选模型那层
- [[entities/moonshort-script]] — 编译产物（L0 静态分析的输入）
- [[concepts/signal-int-backend]] — `@signal` 变量（好感 / 门槛校验对象）
- [[concepts/mss-gate-no-variable-comparison]] — `@gate` 整数阈值（可达性分析前提）
- [[concepts/novel-game-config]] — 每剧本数值系统
- [[concepts/villain-season-demo]] — 标注语料种子
