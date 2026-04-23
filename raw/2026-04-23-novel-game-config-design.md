# Novel 属性配置 + 平台数值整理 —— 设计文档

**日期**：2026-04-23
**作者**：cdotlock + Claude
**状态**：Draft（待用户评审）
**关联**：取代 `docs/archive/numerical_design.md` v7.1

---

## 1. 背景与目标

### 1.1 当前问题

- **属性硬编码**：`SAN` / `ATK`/`INT`/`CHA`/`WIL` 写死，每部剧本用不了自己的叫法
- **显示名和内部 key 耦合**：`ATTRIBUTE_DISPLAY_NAMES` 全局硬编码
- **DB schema 命名歧义**：`Session.san` / `Session.attributes Json` 把特定业务名和泛化容器混用
- **平台级数值散落**：DC 阶段、等级 XP 表、coins/gems/VIP、关系 tier 阈值 …… 全是顶层 `export const` 散在 4~5 个文件里，没有分组
- **剧本作者无法自定义属性名**：没有 admin UI

### 1.2 目标（两件事，划清边界）

**A. per-novel 可配置** —— 只包括连续变量（SAN-slot）和 4 个检定属性：
- 连续变量的显示名 / `mssKey` / 初始值 / 上限 / 每日重置值
  - label 可按剧本改：默认 "SAN/理智"，也可以叫 "HP"、"Fate"、"心情"、"污秽度" 等
  - mssKey 对应 MSS 里引用连续变量用的 key（默认 "san"；换剧本可能是 "hp" 等）
- 4 个检定属性各自的显示名 / `mssKey` / 初始值 / 上限
- 角色创建的自由分配点（`freePoints`）

**B. 平台级数值整理** —— 其他所有数值保持"平台级单一来源"，但**不再散落**：
- 收拢到一个 `app/core/game-rules.ts` 文件，分 section 组织
- 全部是 TS `const`，编译期固定；改值需要发布代码
- admin UI 可**只读展示**这些值（用于运营 / 调优观察）
- **包括 XP**：XP 也是一种连续变量，但它是跨剧本通用的（所有剧本共用同一套等级/XP 表），归 `LEVEL` 常量，不进 per-novel 配置

### 1.3 非目标

- **其他数值不做 per-novel 配置**：DC 曲线、XP 表、coins/gems/VIP、关系 tier、UI 参数、Influence 规则 …… 全部是平台级，剧本不能覆盖
- **不给 admin UI 编辑平台级数值**：改这些要走代码 PR（保留 git 审计 + code review）
- **不改 MSS 契约**：MSS 由上游 dramatizer 产出，我方只读
- **不留向后兼容层**：大刀阔斧一次切

---

## 2. 核心术语

| 术语 | 含义 |
|---|---|
| **continuousVariable**（连续变量） | 会随检定涨落、可能崩溃的变量，per-novel 可改名（SAN / HP / Fate / 心情 / ...）。XP 虽概念上也是连续变量，但它跨剧本统一，不走这条路径 |
| **checkingVariable1~4**（检定变量 1~4） | D20 检定用的 4 个能力值，位置固定 |
| **MSS key** | MSS 脚本里 `check.attr` / `minigame.attr` 的字符串（如 `"cha"`）。由上游决定，我方只读 |
| **slot** | 4 个 `checkingVariable` 的位置编号 1~4；通过 `mssKey` 字段绑定一个 MSS key |
| **Novel.gameConfig** | per-novel 的属性配置 JSON，只含属性信息（见 §4） |
| **平台数值（game-rules）** | 跨剧本统一的数值常量，集中在 `app/core/game-rules.ts`（见 §5） |

---

## 3. 数据模型变更

### 3.1 Novel 表

```prisma
model Novel {
  id          String   @id @default(cuid())
  // ...
  gameConfig  Json     @default("{}")        // 只含属性配置，见 §4
  // ...（其他字段不变；attributeConfig 删除）
}
```

### 3.2 Session 表

```prisma
model Session {
  // ...
  continuousVariable    Int      // 原 san
  continuousVariableMax Int      // 原 sanMax

  checkingVariable1     Int      // slot 1
  checkingVariable2     Int      // slot 2
  checkingVariable3     Int      // slot 3
  checkingVariable4     Int      // slot 4
  // 旧 san / sanMax / attributes 删除
}
```

