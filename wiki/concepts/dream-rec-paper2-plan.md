---
title: dream-rec Paper #2 方案 — 表征隔离基准 + 科研 skill 工具链
updated: 2026-06-11
tags: [dream-rec, paper, research-skills, cold-start, benchmark]
sources: [dream-recv2/docs/2026-06-10-paper2-feasibility-plan.md, dream-recv2/docs/2026-06-11-spec-v3.1-representation-isolation-benchmark.md]
status: active
---

# dream-rec Paper #2 方案（2026-06-10，阶段 A+B 完成 06-11）

全文：`dream-recv2/docs/2026-06-10-paper2-feasibility-plan.md`（工具链+流程映射）与 `dream-recv2/docs/2026-06-11-spec-v3.1-representation-isolation-benchmark.md`（实验 spec，超越 v3）。本页是决策摘要。

## 结论

1. **选题沿用 v3 spec 并升级为 v3.1**：*When Do LLM Representations Help Item Cold-Start? A Representation-Isolation Benchmark*。固定 backbone、只换表征、2D 冷启动严重度网格、4 项协议陷阱审计（新 RQ4）、产出决策规则。两个方向的结果都可发表。
2. **旧探索实验（2026-05-30 matrix_*.json）的"TF-IDF 打败 LLM embedding"结论作废**，5 个协议缺陷：①"LLM"只是 MiniLM/bge-small 级小模型（数据显示模型越大越接近 TF-IDF，SOTA embedding 下可能翻转）；②neural 256-token 截断 vs TF-IDF 全文不公平；③n_neg=200 负采样评估（Krichene & Rendle KDD'20）；④ridge/probit 固定超参欠正则；⑤随机冷启动 split 无时序。修复=论文 motivation 的一部分（Finding 0）。
3. **选刊**：IPM（中科院 1 区）主投或 TOIS（CCF-A，IF 9.1）冲刺，KBS/ESWA 次选；TORS 新刊无分区不满足硬约束。投稿前以最新中科院分区表核实。
4. **时间线**：阶段 B 协议修复（✅ 06-11 完成，远快于 2 周计划）→ C 探针 1 周（go/no-go）→ D 全矩阵 4 周 → E 写作 4 周 → F 预审投稿 2 周，约 10–12 周（Q3 2026 投出）。

## 阶段 B 协议修复 harness（2026-06-11 完成）

- 新仓库 `dream-recv2`：uv + `src/repbench/`，从 dream-rec-paper/sim 行为保持迁移；**出口检查**用上游缓存 + 旧配置复现旧 matrix_Video_Games.json 全部 5 个 grid cell（容差 1e-6）——迁移无损有测试背书，legacy 路径冻结为 RQ4"缺陷协议"审计 arm。
- **五项协议修复全部落地**（TDD，每项先写单测，共 86 个测试）：①全量 cold-pool 排序 evaluator（与负采样 arm 的用户/profile 逐位对齐，审计只换 evaluator 一个杠杆）；②文本公平（encoder 默认原生上下文窗口，256-token cap 只作 RQ4 复现 arm，缓存键分离）；③per-cell 网格调参（用户级验证折，log-grid 含 legacy 固定值，kNN 引入可调 top-k 且 k=None 与旧质心余弦排序等价）；④temporal cold split（最晚到达 items 为 cold，τ 前历史做 profile；Amazon 加载器新增时间戳支持走独立缓存键）；⑤6 模型 encoder 适配层（minilm / bge_small / gte_qwen2_1p5b / qwen3_4b / voyage4 / qwen3_8b 注册表 + sdpa/trust_remote_code 工程参数 + (dataset, encoder, 截断 arm) 缓存）。
- 下一步阶段 C 探针：VG 单数据集、固定协议、4 表征 × 3 轻 backbone，kill-switch 定论文 framing（两种结果都可发表）。

## 阶段 A 查新与出口评审（2026-06-11 完成）

