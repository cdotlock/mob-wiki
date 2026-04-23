---
title: Novel GameConfig — Per-Novel Attribute System
tags: [moonshort, backend, schema, game-design]
sources: [raw/2026-04-23-novel-game-config-design.md]
created: 2026-04-23
updated: 2026-04-23
---

# Novel GameConfig — Per-Novel Attribute System

MoonShort 的角色属性配置分两层：**平台级**（跨剧本统一的数值常量）和 **per-novel 级**（每部剧本可以命名自己的连续变量与 4 个检定属性）。这套分层在 2026-04-23 取代了原先硬编码的 SAN/ATK/INT/CHA/WIL 布局，让剧本作者能把主角的"心智可崩溃变量"按剧本起名（理智 / HP / Fate / 心情 / 污秽度 ...），同时把所有跨剧本数值统一收拢到 `app/core/game-rules.ts` 单一文件里。

## 为什么要分两层

改造前的问题：

- **属性硬编码**：`SAN` 以及 `ATK/INT/CHA/WIL` 在 `app/lib/numerical-system.ts` 写死，每部剧本用不了自己的叫法。
- **显示名和内部 key 耦合**：`ATTRIBUTE_DISPLAY_NAMES` 全局硬编码。
- **DB schema 命名歧义**：`Session.san` / `Session.attributes Json` 把特定业务名和泛化容器混用。
- **平台级数值散落**：DC 阶段参数、等级 XP 表、coins / gems / VIP 档位、关系 tier 阈值在 `numerical-system.ts` / `minigame-registry.ts` / `chat-tier.ts` 4~5 个文件里各散各的。

改造的两条目标：

- **per-novel 可配置**：每部剧本可以改 1 个连续变量（SAN-slot）和 4 个检定变量的显示名、`mssKey`、初始值与上限，再加角色创建的 `freePoints`。
- **平台级数值整理**：其他所有数值保持"平台级单一来源"，但不再散落——全部收拢到 `app/core/game-rules.ts`，分 section 组织，admin UI 只读展示。

## Per-Novel 部分：`Novel.gameConfig`

### Zod Schema

文件：`app/core/game-config-schema.ts`

```ts
{
  version: "1.0",
  variables: {
    continuous: {
      mssKey: string,         // MSS 引用连续变量用的 key（默认 "san"）
      label: string,          // 显示名，如 "理智" / "HP" / "Fate" / "心情" / "污秽度"
      initial: number,        // 初始值
      max: number,            // 上限
      dailyReset: number | null,  // 每日重置值；null=不重置
    },
    checking: [               // 恰好 4 项（位置固定为 slot 1~4）
      {
        mssKey: string,       // 对应 MSS check.attr / minigame.attr（大小写不敏感）
        label: string,        // 显示名
        initial: number,
        max: number,          // 通常 = CHECK.attributeHardCap = 24
      },
      /* × 4 */
    ],
    freePoints: number,       // 角色创建自由分配点（通常 2）
  }
}
```

Zod 校验包含：

- `mssKey` 必须匹配 `^[a-z][a-z0-9_]*$i`（字母数字下划线，不能含空格）。
- 4 个 `checking[].mssKey` 不能重复（case-insensitive）。
- `continuous.mssKey` 不能跟任何 `checking[].mssKey` 冲突。
- 每个变量 `initial <= max`。
- `freePoints` ∈ [0, 20]。

### Slot 绑定与 MSS 读取

MSS 契约不动（上游 dramatizer 定义，只读）：

```json
{ "type": "choice", "options": [
  { "id": "o1", "mode": "brave", "text": "挑战", "check": { "attr": "cha", "dc": 12 }, "steps": [] }
]}
```

MSS 里 `check.attr: "cha"` 这个字符串由我方在 `app/lib/game-config.ts` 里解析：

```ts
export function resolveSlot(mssAttr: string, cfg: NovelGameConfig): 1 | 2 | 3 | 4 {
  const normalized = mssAttr.trim().toLowerCase();
  const idx = cfg.variables.checking.findIndex((v) => v.mssKey.toLowerCase() === normalized);
  if (idx < 0) throw new UnknownMssKeyError(mssAttr);
  return (idx + 1) as 1 | 2 | 3 | 4;
}
```

引擎拿到 slot 后就读 `session.checkingVariable{slot}`。大小写不敏感；未匹配抛 `UnknownMssKeyError`（code 4101）。

同名辅助：

- `isContinuousKey(mssAttr, cfg)` — 判断是不是连续变量的 key。
- `resolveAttr(mssAttr, cfg)` — 统一返 `{ kind: "continuous" }` 或 `{ kind: "checking"; slot }`。
- `labelOf(mssAttr, cfg)` — 按剧本配置取显示名，未匹配兜底 `attr.toUpperCase()`。
- `listCheckingSlots(cfg)` — HUD / 角色创建的 4 slot 元数据。
- `attrsFromSession(session, cfg)` — 把 session 的 4 列转成 `{ mssKey: value }` 字典。
- `checkingFieldsFromAttrs(attrs, cfg)` — 反向：把字典转成 Prisma 的 4 列 patch。

