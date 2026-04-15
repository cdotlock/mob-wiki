---
title: MoonShort Script (MSS) Interpreter
tags: [mss, script, interpreter, go, visual-novel]
sources: []
created: 2026-04-15
updated: 2026-04-15
---

MoonShort Script（MSS）是 MobAI 互动视觉小说的统一脚本格式及其配套解释器。一个 `.md` 脚本文件同时定义一集的叙事内容和游戏机制（D20 检定、小游戏、分支路由），Go 解释器将其编译为前端播放器可直接消费的 JSON。

仓库：[cdotlock/moonshort-script](https://github.com/cdotlock/moonshort-script)

## 产品定位

MSS 解决的核心问题是：Dramatizer 生成的剧本、Remix Executor 生成的二创内容、以及人工编写的脚本，需要一个统一的格式和工具链来编译为前端播放器的输入。

MSS 不是一个运行时引擎——它是一个编译时工具。脚本在上线前编译为 JSON，前端播放器消费 JSON，运行时不需要解释器。

## 架构

解释器是一个 Go 单二进制工具 `mss`，内部有 6 个模块，按管线顺序执行：

```
.md 脚本 → Lexer → Parser → Validator → Fixer(可选) → Resolver → Emitter → JSON
```

### 模块职责

| 模块 | 路径 | 职责 |
|------|------|------|
| Token | `internal/token/` | 定义 23 种 token 类型（AT、IDENT、STRING、NUMBER、操作符等） |
| Lexer | `internal/lexer/` | 将原始文本拆分为 token 流。处理 `@` 指令、`{ }` 块界定、`"..."` 字符串、`//` 注释、`>=` `&&` 等操作符。特殊方法 `ReadDialogueText()` 读取对话行冒号后的全部文本 |
| AST | `internal/ast/` | 定义 30+ 种 AST 节点类型，覆盖所有 MSS 指令：视觉（BgSet、CharShow、CharHide、CharExpr、CharMove、CharBubble、CgShow）、对话（Dialogue、Narrator、You）、手机（PhoneShow、PhoneHide、TextMessage）、音频（MusicPlay、MusicCrossfade、MusicFadeout、SfxPlay）、游戏机制（Minigame、Choice、Option、CheckBlock）、状态（Xp、San、Affection、Signal、Butterfly）、流程（If、Label、Goto）、结构（GatesBlock、Gate、Default） |
| Parser | `internal/parser/` | 递归下降解析器，将 token 流组装为 AST。关键设计：通过排除法识别角色指令——`@` 后的 IDENT 如果不是已知关键字（bg、cg、phone、text、music、sfx、minigame、choice、option 等），就视为角色名，下一个 IDENT 是动作（show、hide、expr、move、bubble） |
| Validator | `internal/validator/` | 对 AST 做语义校验：episode 必须有 `@gates` 块、gates 必须有 `@default`、brave 选项必须有 `check` 块和 `@on success/fail`、`@goto` 必须有匹配的 `@label`、选项 ID 不能重复 |
| Fixer | `internal/fixer/` | 文本级自动修复（仅通过 `mss fix` 显式调用）：补全缺失的 `}`、角色名大小写统一、去除对话行多余的 `@`、给 `@butterfly` 参数补引号、清理尾部空格和多余空行。影响内容的问题（缺 gates、缺 check 块等）报错不修 |
| Resolver | `internal/resolver/` | 读取独立的 JSON 素材映射表，将脚本中的语义名（如 `malias_bedroom_morning`）翻译为完整 OSS URL。映射表由素材管线（Agent-Forge）生成维护，与脚本解耦 |
| Emitter | `internal/emitter/` | 将 AST 转为前端可消费的 JSON。每个 AST 节点映射为一个带 `type` 字段的 JSON step，URL 全部已解析。输出扁平数组，嵌套只出现在有分支的地方（choice、minigame、if） |

### 关键设计决策

**脚本与素材分离**：脚本只写语义名，不包含任何 URL 或文件路径。素材映射是一个独立的 JSON 文件，解释器通过 `--assets` 参数读入。这意味着同一套脚本可以指向不同的 OSS 环境（开发/生产/测试），素材更新不需要改脚本。

**对象-行动语法**：所有视觉指令遵循 `@<对象> <行动> [参数]` 模式（如 `@mauricio show neutral_smirk at right`），而非行动-对象模式。这让脚本更像自然语言描述，LLM 生成时认知负担更低。

**fix 只在显式调用时执行**：`mss compile` 和 `mss validate` 遇到问题直接报错，不会自动修复。只有 `mss fix` 才会修改文件。这避免了静默修改内容的风险。

**语法糖 `CHARACTER [pose_expr]: text`**：因为对白+换表情的组合在实际脚本中出现频率极高（几乎每句对话），保留了这个语法糖。解析器将其展开为 CharExprNode + DialogueNode 两个 AST 节点。

## 命令行用法

```bash
# 编译单集脚本为 JSON
mss compile episode.md --assets mapping.json -o output.json

# 批量编译整个目录
mss compile novel_001/ --assets mapping.json -o novel.json

# 验证脚本语法（不输出 JSON）
mss validate episode.md

# 自动修复常见语法错误
mss fix episode.md -o fixed.md

# 干跑 fix，只看报告不改文件
mss fix episode.md --check
```

## 素材映射表格式

```json
{
  "base_url": "https://oss.mobai.com/novel_001",
  "assets": {
    "bg": {
      "malias_bedroom_morning": "bg/malias_bedroom_morning.png"
    },
    "characters": {
      "mauricio": {
        "neutral_smirk": "characters/mauricio_neutral_smirk.png"
      }
    },
    "music": {
      "calm_morning": "music/calm_morning.mp3"
    },
    "sfx": {
      "door_slam": "sfx/door_slam.mp3"
    },
    "cg": {
      "window_stare": "cg/window_stare.png"
    },
    "minigames": {
      "qte_challenge": "minigames/qte_challenge/index.html"
    }
  }
}
```

解释器拼 `base_url` + 相对路径 = 完整 OSS URL。映射表中找不到的语义名在 compile 时输出 warning（URL 留空），在 validate 时报 error。

## JSON 输出结构

编译后的 JSON 是前端播放器的直接输入，设计原则是**类型明确、URL 已解析、扁平易遍历**：

```json
{
  "episode_id": "main:01",
  "branch_key": "main",
  "seq": 1,
  "title": "Bad Idea",
  "steps": [
    {"type": "bg", "name": "malias_bedroom_morning", "url": "https://oss.../bg/malias_bedroom_morning.png", "transition": "fade"},
    {"type": "char_show", "character": "malia", "pose_expr": "neutral_phone", "url": "https://oss.../...", "position": "center"},
    {"type": "narrator", "text": "Senior year. Day one."},
    {"type": "dialogue", "character": "mauricio", "text": "Hey, Butterfly."},
    {"type": "you", "text": "He hasn't called me that in eight years."},
    {"type": "choice", "options": [
      {"id": "A", "mode": "brave", "text": "Stand your ground.", "check": {"attr": "CHA", "dc": 12}, "on_success": [...], "on_fail": [...]},
      {"id": "B", "mode": "safe", "text": "Walk away.", "steps": [...]}
    ]}
  ],
  "gates": {
    "rules": [
      {"target": "main/bad/001:01", "type": "choice", "trigger": {"option_id": "A", "result": "fail"}},
      {"target": "main/route/001:01", "type": "influence", "condition": "玩家展现过对Easton的持续接纳"}
    ],
    "default": "main:02"
  }
}
```

每个 step 有 `type` 字段做类型判别，前端用 switch/case 消费。`steps` 是扁平数组，顺序即执行顺序。

## 文件组织

```
moonshort-script/
├── cmd/mss/main.go              # CLI 入口
├── internal/
│   ├── token/token.go           # Token 类型定义
│   ├── lexer/                   # 词法分析（9 tests）
│   ├── ast/ast.go               # AST 节点类型
│   ├── parser/                  # 语法分析（13 tests）
│   ├── resolver/                # 素材映射（6 tests）
│   ├── emitter/                 # JSON 输出（2 tests）
│   ├── validator/               # 语义校验（5 tests）
│   └── fixer/                   # 自动修复（14 tests）
├── testdata/
│   ├── mapping.json             # 测试用素材映射
│   ├── minimal.md               # 最小集脚本
│   ├── ep01.md                  # Episode 1 测试脚本
│   └── example/                 # No Rules E1-E4 完整示例
│       ├── 01.md ~ 04.md        # MSS 格式
│       └── example-old-version.md  # 原版 v1 格式（对照）
├── skills/mss-scriptwriting/    # Agent 写作指南
│   ├── SKILL.md                 # 主文档
│   └── references/
│       ├── MSS-SPEC.md          # 完整格式规范
│       ├── addressing.md        # episode_id 寻址规则
│       └── directive-table.md   # 指令速查表
├── MSS-SPEC.md                  # 格式规范（根目录副本）
├── Makefile
└── README.md
```

## 与其他系统的关系

**[[entities/dramatizer]]**：Dramatizer 的 Phase 3（ludify 阶段）将重构为输出 MSS 格式。当前 Dramatizer 输出 JSON 结构化数据，未来需要在最终阶段将 JSON 转为 MSS 脚本文本。

**[[entities/agent-forge]]**：Agent-Forge 的视频工作流将转型为 VN 素材管线，负责生成背景、角色立绘、CG 等素材，并维护素材映射表（mapping.json）。

**Remix Executor**：后端 Remix 管线的 Executor 阶段将输出 MSS 格式，与 Dramatizer 产出完全一致，前端统一消费。

**前端播放器**：消费 MSS 解释器输出的 JSON，渲染 Unfolded 风格的互动视觉小说体验。播放器不需要理解 MSS 脚本——它只消费 JSON。

## Agent Skill

项目内置了 `skills/mss-scriptwriting/` 目录，包含一个完整的 Agent Skill，教 LLM agent 如何正确生成 MSS 脚本。Skill 覆盖完整语法规则、最佳实践、10 条常见错误、Remix 差异点和节奏指导。Dramatizer 和 Remix Executor 的 LLM 在生成脚本时应加载此 Skill。

详细格式规范见 [[concepts/mss-format]]。
