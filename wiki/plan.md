---
title: 团队行动计划
tags: [plan, roadmap, status]
created: 2026-04-15
updated: 2026-04-15
---

这是一个持续维护的计划文件。所有人都可以更新自己的进度和下一步。每次更新时修改 `updated` 日期。

## 当前状态快照

| 方向 | 状态 | 负责 |
|------|------|------|
| 产品形态转型 | 已完成 MSS 脚本定义和解释器 | Clock |
| Dramatizer 重构 | 待启动——需要对接 MSS 输出格式 | August |
| Agent-Forge 转型 | 待启动——从视频管线转为 VN 素材管线 | 待定 |
| 前端播放器 | 待启动——消费 MSS JSON 的 Unfolded 风格播放器 | 待定 |
| 视频生产（现行） | 继续——雨佳和何莲保障视频生产 | 雨佳/何莲 |
| UIUX | 待启动——运营和 UIUX 先行 | 待定 |
| 运营 | 急需推进——4 个月了还没 demo，需要尽快上线测试 | 待定 |

## 产品侧

### 已完成

- [x] 视觉形态论证（v3 调研 → Unfolded 风格确定）
- [x] MSS 脚本格式设计 v2.1（完整指令集、Remix 兼容、gates 路由）
- [x] MSS 解释器 Go 二进制（lexer/parser/validator/fixer/resolver/emitter）
- [x] MSS Agent Skill（给 Dramatizer/Remix LLM 的写作指南）
- [x] No Rules E1-E4 转换为 MSS 格式验证

### 进行中

- [ ] A/B Test 复原 Live 2D + TTS 模式（后台已保留兼容）
- [ ] 内容分集上线策略（十集十集上，做成"游戏卡带"感觉）

### 待启动

- [ ] Dramatizer Phase 3 重构：ludify 输出从 JSON 改为 MSS 格式
- [ ] Agent-Forge 素材管线重构：LoRA → 表情 Inpainting → LivePortrait → 背景 → CG
- [ ] 前端 Unfolded 播放器：消费 MSS JSON，实现 5 种叙事容器 + 嵌入式小游戏
- [ ] Remix 功能加速：剧情 Remix + 聊天 Remix + 结局 Remix + 角色支线 Remix
- [ ] premium choice 支持（`@choice` 加 premium 参数）

## 技术侧

### 核心目标：三端打通，Agent Native

每个端（游戏/剧本/视频）彻底 Agent Native 化，主控模型可以同时掌握三端的过程、结果和体验。

### 架构调整

- [ ] REMIX 管线独立化：从游戏后端拆出，做成单独服务，自己 mock 游戏侧体验，游戏侧只拿数据和校验
- [ ] 素材映射表自动化：Agent-Forge 生成素材后自动更新 mapping.json
- [ ] MSS 编译集成到 CI：Dramatizer 产出 → MSS 编译 → JSON → 部署到 OSS

### 工具 / 基建

- [ ] 所有代码 Atomic commits，接受产品侧和运营侧也参与提交
- [ ] 工具 GUI 只要能用就行，不追求完美
- [ ] 不需要 PRD 稿，直接在 demo 上做 feature

## 运营侧

### 紧急

- [ ] **尽快上 demo**——拒绝闭门造车，4 个月过去了需要真实用户反馈
- [ ] 开源计划的核心 PR 需要排上时间

### 待定

- [ ] TikTok / Ins 引流策略
- [ ] 创作者生态规划（从 Episode 式被动社区 → 主动社区）

## 关键决策记录

| 日期 | 决策 | 原因 |
|------|------|------|
| 2026-04 | 视频 → Unfolded VN | 视频模型不及预期，玩家体感最重剧本效果 |
| 2026-04 | 保留 D20 + 小游戏 | 游戏性保证，嵌入阅读流而非独立阶段 |
| 2026-04 | MSS 统一脚本格式 | Dramatizer + Remix 统一输出，解耦脚本与素材 |
| 2026-04 | 素材预生成 + LoRA | 角色一致性生死线，预生成绕过实时生成的核心痛点 |
| 2026-04 | 双 Feed（Classic + Remix） | 官方正剧和玩家二创调性互相伤害，分开放 |

## 风险 / 待解决

- 视频模型能力仍在快速迭代，需要持续评估是否要回到视频形态
- CHA 类小游戏目前只有 2 个，是待补充方向
- 角色一致性在 Remix 实时生成场景下仍有挑战（LoRA 只能覆盖预定义角色）
- 前端播放器开发量较大，需要评估优先级和人力