**Slot 如何绑 MSS key**：
- MSS 给 `{ "check": { "attr": "cha", "dc": 12 } }`
- 查 `gameConfig.variables.checking.findIndex(v => v.mssKey === "cha")` → 索引 2 → slot 3
- 读 `session.checkingVariable3`

### 3.3 迁移方式（单次大刀阔斧）

1. 离线扫描所有 Novel 的 Episode JSON → 抽出 MSS key → 生成每个 Novel 的 `gameConfig`
2. 一次 Prisma migration：加新列、删旧列、数据回填（migration 内嵌 SQL）
3. 代码切换同一 PR 合入
4. 无双写、无过渡期

---

## 4. `Novel.gameConfig` Schema（**只含属性**）

```ts
{
  version: "1.0",
  variables: {
    continuous: {
      mssKey: string,          // MSS 里连续变量的 key（当前 "san"）
      label: string,           // 显示名，如 "理智"
      initial: number,         // 初始值
      max: number,             // 上限
      dailyReset: number | null, // 每日重置值；null=不重置
    },
    checking: [                // 恰好 4 项 tuple
      {
        mssKey: string,        // MSS check.attr / minigame.attr 的 key
        label: string,         // 显示名
        initial: number,
        max: number,
      },
      // × 4
    ],
    freePoints: number,        // 角色创建自由分配点
  }
}
```

**就这些**。没有其他 section。

Zod schema 放 `app/core/game-config-schema.ts`。

示例（当前剧本 scan 结果）：
```json
{
  "version": "1.0",
  "variables": {
    "continuous": { "mssKey": "san", "label": "理智", "initial": 100, "max": 100, "dailyReset": 100 },
    "checking": [
      { "mssKey": "atk", "label": "力量", "initial": 10, "max": 24 },
      { "mssKey": "int", "label": "智力", "initial": 13, "max": 24 },
      { "mssKey": "cha", "label": "魅力", "initial": 14, "max": 24 },
      { "mssKey": "wil", "label": "意志", "initial": 15, "max": 24 }
    ],
    "freePoints": 2
  }
}
```

---

## 5. 平台数值整理（`app/core/game-rules.ts`）

### 5.1 目标

把当前散在 5 个文件的**剧本无关**数值常量**收拢到一个 TS 文件，分 section 组织**。值保持不变，只重新组织。

### 5.2 文件结构

