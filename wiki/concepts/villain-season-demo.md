---
title: Villain Season — Heart Signal Otome Demo
tags: [demo, content, villain-season, dreaming, ls, tts, onboarding]
sources: [raw/2026-05-30-villain-season-readme.md]
created: 2026-05-30
updated: 2026-05-30
---

恶人季是 [[entities/lunaverse-backend]] 2026-05 落地的 **平台 demo 兼新玩家教学**：Heart Signal 设定 NA otome 短剧，3 集 + 1 dream，端到端展示当前所有 player-facing 机制。**双重用途**：新玩家教学 + 投资人演示。源 README：[`lunascripts/villain-season/README.md`](https://github.com/cdotlock/lunaverse-backend/blob/main/lunascripts/villain-season/README.md)。

## 双 novel 并行

**两本平行 novel，行为完全一致**（同素材 / 同 dream 链 / 同成就 / 同小游戏）：

| novelId | 语言 | 剧本目录 | 配音 | 用途 |
|---|---|---|---|---|
| `villain-season` | 英文 | `scripts-en/` | ✅ 英文 Breeze 配音 + TTS 已生产 | 上线版 |
| `villain-season-zh` | 中文 | `scripts-zh/` | ❌ 无（中文嗓音未到位） | 留档 / 对照版 |

为什么分两本：配音只接了英文。中文本保留原始中文台词留档，但不挂英文嗓音（不让英文 TTS 念中文）。两本是各自独立的单本 novel，不是 i18n 同一本。

## 流程图（Dream 100% 自动）

```
main:01  恶人入场 → 互读恶评 ×2 → 第一玫瑰 → 3 场约会 → 淘汰 → Final Rose → cliffhanger 分支独白
  (~10 min)   末尾 bonus_only overlay 追加 Continue + ✦DREAM 两个选项
      ├─ Continue → mp:01
      └─ ✦DREAM → dream/three_years_ago:01
                      Remix→梦境教学 → 入梦 → 三年前公寓 → 同时不开口 → 醒来 → "另一个是我自己" + epic 成就
                      @gate → mp:01
mp:01    匹配 Avery → 重放 Kai 真假 → 双方投票 → 合并演出 → 加好友
  (~3 min)    @ending complete
```

每次 `createSession` 都自动挂载 dream（不需要手动 `/api/admin/dreaming/assign`）：

- `Dream.entryPatch.autoAssign: true` —— `app/services/dream-autoassign-service.ts` 在 post-commit 阶段 best-effort 建 DreamAssignment（`(sessionId, dreamId)` 幂等）
- `Dream.entryPatch.operations: [{ op: "bonus_only", optionFlavor: ... }]` —— runtime [[concepts/dream-bonus-only-op]] applier 追加 Continue + ✦DREAM 两个选项

ZH 本：`Dream.branchKey` 全局唯一，英文本占了 `dream/three_years_ago`，中文本用 `dream/three_years_ago#zh`；路由靠 dreamId + entryEpisodeId，不受影响。

## 一键 seed

```bash
pnpm seed:villain-season:full     # build + seed 两本
# 拆开
pnpm seed:villain-season:en
pnpm seed:villain-season:zh
```

链：
1. `pnpm build:villain-season` —— `lsc compile` 双语脚本 → `compiled/compiled.en.json` + `compiled.zh.json`；**校验**每个引用素材都在官方 `mapping.json` 里（缺一个硬失败）
2. `pnpm seed:villain-season` —— 两本都 upload to OSS + upsert `Novel` / `Episode` / `Dream` + 角色名册 + （英文本）配音 + `NovelProductionRelease` stub

依赖：`lsc` binary（本地 dialect 版，支持 `@trick` + 旧 `@minigame`，默认 `/Users/Clock/.local/bin/lscc`，env `LS_BIN` 覆盖）。**上游 v2.4 HEAD 编不了这剧本**（用了本地 dialect 才有的 `@trick`）。后端 healthy + OSS 凭证在 `.env`。

## 素材清单

`compiled/mapping.json` 是同事产出的**官方** asset mapping（不再是 feature-parade 占位）。所有 URL 真图真音，OSS 前缀 `lianzong/`：

| 类别 | 数量 | 形态 |
|---|---|---|
| bg 背景 | 6 | `lianzong/backgrounds/*.png` |
| characters 立绘 | 7 角色 / 30 looks | `lianzong/characters/<slug>/<look>.webp` |
| music BGM | 3 | `house-variety_show` / `rnb-dating_tense` / `indie-love_certain` `.mp3` |
| sfx 音效 | 22 | `lianzong/sfx/*.mp3` |
| minigames | 1 | `qte_challenge` |

**重要**：`build:villain-season` **不再生成 mapping** —— 它是手动维护的权威文件，build 只做 "引用 ⊆ mapping" 校验。改素材名：改 `.ls` → rebuild → 报哪个引用缺图。

### qte_challenge 小游戏

真 Phaser 包在 `public/minigames-play/qte-challenge/`（`index.html` + `phaser.min.js`），由后端 same-origin serve（OSS 对 HTML 强制下载，iframe 加载不出来）。seed 时 `rewriteMinigameUrls` 把 `game_url` 改写成 `/minigames-play/qte-challenge/index.html`；mapping 里那条 minigame 路径不进 DB（`assetMapping` schema 只收 URL），运行时不依赖它。

## 配音（仅英文本）

`voices.json` （同事交付）= 8 个 Breeze `bluebell-v1-en` 稳定 voiceId。`seed:villain-season:en` 落 DB：

- `Novel.narratorVoiceId` + `Novel.mcVoiceId`（旁白 + YOU = Mia）
- 7 角色 → `NovelCharacter` + 唯一 active `CharacterVoiceProfile`（`voc_` id）
- 8 voiceId → `VoiceCatalogCache`（`voiceDescription` 作为 voicePersona 进 per-line TTS 指令）

电话短信发信人（`manager` / `unknown` / `heart_signal_app`）不是真角色、`voices.json` 没给声音 —— prerender 时用旁白嗓音兜底（`scripts/prerender-villain-tts.ts`）。

### 生产 TTS（英文本）

```bash
pnpm tts:up                  # 起 services/tts（docker）
pnpm prerender:villain-tts   # 入队 3 集 + 等渲染完；音频落 Cloudflare R2
```

`rebuild:false` 幂等：按 `textHash` 比对，只重渲染**文本变了**的行。改一句台词 → reseed → 重跑 prerender，不会重花整本 Breeze 调用。

## 教学层配比

demo 双重用途要求"边玩边教"：**Remix + Dream 重点教**，**trick 轻提示**，其它展示即可。

| 机制 | 教学方式 | 位置 |
|---|---|---|
| **Remix Anywhere** ⭐ | 2 行旁白讲清 what/why/how + "改写会真的留在存档、后面人物会记得" | Round 1 首次出现 |
| **Dream 系统** ⭐ | main 末尾 ✦pill 前引导旁白 + dream 开头教学：**Remix 触发 → 顺着你的玩法专为你生成的一段支线 → 希望你享受其中** | main:01 末尾 / dream 开头 |
| **@signal** | 第一个 signal 处「因你独特选择触发隐藏剧情」+ 排名处兑现 | Round 2 / 排名 |
| **@signal int** | 「胆识 +1，跨集累积、影响隐藏判定」 | 首次 brave 成功 |
| **@trick** | 1 行轻提示「跟着屏幕提示做」 | 首个 trick 前 |
| **@minigame** | 1 行轻提示「可玩可跳、翻到哪张只是包装」 | 互读恶评开场 |

2026-05-30 改版梦境教学措辞：不再说"不 Remix 就遇不到的隐藏剧情"，改成 "Remix 触发 / 为你定制生成 / 希望享受"。4 处同步（EN+ZH 的 dream 开头 + main:01 末尾）。

## 机制覆盖总览

| LS 指令 | 用了 | 说明 |
|---|---|---|
| `@episode <branch_key> <title> { }` | ✅ ×3 | main:01 / dream/three_years_ago:01 / mp:01 |
| `@gate { @else: @next ... }` | ✅ ×2 | main → mp, dream → mp |
| `@ending complete` | ✅ ×1 | mp:01 |
| `@bg set <name> [fade]` | ✅ 多次 | default dissolve + `fade` |
| `@music play / crossfade / fadeout` | ✅ 多次 | 3 首 BGM |
| `@sfx play <name>` | ✅ 22 种 | |
| `@<char> show <look> at <pos>` / `look` / `hide` | ✅ | 30 looks |
| `@<char> bubble <type>` | ✅ ×3 | jace heart / kai sweat / mia doom |
| `CHARACTER [look]:` 语法糖 / `YOU:` / `NARRATOR:` | ✅ 多次 | |
| `@phone show { @text from <char>: }` | ✅ 多段 | manager / unknown / heart_signal_app |
| `@pause for N` | ✅ | 沉默节奏 + cliffhanger |
| `@choice { brave / safe }` + `check { attr / dc }` | ✅ ×8 | bold / sweet / smart |
| `@if (check.success) {} @else {}` / 顶层 flag 链 | ✅ | |
| `@affection <char> +N` | ✅ | 4 个 LI |
| `@butterfly "..."` | ✅ 15+ | LLM influence judgment |
| `@signal mark` / `@signal int boldness +N` | ✅ 17 / ×3 | |
| `@achievement NAME { name/rarity/description }` | ✅ 6 个 | rare / uncommon / epic（含 dream 的 epic） |
| `@trick hold / swipe` | ✅ | Jace 天台 / Ethan 告白室 |
| `@minigame <name> "<desc>"` | ✅ ×1 | qte_challenge（cosmetic，可玩可跳） |
| `&` 并发前缀 | ✅ 多次 | 场景切换三件套同步 |

| Engine / Backend 机制 | 用了 |
|---|---|
| Dream `bonus_only` overlay | ✅ 真 overlay：seed 建 Dream row + entryPatch；runtime apply-overlays 追加 Continue + ✦DREAM |
| DreamAssignment (autoAssign) | ✅ createSession 自动挂；runtime 断言验证（两本） |
| STORY 成就 JIT unlock | ✅ inline metadata 建 PlayerAchievement |
| D20 检定 | ✅ `D20 + attr 修正 >= DC` |
| 跨集路由 | ✅ main → dream → mp |
| NovelProductionRelease stub | ✅ 否则 `/api/novels` 过滤掉 |
| OSS upload + episode JSON 持久化 | ✅ |
| **英文 TTS 产出**（Breeze + R2） | ✅ 英文本 569 行音频；电话短信发信人用旁白嗓音 |
| **角色名册 + 头像** | ✅ 两本 7 人；Mia 真图 + 6 占位 |

## 验证

```bash
pnpm verify:villain-dream
```

断言覆盖（两本都跑，含**真 createSession runtime 自动挂载断言**）：novel/release / 封面+元信息 / 7 人名册+主角头像 / 3 集 / Dream autoAssign+generic bonus_only / **runtime createSession 真的挂出对应 DreamAssignment** / （英文本）配音 + TTS 产出。

## 没演到的（明确划掉）

| 没用 | 为什么 |
|---|---|
| `@cg show` | demo 没视频管线 |
| `@label / @goto` | spec 标注 "高级慎用" |
| `@trick tap / shake / swing / tilt` | hold + swipe 已够 |
| `@ending bad_ending` | demo 不需要 bad route |
| Remix 真长按 → LLM splice | CLI 不支持长按；用 4th-wall NARRATOR 提示代替 |
| MP `NovelMultiplayerConfig` + matchmaking | mp:01 是 SP backend + 叙事假装 MP |
| GLOBAL / REALTIME 成就 | demo 单 user 不演 |

## 文件清单

| 文件 | 用途 |
|---|---|
| `scripts-en/{main_01,dream_three_years_ago_01,mp_01}.ls` | 英文剧本 ×3（上线 / 配音） |
| `scripts-zh/{...}.ls` | 中文剧本 ×3（留档 / 对照） |
| `compiled/compiled.en.json` / `compiled.zh.json` | 各自编译产物 |
| `compiled/mapping.json` | **官方** asset map（真 OSS URL，手动维护） |
| `voices.json` | 8 个 Breeze 英文 voiceId（同事交付） |

build / seed / verify scripts：
- `scripts/build-villain-season.mjs` — 双语 lsc compile + 引用校验（不生成 mapping）
- `scripts/seed-villain-season.ts` — 两本 OSS upload + Novel/Episode/Dream + 名册 + （英文）配音 + release stub
- `scripts/prerender-villain-tts.ts` — 英文本 TTS 入队 + 等渲染（电话短信→旁白嗓音）
- `scripts/verify-villain-dream-forced.ts` — 两本端到端验证（含 runtime auto-load）
- `app/services/dream-autoassign-service.ts` — session 开档自动挂 dream（mini Phase-4 recommender）

## 已知局限

- **DC 偏硬**：BOLD=11 vs DC=8/10 仍 30%-50% fail；低 roll 时成就可能解锁不全
- **新手教学 Remix Anywhere 是 4th-wall 旁白提示**（不是真 long-press 教学覆层）
- **中文本无配音**：英文 TTS only；中文本 TTS 等中文嗓音到位再补

## 相关

- [[concepts/dream-bonus-only-op]] — 自动挂的 dream entry 用的 op
- [[concepts/dreaming-universe]] — 父系统
- [[concepts/remix-anywhere]] — demo 教学的重点机制
- [[entities/lunaverse-backend]] — 全部 service / API / seed 脚本所在地