- **3 路并行查新（25+ 论文）确认 GO**：四个系统性 gap 无人占据（severity 连续轴 / 表征-架构隔离 / 协议审计捆绑 / 固定 backbone 下的 encoder 全谱对比）。
- **近邻定位**：arXiv 2512.13001（Kusano+，training-free TEM vs LLM-reranker，未中刊）是最近邻但缺我们全部 5 个设计核心；AlphaRec（ICLR'25 Oral）projector 共训属表征-架构混淆；担心的 2602.15012 (Pep) 根本不是推荐论文（推理域偏好引导），一句话区分即可。黄金引语：SIGIR'26 复现研究 "key design choices are frequently changed together"（arXiv:2603.29845）；BLaIR 证明 MTEB 排名与推荐性能几乎无关。
- **6 模型 embedding 实验集选定**（能力轴全覆盖，总 API 成本 ~$9）：MiniLM + bge-small（小对照）/ gte-Qwen2-1.5B + Qwen3-Embedding-4B（开源中档，MPS 本地）/ Voyage-4（API 前沿）/ Qwen3-Embedding-8B（开源前沿，Apache 2.0；NV-Embed-v2 因 CC-BY-NC 弃用）。工程坑：sentence-transformers≥2.7.0（EOS pooling）、MPS 走 sdpa+fallback。
- **idea-evaluator 出口评审：Accept with Revisions**（Stronger 9 / Cheaper 8 双主轴；paradigm 探针 4/4 yes）。两个 MAJOR 已防御并写回 spec §4.8：①实验矩阵预收缩（重 backbone 只跑 5 锚点 cell、RQ4 只跑 VG×3 轻 backbone）；②upper-bound cell 改为 RLMRec 同协议实测 ×1 数据集。

## 科研 skill 调研结论（deep-research，3-0 对抗验证）

- 三个点名仓库均真实：K-Dense scientific-agent-skills（27.8k★，144 skills，偏生科）、nature-skills（18.4k★，论文后段 10 skills）、Supervisor-Skills（港科广 DIAL，2.2k★，04-29 后停更）。另确认 claude-scholar（4.3k★）是 CS/ML 论文最对口全流程包。
- **全自动科研系统不可用于正经论文**：AI Scientist 独立评估 42% 实验失败（arXiv:2502.14297）；自治科研 4 试 3 败 + 六大失败模式（arXiv:2601.03315）；"PaperQA2 超 PhD"宣传被 0-3 推翻。采用 skill 增强的人主导工作流。
- 已从四仓精选 **22 个 skill 装入 `dream-recv2/.claude/skills/`**（出处/commit/license 见同目录 ATTRIBUTION.md；Supervisor-Skills 五个为 CC BY-NC，勿商用分发）。关键映射：benchmark-paper-template（骨架）、nature-figure（出版图）、citation-verification（防编造引用——v1 spec 事故的制度化防线）、nature-reviewer + pre-submission-reviewer（投稿前模拟审稿）、review-response（审稿回复）；06-11 补装 K-Dense 统计三件套（statistical-analysis / statsmodels / exploratory-data-analysis）加固 C/D 实验统计段。

## 给 dream-rec 产品侧的批评（独立于论文）

最高优先级三条：①补 recommend_log，否则上线效果永远不可度量；②LLM 自报 confidence 进 ψ² 似然但零校准（正是论文 #1 证明的"虚增精度"失败模式），至少做抽样人审校准；③θ 后验协方差被 `del` 弃用——**2026-06-10 排序器升级已部分响应（Thompson 采样通道，见 [[concepts/dream-rec-ranker-upgrade-2026-06]]）**。完整 10 条见方案 §5。

## Cross-links

- [[concepts/dream-rec-component-1-tirt-estimator]] / [[concepts/dream-rec-component-2-llm-tagger]] / [[concepts/dream-rec-component-5-cold-start]] — 被批评条目对应的组件设计
- [[concepts/dream-rec-ranker-upgrade-2026-06]] — θ_cov 批评的产品侧响应
- [[concepts/dream-rec-monorepo-migration]] — 生产代码现所在