```ts
// app/core/game-rules.ts

// ──────── 检定规则 ────────
export const CHECK = {
  dice: "D20",
  attributeHardCap: 24,
  modifierFormula: { offset: 10, divisor: 2 },
  minigameModifierByRating: { S: 3, A: 1, B: 0, C: -1, D: -1 },
} as const;

// ──────── 连续变量规则（SAN 机制）────────
export const CONTINUOUS_RULES = {
  successBonus: 5,
  failPenalty: -20,
  crashThreshold: 5,
  crashRecoveryCostGems: 50,
  inPlaceRecoveryCostGems: 100,
} as const;

// ──────── 难度曲线 ────────
export const DIFFICULTY = {
  totalEpisodes: 60,
  seed: 42,
  phases: [
    { name: "开篇", range: [1, 6],   mean: 10, stddev: 1.0, min: 8,  max: 12 },
    { name: "铺垫", range: [7, 20],  mean: 11, stddev: 1.5, min: 8,  max: 13 },
    { name: "转折", range: [21, 35], mean: 14, stddev: 1.5, min: 11, max: 16 },
    { name: "高潮", range: [36, 55], mean: 17, stddev: 1.5, min: 15, max: 20 },
    { name: "结局", range: [56, 60], mean: 12, stddev: 1.0, min: 10, max: 14 },
  ],
} as const;

// ──────── 等级 & XP ────────
export const LEVEL = {
  max: 20,
  cumulativeXpTable: [0, 0, 6, 13, 20, 28, 36, 45, 54, 64, 74, 82, 90, 99, 108, 117, 125, 133, 141, 149, 156],
  attributeGrowthLevels: [2,3,4,5,6,7,8,9,10,11,13,15,17,19],
} as const;

// ──────── 每集 XP ────────
export const CHOICE_XP = { braveSuccess: 3, braveFail: 1, safe: 1 } as const;
export const MINIGAME_XP = { S: 2, A: 1, B: 1, C: 0, D: 0 } as const;

// ──────── 体力（Coins）────────
export const COINS = {
  dailySignin: 200,
  dailyFreeCap: 400,
  timeRecoveryMax: 200,
  timeRecoveryIntervalSec: 144,
  timeRecoveryAmount: 1,
  costPerEpisode: 10,
  packs: [
    { id: "coins_small",  priceGems: 100, coins: 150 },
    { id: "coins_medium", priceGems: 250, coins: 425 },
    { id: "coins_large",  priceGems: 450, coins: 900 },
  ],
} as const;

// ──────── Gems ────────
export const GEMS = {
  reroll: { costGems: 30 },
  dramaRemix: { costGems: 60 },
  plotCompletion: 60,
  packs: [
    { id: "gems_starter", priceUSD: 0.99,  gems: 100 },
    { id: "gems_value",   priceUSD: 4.99,  gems: 550 },
    { id: "gems_super",   priceUSD: 9.99,  gems: 1200 },
    { id: "gems_whale",   priceUSD: 19.99, gems: 2800 },
  ],
} as const;

// ──────── VIP ────────
export const VIP = {
  tiers: [
    { id: "vip_weekly",  priceUSD: 4.99,  period: "week",  dailyCoins: 600, dailyCoinsBonus: 200, dailyGems: 5 },
    { id: "vip_monthly", priceUSD: 12.99, period: "month", dailyCoins: 800, dailyCoinsBonus: 400, dailyGems: 10 },
  ],
} as const;

// ──────── 关系 tier ────────
export const RELATIONSHIP = {
  tierThresholds: [0, 10, 30, 80, 200],
  defaultTierLabels: ["初识", "熟悉", "朋友", "挚友", "核心关系"],
} as const;

// ──────── UI / 反馈 ────────
export const UI = {
  typewriterCps: 60,
  episodeDurationSec: 130,
} as const;

// ──────── Influence / LLM ────────
export const INFLUENCE = {
  maxRetries: 10,
  llmTemperature: 0.0,
  llmTimeoutMs: 30_000,
} as const;

// ──────── 纯基础设施（非游戏机制）────────
export const INFRA = {
  walkerSafetyLimit: 100_000,
  httpTimeoutsMs: { dramatizer: 15_000, sidecar: 10_000 },
  dramatizerRetries: 3,
  sidecarRetries: 1,
  cache: {
    episodeJsonMax: 256,
    manifestTtlMs: 300_000,
    characterMemoriesMax: 50,
    chatHistoryWindow: 20,
    chatDistillTrigger: 30,
    chatDistillFetch: 60,
  },
} as const;

// ──────── 平台（账户级）────────
export const ONBOARDING = {
  registerGems: 1000,
  inviteGems: 1000,
} as const;
```

### 5.3 访问模式

```ts
import { CHECK, CONTINUOUS_RULES, DIFFICULTY, LEVEL } from "@/app/core/game-rules";
// 不再从 numerical-system.ts / minigame-registry.ts / chat-tier.ts 散点 import
```

### 5.4 `numerical-system.ts` 清理

- 所有 `export const` 移到 `game-rules.ts`
- 只保留**纯函数**（`calcAttributeModifier`、`calcSANChange`、`performD20Check` 等）
- 函数内引用从常量改成 `CHECK.attributeHardCap` 这种

---

## 6. MSS 脚本（只读）

完全不动格式。只在我方加 slot 解析：

```ts
// app/lib/game-config.ts
export function resolveSlot(mssAttr: string, cfg: NovelGameConfig): 1|2|3|4 {
  const normalized = mssAttr.toLowerCase();
  const idx = cfg.variables.checking.findIndex(v => v.mssKey === normalized);
  if (idx < 0) throw new UnknownMssKeyError(mssAttr);
  return (idx + 1) as 1|2|3|4;
}
```

---

## 7. 代码组织

