---
title: dream-rec Ranker Upgrade — Optional Channels + Thompson Sampling (2026-06)
tags: [dream-rec, recommendation, thompson-sampling, bandit, cold-start, exploration]
sources: [services/dream-rec/docs/superpowers/specs/2026-06-10-ranker-upgrade-port-and-runbook.md]
created: 2026-06-10
updated: 2026-06-10
---

dream-rec 排序器的可选通道升级:**6 个提交，落在 lunaverse-backend 分支 `feat/dream-rec-recsys-upgrade`**（基 origin/main;截至 2026-06-10 **仅在本地 worktree `~/MobAI/msb-recsys`，未 push、未开 PR**——等 August 批准）。全部通道 **feature-flag 默认关 = 与 main 字节级一致、热路径零额外 HTTP**。北极星:内容×玩家匹配为主，每个玩家玩到的都是为他定制、各不相同的小说。

## 通道一览（env flag，默认值=关）

| Flag | 通道 | 备注 |
|---|---|---|
| `RANKER_THOMPSON_SCALE=0.0` | **Thompson 采样**（本次主菜，新写） | 每次请求从 θ 后验抽一份口味排序;零历史玩家从先验 N(0,I) 抽 → **新玩家第一屏人人不同**（实测 12 次请求 9 种排序;关=字节一致）。配 `RANKER_THOMPSON_W_FLOOR=0.35` 让采样口味过冷权重路径。建议第一个开（0.5 起步） |
| `RANKER_EXPLORATION_KAPPA=0.0` | UCB 探索 | κ·√(后验方差投影);对零历史用户无效（无后验），与 Thompson 二选一 |
| `RANKER_COLLAB_WEIGHT=0.0` | 协同亲和度融合 | 读者 UserNovelProfile.vector ↔ Dream.producerVector;**依赖 dream-trigger v2 暴露 batch affinity 端点（尚不存在）**，在那之前 affinity 恒 None=纯内容、绝不报错。契约假定记录在 `backend_client.get_dream_affinities` |
| `RANKER_POPULARITY_DAMPING=1.0` | 流行度阻尼 | 凹变换压 engagement，抗强者愈强 |
| `RANKER_MMR_LAMBDA=1.0` | 列表内 MMR 多样性 | 单人列表内别重样;非北极星主目标 |

另含:投影硬化（畸形 genre matrix 降级 cold-start identity 而非 500）、离线评测台 `evals/`（**合成数据，只证机制不证真实收益**）、runbook（启用顺序、与 score_history P50 动态阈值的交互、冷启动问卷接线提案）、顺手修了 main 上一个过期断言（`llm_retry_max` 1→5）。

## 为什么是 Thompson（一句话版）

实测钉死的缺口:零历史玩家全员看同一张确定性热门榜，且 UCB 对他们无效。Thompson 把 TIRT 估计器**本来就在维护、但排序器一直丢弃**的后验协方差用起来:信念宽→抽样散（探索+人人不同），信念窄→抽样贴均值（探索自动消退），抽样引出的选择又喂回 TIRT 更新——标准 bandit 闭环，无需手动探索衰减日程。新增代码 ~80 行，每请求一次 6×6 Cholesky（微秒级）。

## 刻意没移植的:质量先验

归档仓原有第 6 通道（moonshort 完成率/播放量 → 全候选共享标量凸混合）。复审实证驳回:同一标量对全候选是**保序仿射变换，数学上改不了推荐顺序**。若要"对高活跃用户多推"，应在阈值层显式做。

## 证据基础

二轮深度调研（25 条论断全量 3 票对抗核实，24 确认）:此规模（每本几十候选）下 HSTU/OneRec/LLM-as-ranker/diffusion-rec 全档驳回（规模差 6–10 个数量级;旗舰案例回报 ≈1%;LLM-ranker 自带流行度偏差反北极星）;证据支持"简单方法+bandit 试探"。裁决文档:归档仓 `AugustZAD/dream-rec` `docs/superpowers/specs/2026-06-10-recsys-advancedness-verdict.md`。

## 验证（2026-06-10）

- 完整 pytest **390 passed**（testcontainers/Docker;`tests/brm_validation` 论文组除外）+ ruff 全绿
- 默认关字节一致门、零 HTTP 守卫、端到端发散性（9/12 distinct orders）全过

## 待办 / 依赖

1. **push + PR**:等 August 明确批准（cdotlock 仓规矩）;PR body 草稿在 `/tmp/dream-rec-pr-body.md`
2. **冷启动问卷接线**:dream-rec 侧 API 已就绪（`/cold_start/items` + `/cold_start/answers`），缺 lunaverse-backend UX 触发点（提案:首次进 novel 且无 θ 档案时弹 5 题）——产品拍板
3. **v2 affinity 端点**:`POST /api/internal/user-novel-profiles/{u}/{n}/affinities` body `{dreamIds:[...]}` → `{affinities:{id:cosine|null}}`（假定契约，需与 v2 owner 对齐）
4. 启用后盯 `meta.threshold_used`:通道改分数分布 → P50 阈值随窗口自适应，初期推送率会漂移

## Related

- [[concepts/dream-rec-component-4-dream-ranker]] — 被升级的排序器本体
- [[concepts/dream-rec-component-5-cold-start]] — 问卷后端（待接线）
- [[concepts/dream-trigger-v2-mechanical]] — 行为向量的所有者（协同通道数据源）
- [[concepts/dream-rec-trigger-v2-coexistence]] — 职责边界与向量复用 defer 决议
- [[concepts/dream-rec-monorepo-migration]] — 代码为何住在 lunaverse-backend