### Session 存储

`Session` 表 2026-04-23 起改为扁平 Int 列：

| 新列 | 老列（已删除） | 含义 |
|---|---|---|
| `continuousVariable` | `san` | 当前连续变量值 |
| `continuousVariableMax` | `sanMax` | 连续变量上限 |
| `checkingVariable1` | `attributes[cfg.checking[0].mssKey]` | Slot 1 当前值 |
| `checkingVariable2` | `attributes[cfg.checking[1].mssKey]` | Slot 2 当前值 |
| `checkingVariable3` | `attributes[cfg.checking[2].mssKey]` | Slot 3 当前值 |
| `checkingVariable4` | `attributes[cfg.checking[3].mssKey]` | Slot 4 当前值 |

迁移策略是单次 Prisma migration（`20260423010000_session_continuous_and_checking_variables`）：add new → backfill 用 canonical `atk → int → cha → wil` 顺序映射 attributes JSON → SET NOT NULL → drop old。16 个存量 Session 一次过完。

API 层（`SessionSnapshot` 返给 player）保持 `san / sanMax / attributes` 旧形状，由 `save-service.ts` 动态 join `Novel.gameConfig` 拼出——前端零改动。Admin cheat `/status` 同时暴露新 flat 列 + 旧 map，便于迁移期间透明排查。

### Admin Scan 服务

`app/services/novel-config-scan-service.ts` 提供 `scanNovel(novelId)` / `scanFromEpisodeRecords(records)` / `scanFromEpisodeJsons(episodes)`：

- 递归走 `episode.steps[]`，进入 `choice.options[].steps`、`minigame.steps`、`cg_show.steps`、`if.then / else`；命中 `brave.check.attr` 与 `minigame.attr` 时收集（case-normalized）。
- 返 `{ draft, stats }`：
  - `draft` 是一份 `NovelGameConfig`（canonical `atk → int → cha → wil` 优先、按频次降序、最后字母序；>4 丢弃、<4 用 `DEFAULT_FALLBACK_KEYS = [atk, int, cha, wil]` 补位）。
  - `stats` 包含 `episodesScanned` / `distinctKeysFound` / `allKeys` / `droppedKeys` / `fallbackSlotsAdded` / `frequency`（admin UI 显示警示用）。

离线脚本：`scripts/scan-novel-game-configs.ts` 一次过扫全部 Novel 并落库。

## Platform 部分：`app/core/game-rules.ts`

散落 5 个文件的平台常量（87 个常量）单一来源归集。分 section：

| Section | 内容 | 对应旧位置 |
|---|---|---|
| `CHECK` | 骰子 / 属性上限 / 修正公式 / 小游戏评级修正 | numerical-system / minigame-registry |
| `CONTINUOUS_RULES` | 检定成功/失败变动 / 崩溃阈值 / 复活费用 | numerical-system `SAN` |
| `DIFFICULTY` | 60 集 5 阶段 DC 参数（截断正态分布） | numerical-system `DC_PHASE_PARAMS` |
| `LEVEL` | max=20 / `cumulativeXpTable` / 属性成长节点 | numerical-system `LEVEL` / `CUMULATIVE_XP_TABLE` |
| `CHOICE_XP` | braveSuccess=3 / braveFail=1 / safe=1 | numerical-system `CHOICE` |
| `MINIGAME_XP` | S=2 / A=1 / B=1 / C=0 / D=0 | minigame-registry `XP_BY_RATING` |
| `COINS` | 签到 / 时间恢复 / 每集消耗 / 3 档购买包 | numerical-system `COINS` / `COINS_PACKS` |
| `GEMS` | reroll / drama-remix / plot 奖励 / 4 档充值包 | numerical-system `REROLL` / `DRAMA_REMIX` / `GEMS_PACKS` / `PAYMENT_POINTS` |
| `VIP` | 周卡 / 月卡参数 | numerical-system `VIP_TIERS` |
| `RELATIONSHIP` | tier 阈值 `[0,10,30,80,200]` / 5 档默认称号 | chat-tier |
| `UI` | 每集 130s / 打字机 60cps | numerical-system `EPISODE` |

改值原则：平台数值必须走代码 PR + code review。Admin UI 对这些字段**只读展示**（6 个 KV 卡片 + 一张 DC 曲线 SVG 小图），不提供编辑入口。

`PHASE3:per-novel` 字段（如 `CONTINUOUS_RULES.defaultMax`、`CHECK.defaultStandardArray`）是迁移过渡期的平台默认值；Phase 3 落地后已被 per-novel `Novel.gameConfig` 覆盖，保留是为了 admin 未配置剧本的兜底。

