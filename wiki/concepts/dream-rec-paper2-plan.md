---
title: dream-rec Paper #2 方案 — 表征隔离基准 + 科研 skill 工具链
updated: 2026-06-10
tags: [dream-rec, paper, research-skills, cold-start, benchmark]
sources: [dream-recv2/docs/2026-06-10-paper2-feasibility-plan.md]
status: active
---

# dream-rec Paper #2 方案（2026-06-10）

全文：`dream-recv2/docs/2026-06-10-paper2-feasibility-plan.md`（含 19 个 skill 的来源与 license、完整流程映射、风险表）。本页是决策摘要。

## 结论

1. **选题沿用 v3 spec**（`dream-rec-paper/docs/design-specs/2026-05-29-llm-coldstart-representation-study-design.md`）：*When Do LLM Representations Help Item Cold-Start? A Representation-Isolation Benchmark*。固定 backbone、只换表征、按冷启动严重度分层，产出"何时值得用 LLM 表征"的决策规则。两个方向的结果都可发表。
2. **旧探索实验（2026-05-30 matrix_*.json）的"TF-IDF 打败 LLM embedding"结论作废**，查验发现 5 个协议缺陷：①"LLM"只是 MiniLM/bge-small 级小模型（且数据显示模型越大越接近 TF-IDF，SOTA embedding 下可能翻转）；②neural 256-token 截断 vs TF-IDF 全文不公平；③n_neg=200 负采样评估（Krichene & Rendle KDD'20）；④ridge/probit 固定超参欠正则（"Bayesian 差 2×"大概率是调参问题）；⑤随机冷启动 split 无时序。修复清单已写入方案 §3，修复本身成为论文 motivation 的一部分。
3. **选刊**：IPM（中科院 1 区）或 TOIS（2 区，IF 9.1）主投，KBS/ESWA 次选，Neurocomputing 保底；TORS 最对口但新刊无分区，不满足 SCI Q2+ 硬约束。投稿前以中科院最新分区表核实。
4. **时间线**：协议修复 2 周 → 探针 1 周（go/no-go）→ 全矩阵 4 周 → 写作 4 周 → 预审投稿 2 周，约 10–12 周（Q3 2026 投出）。

## 科研 skill 调研结论（deep-research，3-0 对抗验证）

- 三个点名仓库均真实：K-Dense scientific-agent-skills（27.8k★，144 skills，偏生科）、nature-skills（18.4k★，论文后段 10 skills）、Supervisor-Skills（港科广 DIAL，2.2k★，04-29 后停更）。另确认 claude-scholar（4.3k★）是 CS/ML 论文最对口全流程包。
- **全自动科研系统不可用于正经论文**：AI Scientist 独立评估 42% 实验失败（arXiv:2502.14297）；自治科研 4 试 3 败 + 六大失败模式（arXiv:2601.03315）；"PaperQA2 超 PhD"宣传被 0-3 推翻。采用 skill 增强的人主导工作流。
- 已从三仓精选 **19 个 skill 装入 `dream-recv2/.claude/skills/`**（出处/commit/license 见同目录 ATTRIBUTION.md；Supervisor-Skills 五个为 CC BY-NC，勿商用分发）。关键映射：benchmark-paper-template（骨架）、nature-figure（出版图）、citation-verification（防编造引用——v1 spec 事故的制度化防线）、nature-reviewer + pre-submission-reviewer（投稿前模拟审稿）、review-response（审稿回复）。

## 给 dream-rec 产品侧的批评（独立于论文）

最高优先级三条：①补 recommend_log，否则上线效果永远不可度量；②LLM 自报 confidence 进 ψ² 似然但零校准（正是论文 #1 证明的"虚增精度"失败模式），至少做抽样人审校准；③θ 后验协方差被 `del` 弃用，TIRT 的不确定性卖点没有兑现（无探索策略）。完整 10 条见方案 §5。

## Cross-links

- [[concepts/dream-rec-component-1-tirt-estimator]] / [[concepts/dream-rec-component-2-llm-tagger]] / [[concepts/dream-rec-component-5-cold-start]] — 被批评条目对应的组件设计
- [[concepts/dream-rec-monorepo-migration]] — 生产代码现所在