```
app/
  core/
    game-rules.ts             # 新增：所有平台级数值常量（§5）
    game-config-schema.ts     # 新增：Novel.gameConfig Zod
    schema.ts                 # 只留 MSS Step/Condition/Episode schema
  lib/
    game-config.ts            # 新增：getGameConfig(novelId) + resolveSlot()
    numerical-system.ts       # 收缩：只留纯函数，const 迁走
    minigame-registry.ts      # 收缩：MODIFIER/XP 迁到 game-rules.ts
    chat-tier.ts              # 收缩：TIER_THRESHOLDS 迁到 game-rules.ts
  services/
    novel-config-scan-service.ts  # 新增：扫描 Episode 抽 MSS key
```

---

## 8. 数据迁移

1. 离线 scan：对每个 Novel 跑 `novel-config-scan-service` → 产出 gameConfig JSON
2. 单次 Prisma migration：
   - `Novel`：加 `gameConfig`、删 `attributeConfig`
   - `Session`：加 `continuousVariable/Max/checkingVariable1~4`，删 `san/sanMax/attributes`
   - 数据回填 SQL 内嵌
3. 代码切换（同一 PR）：全局 import 重写 + 删旧导出
4. 单测跑绿 → merge

**scan 逻辑**：
```ts
async function scanNovel(novelId: string): Promise<GameConfigDraft> {
  const episodes = await loadAllEpisodeJsons(novelId);
  const checkKeys = new Set<string>();

  walkSteps(episodes, {
    onBraveOption: (o) => checkKeys.add(o.check.attr.toLowerCase()),
    onMinigame: (m) => checkKeys.add(m.attr.toLowerCase()),
  });

  // SAN 是隐式约定，scan 不出来，直接兜底
  return {
    continuous: { mssKey: "san", label: "理智", initial: 100, max: 100, dailyReset: 100 },
    checking: orderKeys([...checkKeys]).slice(0, 4).map((key, i) => ({
      mssKey: key,
      label: DEFAULT_LABEL[key] ?? key.toUpperCase(),
      initial: [10, 13, 14, 15][i],
      max: 24,
    })),
    freePoints: 2,
  };
}
```

排序：已知的 `atk → int → cha → wil` 优先，其他按字母序。

---

## 9. Admin UI（保持简洁）

### 9.1 页面 `/admin/novels/[id]/game-config`

**编辑区**（写）：
- 连续变量：`mssKey` / `label` / `initial` / `max` / `dailyReset`（5 个输入）
- 检定变量（4 个一样的表单）：`mssKey` / `label` / `initial` / `max`
- `freePoints`（1 个输入）
- **[扫描 MSS]** 按钮：读本剧本所有 Episode → 填充 4 个 slot 的 `mssKey`（label/initial 保持用户已填的，只覆盖 `mssKey`）

**平台数值速查**（只读卡片）：
- 显示从 `game-rules.ts` 读出的关键值：检定规则、连续变量规则、DC 曲线概览、等级 XP 表、每集 XP、体力消耗、Gems 价格、关系 tier
- 每个 section 一个折叠卡片，默认展开 2~3 个最常看的
- 纯展示，不提供编辑（改值要走代码 PR）

**可视化**（简洁）：
- DC 曲线：一条小折线图展示 60 集的 mean（from `DIFFICULTY.phases`）
- 不做多余图表

### 9.2 后端接口

```
GET    /api/admin/novel/[id]/game-config        # 读取 gameConfig + 平台只读数值
POST   /api/admin/novel/[id]/game-config/scan   # 扫描 MSS，返回 mssKey 草稿（不落库）
PATCH  /api/admin/novel/[id]/game-config        # 全量覆盖，Zod 校验
```

不做 reset（直接编辑即可）、不做 audit log（MVP 从简）。

---

## 10. 实施分期

### 阶段 1：平台数值整理（0.5~1 天）
- 新建 `app/core/game-rules.ts`，把散落的 const 全部迁入
- 改 import：`numerical-system.ts` / `minigame-registry.ts` / `chat-tier.ts` 及下游消费者
- 保留纯函数；跑现有测试确保无回归
- **独立 PR**

