---
title: Vibe Motion
tags: [remotion, video, motion-graphics, promo, villain-season, lunaverse]
sources: []
created: 2026-06-16
updated: 2026-06-16
---

Vibe Motion 是 AI 驱动的 motion graphics 工作仓库，以 Remotion（React 视频框架）为核心，负责 Lunaverse 平台的宣传视频制作。产出竖屏 9:16 格式视频，面向 TikTok / Reels / Shorts 投放。

仓库：[cdotlock/mob-vibe-motion](https://github.com/cdotlock/mob-vibe-motion)（私有）。
本机路径：`/Users/Clock/vibe-motion`

## 三区目录结构

```
work/    工作区 — 项目与产出
skills/  知识区 — 可复用生产经验（SKILL.md 格式）
deps/    依赖区 — 17 个 clone 的参考仓库（不入库，bash deps/restore.sh 恢复）
```

## 已完成 / 进行中项目

| 路径 | 说明 | 状态 |
|---|---|---|
| `work/lunaverse-intro/` | Lunaverse IDE 介绍视频（Remotion，v3 final 已交付） | 已交付 |
| `work/lunaverse-app-promo/` | Lunaverse APP 玩家向宣传片（72s 主片 + 30s / 15s 裁剪版） | 迭代中（V8+） |

### lunaverse-intro

Lunaverse IDE 平台介绍视频。v3 为最终交付版本，定稿在本地 `out/lunaverse-intro-final.mp4`。

### lunaverse-app-promo

**72 秒竖屏宣传片**（1080x1920 @30fps，2160 帧）+ 30s / 15s 两个裁剪版。目标观众：北美 18-24 女性、BookTok 言情读者。全程英文 VO + 英文字幕。

核心创意："一掷改命"单线叙事 —— 以 [[concepts/villain-season-demo]] （Heart Signal NA otome）的 main:01 真实桥段为素材，跟随玩家经历选择、掷骰、CG 高光、体感交互、Remix 改写、Dream 支线。所有立绘 / 背景 / CG / SFX / BGM 来自恶人季官方素材包（英文版）。

8 场景分镜：Hook（恶评卡翻转）→ Choice（brave vs safe）→ Roll（bullet-time 骰子运镜，d20 代码重建）→ CG（额头相抵 CG 直出）→ Body（体感 trick 四连）→ Remix（键盘逐字 + AI 判定 + 支线连锁）→ Dream（三年前闪回）→ Endcard（Lunaverse logo + "Roll for it."）。

生产管线 6 阶段：P0 脚手架 → P1 素材 → P2 音频（Breeze TTS 女声 + 角色配音）→ P3 场景（8 场景 agent 并行）→ P4 混音 → P5 渲染交付。执行管线沿用 `skills/remotion-promo-production/SKILL.md`。

迭代历史：23 commits，从 P0 scaffold 经 V1-V8+ 迭代，包含场景重建、VO 重录、kinetic captions、bullet-time 骰子运镜、CG 集成、F Studio 场景等。

## Skills（可复用生产知识）

| Skill | 一句话 |
|---|---|
| `remotion-promo-production` | Remotion 产品宣传片端到端生产线：单一时间轴源、Workflow 多 agent 编排、TTS 质检、ffmpeg 配方、素材热替换、视觉确认纪律 |

`skills/vendor/` 另有 6 个第三方 skill 合集（remotion-skills / gsap-skills / motion-design-skill 等），仅本地参考不入库。

## 素材策略

**所有图片 / 音频 / 视频素材不推 GitHub**（.gitignore 按目录 + 扩展名双重拦截），只推代码与文档。素材位置：

- `work/assets/brand-assets/` — Figma LUNAVERSE-APP 界面导出 PNG
- `work/assets/cg-example-case/` — CG 视频源片
- `work/assets/audio/` — BGM
- `work/assets/villain-season/` — 恶人季完整素材包（7 角色 30 表情 / 6 背景 / 3 BGM / 22 SFX / 4 CG / 配音 voices.json）
- `work/lunaverse-intro/public/` — intro 项目内素材
- 换机器时素材需另行同步（网盘 / AirDrop / 移动硬盘）

## 依赖区（deps/）

17 个 clone 的参考仓库，覆盖 remotion 生态、manim、lottie、视频工具链等。内容不入库，清单与恢复脚本见 `deps/README.md`，一键恢复：`bash deps/restore.sh`。

## 环境变量

| 变量 | 用途 |
|---|---|
| `BREEZE_API_KEY` | Breeze TTS（旁白与角色配音生成） |

根目录 `.env`（gitignored）保存；项目内可自带 `.env`。

## 常用命令

```bash
# lunaverse-intro 渲染
cd work/lunaverse-intro
node scripts/remotion-cli.mjs render LunaverseIntro out/lunaverse-intro.mp4 --codec=h264

# 单帧验证
node scripts/remotion-cli.mjs still LunaverseIntro /tmp/check.png --frame=1730

# 恶人季素材拉取（幂等）
cd work/assets/villain-season && bash fetch-media.sh
```

## 相关

- [[concepts/villain-season-demo]] — 宣传片使用的恶人季素材与剧目设计
- [[entities/lunaverse-ide]] — 宣传片推广的 IDE 产品
- [[entities/lunaverse-backend]] — 宣传片展示的游戏引擎后端
- [[entities/lunaverse-client]] — 宣传片展示的游戏前端
- [[entities/lunascripts]] — 宣传片展示的 LS 脚本格式
- [[entities/assets-produce]] — 资产生产平台（素材来源之一）