## Admin UI `/admin/novels/[id]/game-config`

### 编辑区

- 连续变量 1 行（5 个输入）：`mssKey` / `label` / `initial` / `max` / `dailyReset`（`-1` = 不重置）。
- 4 个检定变量（每个 4 个输入）：`mssKey` / `label` / `initial` / `max`。
- `freePoints` 1 个输入。
- **[扫描 MSS]** 按钮：调 `POST /api/admin/novels/[id]/game-config/scan`，只覆盖 4 slot 的 `mssKey`，保留用户已编辑的 `label`。扫描后顶部出现 amber 提示条显示 episode 数 / 抽到 key / 频次 / 丢弃 / 补位。

### 只读卡片 + 可视化

6 个 KV 卡片：检定规则 / 连续变量规则 / 等级-XP / 体力 / Gems / 关系 tier。
SVG 折线图：60 集 DC mean 曲线，5 阶段用淡色背景带标出。

### 后端

| Endpoint | 作用 |
|---|---|
| `GET /api/admin/novels/[id]/game-config` | 返 `{ novel, gameConfig, platform }`；gameConfig 经 Zod 校验，空 `{}` 返 `getDefaultGameConfig()`；platform 是 `game-rules` 的只读采样 |
| `POST /api/admin/novels/[id]/game-config/scan` | 跑 `scanNovel`，返 `{ draft, stats }`，不落库 |
| `PATCH /api/admin/novels/[id]/game-config` | 整份 gameConfig Zod 严校验后整体覆盖；错误返 `1001` + 聚合 zod 报错 |

所有接口 `requireAdmin`（cookie `noval_admin=<HMAC>`）。

## Cheat API 行为

`POST /api/admin/cheat/set-attr`：
- `attr: "SAN"` → `continuousVariable`
- `attr: "SANMAX"` → `continuousVariableMax`
- `attr: "XP"` / `"LEVEL"` → 同名列
- 其他 `attr` 字符串 → `resolveSlot(attr, cfg)` 落 `checkingVariable{slot}`
- 未匹配 → code `4101` `UnknownMssKeyError`，信息里附 `gameConfig.variables.checking[].mssKey` 全集

`GET /api/admin/cheat/status`：同时返老形状（`san / sanMax / attributes`）和新形状（`continuousVariable / continuousVariableMax / checkingVariable1~4 / gameConfig`）。

## 迁移时间线（2026-04-23）

一次 PR，5 个阶段，分 commit：

1. **Phase 1**：`app/core/game-rules.ts` 落地，`numerical-system / minigame-registry / chat-tier` 瘦身为只留纯函数，全局 import 重写。
2. **Phase 2**：`game-config-schema.ts` + `game-config.ts` + `novel-config-scan-service.ts` 加核心 lib；Novel 列 `attributeConfig → gameConfig` 改名；API 形状切换成 `NovelGameConfig`（frontend new-session 页跟改）。
3. **Phase 3**：Session 列 `san/sanMax/attributes` → `continuousVariable/Max + checkingVariable1~4`；save-service / save-action-service / cheat routes 跟改；离线 scan 脚本一次性回填 4 个 Novel 的 gameConfig。
4. **Phase 4**：Admin API 3 路由 + 编辑页面 + dashboard "属性配置" 入口。
5. **Phase 5**：归档旧 `docs/archive/numerical_design.md` 并加新指针；入 wiki。

全程 `tsc --noEmit` 零错误、140 单测 / 集成测全绿。生产数据单刀完成无双写、无过渡期。

## 设计记录

### 为什么 MSS 保持只读？

MSS 由 dramatizer 上游产出。改 MSS 契约要跨服务发版，成本太高。`mssKey` 让适配职责留在我方——scan 自动发现新 key 几乎零运维成本。

### 为什么 Session 用 4 个扁平列而不是 JSON？

位置固定 4 slot，JSON 带来的好处（动态字段）用不到；扁平 Int 列索引友好、类型安全、cheat 接口简单。连续变量同理独立为 `continuousVariable / continuousVariableMax` 两列。

### 为什么平台数值不进 gameConfig？

DC 曲线、XP 表、coins/gems/VIP 改动会冲击玩家经济平衡——不能让剧本作者随便改。代码常量保留 git 审计 + PR review。剧本间要求数值一致（A/B 测试另走 `feature-flag` 机制，不是 per-novel override）。

### 为什么不做向后兼容层？

用户明确要求"大刀阔斧"。离线 scan 已预生成所有新配置，Session 回填是纯函数无并发风险。保留兼容层只会让代码久而不可读。

## 相关页面

- [[concepts/mss-format]] — MoonShort Script 脚本格式
- [[entities/moonshort-backend]] — 后端总览
- [[entities/dramatizer]] — MSS 上游产出链

## Sources

- [2026-04-23 novel-game-config design spec](../../raw/2026-04-23-novel-game-config-design.md)