### 阶段 2：gameConfig 基础设施（0.5 天）
- `app/core/game-config-schema.ts` Zod
- `app/lib/game-config.ts`（getGameConfig / resolveSlot）
- `app/services/novel-config-scan-service.ts`

### 阶段 3：Schema 迁移 + 代码切换（1~2 天）
- 离线 scan 脚本跑一遍，产出 gameConfig JSON
- Prisma migration 加/删列 + 数据回填
- 全局 import 重写（所有 SAN/attributes 读写改新字段）
- 单测/集成测绿

### 阶段 4：Admin UI（1~2 天）
- 页面 + 3 个接口
- 编辑表单 + 扫描按钮 + 只读卡片 + DC 曲线图

### 阶段 5：清理 & 文档（0.5 天）
- 更新 `docs/numerical_design.md`
- 归档迁移脚本
- wiki_ingest 本 spec 到团队知识库

**总计：3.5~6 天**

---

## 11. 决策记录

### 11.1 为什么平台数值不进 gameConfig

**决策**：只有属性信息进 per-novel；其他数值全部平台级、代码常量
**理由**：
- DC 曲线、XP 表、coins/gems/VIP 等改动要影响玩家经济平衡，不能让剧本作者随便改
- 平台级数值要求跨剧本一致（A/B 测试另有机制，不是 per-novel override）
- 代码常量保留 git 审计 + PR review，改值流程更严谨

### 11.2 为什么 MSS 保持只读，不改契约

**决策**：MSS 格式完全不动，用 `mssKey` 做 slot 绑定
**理由**：
- MSS 是上游 dramatizer 的契约，跨服务改成本高
- `mssKey` 让适配职责留在我方，scan 自动识别让新 key 零成本

### 11.3 为什么 Session 用 4 个平坦列而不是 JSON

**决策**：`checkingVariable1~4` 为独立 `Int` 列
**理由**：
- 位置固定 4 个，不需要 JSON
- 类型安全、索引友好、作弊接口更简单

### 11.4 为什么不做向后兼容层

**决策**：单次 migration 加列删列回填
**理由**：
- 用户明确要求"大刀阔斧"
- 离线 scan 已预生成所有新配置
- Session 回填是纯函数，无并发风险

### 11.5 为什么 admin UI 不编辑平台数值

**决策**：平台数值在 admin UI 只读展示
**理由**：
- 保持 UI 简洁（用户要求）
- 平台数值改动需要 git 审计 + code review
- 避免"管理员误操作破坏经济平衡"的风险

---

## 12. 测试计划

### 12.1 单测
- `getDefaultGameConfig()` 通过 Zod 校验
- `scanNovel(novelId)`：fixture Episode → 验证抽出的 key 和顺序
- `resolveSlot("cha", cfg)` → 返回正确 slot（大小写归一化）
- Zod refine：`checking.length === 4`、`mssKey` 唯一性
- 迁移脚本：构造旧 Session → 跑脚本 → 新字段正确

### 12.2 集成测
- Session 创建：用自定义 gameConfig 初始化 → `checkingVariable1~4` 正确
- D20 检定：MSS `attr: "CHA"` → resolveSlot → 读 checkingVariable3
- SAN 崩溃流：连续失败 → 崩溃 → Gems 扣费恢复
- Admin scan 接口：fixture Episode → 返回预期 keys
- Admin PATCH：非法 config → 400 + Zod 错误

### 12.3 E2E
- 新建剧本 → admin 点"扫描"→ 填 4 个 slot → 改 label → 保存 → 前端 HUD 显示新 label → 玩家检定正常
- 回归：默认配置玩家体验与迁移前一致

---

## 13. 未决问题

1. **scan 扫出 > 4 个 check key**：当前方案取前 4 个（排序后）。要不要让 admin 手动选？（建议 MVP 直接取前 4，warning 提示）
2. **scan 扫出 < 4 个 key**：比如剧本只用 `atk`、`cha` 两种。缺失 slot 用默认 key 填（`int`/`wil`）还是留空？（建议用默认值填，admin UI 上标记"未使用"）
3. **平台数值可视化深度**：DC 曲线是小折线，其他要不要也加可视化？（当前 spec 只做 DC 曲线，其他纯数字展示）
