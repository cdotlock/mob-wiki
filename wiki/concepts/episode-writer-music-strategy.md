---
title: Episode Writer · BGM 策略 & music-normalizer 流程
updated: 2026-05-07
tags: [novels-to-moonscript, dramatizer, music, normalization, mss]
---

# Episode Writer · BGM 策略 & music-normalizer 流程

> 适用范围:novels-to-moonscript 系列(no-rules-in-bad-ideas + 后续 N 部小说)
>
> 关联仓库:`novels-to-moonscript`(skill + dramatizer 实现);`moonshort-script`(mss 二进制,本流程**不动**)
>
> 完整设计:`novels-to-moonscript/docs/superpowers/specs/2026-05-07-music-normalizer-design.md`

## TL;DR

剧本里 LLM 给每个 BGM 起了几百个语义名(`theme_bedroom_late_night` 之类),但
实际可用 BGM 只有 N 首(本系列默认 5 首)。本机制把语义名归一化到 N 类调色板,
并实现"心动单次播放 → 自动切回 daily 兜底"的运行时行为,**不改 mss spec、
不改 Go 编译器、不改源 .md、不依赖前端实现细节**。

新书接入(零代码改动):
1. 投递 N 个 mp3 到 `dramatizer/raw_audio/<slug>/`
2. 复制 `dramatizer/configs/_template.yaml` 为 `<slug>.yaml`,改 palette
3. `python3 -m skills.music-normalizer <slug>` 自动分类 → `alias_map.json`
4. 人审 `normalize_report.md` 的 low/med-confidence 项
5. `python3 -m dramatizer.build <slug>` 自动跑通整套

## 架构(三层)

```
   05-episode-writer (源剧本,353 个语义名)
        │
        ▼
  ★ skills/music-normalizer + moonscripts/<slug>/05.5-music-normalizer/
        │  alias_map.json (name → category) + normalize_report.md
        ▼
   dramatizer/build.py(扩展 3 个 step)
   ├─ stage_music   :  raw_audio/<slug>/*.mp3 → assets/<slug>/music/
   ├─ build_music_mapping : alias_map + palette → mapping.json music 段
   └─ music_postprocess : staging .md 注入 cleanup crossfade
        │
        ▼
   compile_mss(照旧,完全不感知音频后处理)
```

**关键边界**: skill 只产出数据(alias_map),dramatizer 消费数据。两边解耦。

## 设计 Q&A(为什么不是别的方式)

### 为什么 BGM 用 N 类调色板而不是更多?

- **人耳记忆**:玩家在一集内能区分的 BGM 切换在 5-7 首,超过会变成"听不出差别"
- **情绪锚定**:同一首 BGM 反复出现 = 情绪信号锚点(主旋律每次回归 = 一贯主题)
- **制作成本**:每首 BGM 1 分钟以内 ≈ N×100-500 USD,N=5 已经是性价比甜点
- **可扩展**:配置驱动,N 不是硬编码,需要 8 / 10 都行

### 为什么多对一 mapping 而非改写脚本里的名字?

剧本里的 LLM 自由命名(几百个)是有意义的——每个名字带具体场景上下文。
丢掉这些名字 = 丢失"这首 BGM 在该场景被认为是什么情绪"的训练信号。
保留名字 + mapping 多对一可以让我们将来加 BGM 时再跑一次 normalizer
而不必重写脚本。

mss spec 的 mapping 是 `<name>` → URL string,允许"不同 name 指
同一 URL"。多对一不破坏任何兼容契约。

### 为什么 `once_then_default` 用 dramatizer 后处理而非 mss 新指令?

候选了 4 种实现:

| 方案 | 改动面 | 否决理由 |
|---|---|---|
| 给 mss 加 `@music once` 指令 | mss spec + Go 二进制 | 跨仓库改动,作者要在 cdotlock/moonshort-script 重发 |
| URL 加 `?loop=false` query | 仅 mapping | 依赖前端 player 实现,我们不可控 |
| 脚本里手写 `play X → fadeout → crossfade daily` | 仅 .md | 把"播一次"语义和具体音乐绑死,LLM 写起来啰嗦 |
| **dramatizer 编译前注入 cleanup**(选用) | dramatizer pipeline | 闭环在我们仓库内,不动 mss / 不动前端 / 不动源 .md |

后处理 = 改造 staging .md 临时副本 + 编译,源文件零改动,可关闭(空 yaml music 段)。

### 插入位置规则的设计权衡

后处理插入 cleanup crossfade 时有 3 种位置:
1. **BEAT 边界**(@bg / @cg / @phone)— **首选**
2. **对话块开头**(NARRATOR / `<CHAR>:`)— **fallback**
3. **window_max 强制兜底**

为什么这三层?
- BEAT 是场景切换,语义最干净——心动音乐在场景切换时停 = 自然
- 对话边界是 fallback,因为某些场景内有大段对话没有 BEAT
- 强制兜底处理"心动 → 集尾"边界(否则会循环到下一集 set 新 BGM 才停)

`window_min=4` / `window_max=30` 是经验值,代表 ~15s ~ ~2min 的播放窗口,
可在 yaml 中调。

跳过条件:如果 cleanup 窗口内剧本已经手写了 `@music play/crossfade/fadeout`,
就不重复注入。

## 实测数据(no-rules-in-bad-ideas)

跑完一次 normalizer + 全 build 的实测:

- **统计**:348 unique 语义名,416 occurrences,159 个 .md(中英双语)
- **分类分布**:
  - daily(默认): 178 (51.1%)
  - bittersweet: 67 (19.3%)
  - theme: 35 (10.1%)
  - flutter: 34 (9.8%)
  - tension: 34 (9.8%)
- **注入统计**:70 处 cleanup crossfades 跨 46 个文件
  - BEAT 锚点:10
  - DIALOGUE 锚点:60
  - FORCED 锚点:0
- **LLM**:`claude-sonnet-4-6`,9 个 batch × ~10s,总时长 ~1 分钟,$0.5 量级

## 与项目其他归一化机制的类比

| 归一化对象 | skill | 多对一? | 输出 |
|---|---|---|---|
| 角色名(原著名 → 标准 ID) | `entity-normalizer` (04) | 是(别名 → ID) | characters.json |
| 角色名(版权脱敏改名) | `entity-rename` (04.5) | 否(标准 ID → 新 ID) | rename_map.json |
| BGM 语义名(几百 → N) | **`music-normalizer`** (5.5b) | **是**(几百 → N) | music_alias_map.json |
| 服装一致性 | `wardrobe-consolidator` (5.5) | 否(verify only) | bible patch |
| 图片素材 | `asset-prompt-generator` (06) | 一对一(stem ↔ PNG) | tasks_output.json |

## 配置文件示例(no-rules-in-bad-ideas)

```yaml
music:
  source_dir: ../raw_audio/no-rules-in-bad-ideas/
  palette:
    theme:
      file: 01_theme.mp3
      strategy: loop
      description: 主旋律,关键时刻 / 情感高潮 / 集尾余韵
    flutter:
      file: 02_theme-flutter.mp3
      strategy: once_then_default     # ← 心动单次播放语义
      description: 心动瞬间(角色情感升温的具体时刻)
    bittersweet:
      file: 03_theme-bittersweet.mp3
      strategy: loop
      description: 悲伤 / 苦涩 / 失落 / 离别
    tension:
      file: 04_tension.mp3
      strategy: loop
      description: 紧张 / 对峙 / 冲突 / 危险预兆
    daily:
      file: 05_daily.mp3
      strategy: loop
      is_default: true
      description: 日常 / 无情绪起伏 / 不确定就归这里
  postprocess:
    insert_window_min: 4
    insert_window_max: 30
    default_anchor: _bgm_default
```

## 新书接入 checklist

```bash
# 1. 准备 mp3
mkdir -p dramatizer/raw_audio/<slug2>/
cp ~/Downloads/bgm/*.mp3 dramatizer/raw_audio/<slug2>/

# 2. 写配置
cp dramatizer/configs/_template.yaml dramatizer/configs/<slug2>.yaml
# 编辑 yaml,填 palette(N 个调色板项),strategy 自由组合 loop / once_then_default

# 3. 跑 normalizer 自动分类
python3 -m skills.music-normalizer <slug2>

# 4. 人审 normalize_report.md(看 low / med-confidence 项)
open moonscripts/<slug2>/05.5-music-normalizer/normalize_report.md

# 5. 跑完整 build
python3 -m dramatizer.build <slug2>

# 验证产物
cat dramatizer/build/<slug2>/music_inject_report.md
```

## 失败模式

| 症状 | 原因 | 修法 |
|---|---|---|
| build fail: "music config present but alias_map missing" | 没跑 normalizer | 跑 `python3 -m skills.music-normalizer <slug>` |
| build fail: "exactly one is_default" | yaml palette 配置错 | 检查 yaml,确保恰好一个 is_default: true |
| build fail: "mp3 file not found" | 文件路径错或没投递 mp3 | 检查 source_dir 和文件名 |
| inject_report 注入数量 = 0 | once_then_default 类全部已被剧本自行 crossfade 切走(意味着 LLM 写脚本时已正确处理) | 这是好事,意味着剧本质量高,不需修复 |
| inject_report 注入数量异常多 | 剧本里大量 flutter 出现且无后续 crossfade | 检查 yaml 里 strategy: once_then_default 的描述是否过于宽泛(LLM 把不该是心动的也分到 flutter) |
| LLM 分类质量差 | yaml 里 description 太模糊 | 改 description 加具体场景例子 |

## 测试覆盖

```bash
# Pipeline 模块(dramatizer 侧)
PYTHONPATH=. pytest dramatizer/tests/test_music_config.py \
                    dramatizer/tests/test_stage_music.py \
                    dramatizer/tests/test_music_mapping.py \
                    dramatizer/tests/test_music_postprocess.py -v
# 24 个测试

# Skill 模块
pytest skills/music-normalizer/tests/ -v
# 13 个测试,含 mock LLM 的端到端 orchestrator 测试
```

## 引用

- 完整设计文档:`novels-to-moonscript/docs/superpowers/specs/2026-05-07-music-normalizer-design.md`
- 实现 plan:`novels-to-moonscript/docs/superpowers/plans/2026-05-07-music-normalizer.md`
- skill SKILL.md:`novels-to-moonscript/skills/music-normalizer/SKILL.md`
- mss-spec(指令格式):`novels-to-moonscript/skills/episode-writer/mss-spec.md`
- 相关概念:[[concepts/mss-format]]、[[entities/dramatizer]]、[[entities/dramatizer-mss]]
