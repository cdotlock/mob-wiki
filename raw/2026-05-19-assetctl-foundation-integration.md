# assets-produce 融入 moonshort-ide — 接口合同 + IDE 对接 设计 spec

> 创建 2026-05-19
> 范围:把 assets-produce 的原子能力 + 编排 skill 融入 moonshort-ide,终态是
> IDE 里的 codex 作为外围编排 agent、按 skill 临场调度原子能力。本 spec **只**
> 敲定第 0/1 块的对接面(原子能力 CLI 接口合同 + IDE 侧 Go 重写/构建/接线);
> 第 2/3 块(编排 skill+知识、Langfuse parity)各自另起 spec→plan。
> 状态:待评审

## 0. 一句话 & 范围

**终态**:给 IDE 里的 codex 一个任务 → 它读 staged skill → 临场决定调哪颗原子能力、
什么顺序 → 调本地 Go CLI 干活。流程不写死在代码里,写在 skill 里。这正是
assets-produce 主 spec(`~/MobAI/assets-produce/docs/superpowers/specs/2026-04-29-assets-produce-spec.md`)
**原则 1(原子能力 + skill 编排)/ 原则 2(SKILL→CLI→Tool→API)** 的形状,只是
把"编排 agent"从 assets-produce 自己的 `llm-generator` loop 换成 IDE 自带的 codex。

**本 spec 只锁两件事**:① 那个原子能力 Go CLI 对外怎么用(**接口合同**);
② IDE 这侧怎么把它 Go 重写落地、构建、登记、让 codex 调到。其余为后续(§8)。

**优先级**:接口合同的稳定 > IDE 侧实现细节。合同是冻结的对接面,两侧都照它来;
实现可演进,合同不可随意改。

## 1. 背景:为什么这么做

- assets-produce 把素材生产拆成了**原子能力**(生图/生视频/生音/抠图/放大/合成…),
  上层用 agent+skill 经 LLM 推理临场组合,**禁止硬编码流水线**(原则 1)。
- moonshort-ide 现状:`agents/asset` 已是 image agent,且已用 vendored 的 Go
  `videoctl`(`vendor/videoctl/` → `fork/build.mjs` `buildVideoctl()` →
  `agents/asset/cli/videoctl/bin/videoctl`,登记在 `agents/asset/cli/bindings.json`)
  做视频。但只覆盖视频投递工作流,且 `agents/asset/skills/*/references/` 的知识
  已较上游严重 drift。
- 目标不是"IDE 当 assets-produce 的产物消费方"(assets-produce 那份
  `2026-05-18-assets-produce-ide-workspace-contract.md` 的定位**不是**本 spec 的
  终态);而是把原子能力 + 编排 skill **吸收进 IDE**,IDE 永久自有。

## 2. 已锁定的决策(逐条,带理由)

| # | 决策 | 理由 |
|---|---|---|
| D1 | **终态 = codex 外围编排 + 原子能力 CLI + skill 控制流**,流程不写死 | 对齐 assets-produce 原则 1/2;codex 已在 IDE 内,天然胜任外围 agent |
| D2 | **退役范围:只有 assets-produce 代码仓冻结归档**;Langfuse prompt 库(`prompt.mobai-game.com`, project=`assets-produce`)+ 模型网关继续活,为独立基础设施 | 决定 D5 是否成立 |
| D3 | **打包形态 = 全 Go 重写,一步到位,无 Bun 中间态** | 仓库冻结后无"活代码上游"可追,"两份对齐/stale"的反对理由失效;IDE 与 `mss`/`videoctl` 单一 Go 工具链、永久自有、轻薄。一次性代价 = 重写工作量 + 翻译走样风险(§9 缓解) |
| D4 | **assets-produce = 捐赠方/参考实现**:其 TS 源码(`agent/packages/opencode/src/tool/asset/*.ts`)+ 每颗 `.txt` 描述 + `knowledge/asset-generation/*` 规范 = Go 重写的**行为基准**;交接完即冻结 | 没有"持续从活上游 re-vendor",改为"一次对照基准重写,IDE 接手所有权" |
| D5 | **保留 Langfuse-first skill 正文加载 + sync/parity(选项 2)** | skill 正文的"活上游"是 Langfuse(原则 4),不是 assets-produce 仓。D2 下 Langfuse 仍活 → 这层与仓库冻结无关,继续成立。落在第 3 块(§8) |
| D6 | **videoctl 保持不动**,与新 CLI 并存 | 已是干净 Go、已 vendored、覆盖视频投递工作流;不在本轮重写范围 |

> 计数勘误(与对话口径对齐):此前口语说"37 颗",那是 `src/tool/asset/` 的**文件数**
> (含每颗 `.txt` 描述与 `fc-client`/`python-runner` 支撑件)。**原子能力的权威 id
> 清单以 `skill-source.ts` 的 `ATOMIC_TOOL_IDS` 为准 —— 当前 18 个**:
> `generate-image-nanobanana` `generate-image-gpt` `generate-video-seedance`
> `generate-video-happyhorse` `generate-sfx-elevenlabs` `generate-music-suno`
> `concat-clips` `crop-video` `cg-render` `nrbi-render-prompt` `upscale-image`
> `oss-put` `matting` `hybrid-to-webp` `green-spill-clear` `rgb-unspill`
> `hole-fill` `cutout`。Go 重写以此清单为准,后续如增删以本清单为单一真相源。

## 3. 终态架构

```
┌──────────────── moonshort-ide(.app,离线打包,纯 Go 工具链)────────────────┐
│  codex(IDE 自带 AI = 外围编排大脑)                                         │
│    │ 读 staged skill(第 2 块),临场决定先调谁、再调谁(流程不写死)        │
│    ▼                                                                       │
│  assetctl(本轮 Go 重写的原子能力 CLI)   ‖   videoctl(视频投递,已有,不动)│
│    │ assetctl run <tool-id> --input … → JSON 信封 + 落地文件                │
└────┼───────────────────────────────────────────────────────────────────────┘
     │ 干活时联网 + 用密钥(经模型网关)
     ▼  外部模型/服务(nanobanana / seedance / suno / elevenlabs / OSS …)

  ══ 本 spec 锁定 ══  ① assetctl 接口合同(§4)  ② IDE 侧落地(§5)
  ── 后续另起 spec ──  第 2 块:编排 skill+知识   第 3 块:Langfuse-first parity
```

## 4. 接口合同(本轮核心 · 语言无关,Go 实现照此)

合同 = `assetctl`(暂名)对外的稳定面。冻结后两侧共同遵守。

**A. 能力发现(codex 自检)**
- `assetctl tools list` → JSON:每颗 `{id, summary}`(id 取自 `ATOMIC_TOOL_IDS`)。
- `assetctl tools show <id>` → 该颗的输入参数 JSON Schema。
- `assetctl tools schema [--format anthropic|openai]` → LLM 工具表格式,codex 可直接当工具清单。
> 对应 assets-produce `agent tools list/show` + `config export-schema`,瘦 CLI 原样保留语义。

**B. 能力调用**
- `assetctl run <id> --input <json|@file> [--json]`,非 TTY、不阻塞 stdin(无人值守)。
- stdout 一行 JSON 信封:
  `{ "ok": bool, "data": { "assets": [{ "kind", "name", "loc" }], ... }?, "error": { "code", "message", "retryable": bool }? }`
- 产物字节落工作区;`loc` 可本地路径**或** `oss://…` URL —— 取用方一律走 `loc`,
  **禁止写死"只读 ./assets"**(守住本地/远程同一套逻辑)。

**C. 退出码 & 错误分类(给 IDE 重试层用)**
- `0` 成功。
- `3` 环境/密钥缺失,stdout `{ ok:false, missing:[…] }`;配套 `assetctl config validate`。
- 非 0 且 `error.retryable=true` = 临时故障(网络/限流)→ IDE 可重试。
- 请求本身不可行/被拒(对应 assets-produce `SkillInfeasibleError`→`GENERATION_REJECTED`)
  = 专用非 0 码、`retryable=false` → IDE **不得**重试。
- 内部失败 = 另一专用非 0 码,`retryable` 视情形。
- 本节锁定的是**语义与分类**;各非 0 码的**具体数值**在第 0 块合同冻结时定死
  (`0`/`3` 已固定),冻结后进 §4-E 版本号管辖。

**D. 合同边界(明确不进 assetctl)**
- **不带**:任何编排/流水线 loop(那是 codex 的职责,塞进 CLI 即违反原则 1)、
  DB、web UI、session、账号/providers。
- **只带**:`ATOMIC_TOOL_IDS` 各颗 + 支撑件(`fc-client`/`python-runner` 的 Go 等价)
  + A 的自检 + `config validate`。

**E. 合同版本(防悄悄漂移)**
- 合同带语义版本号;`assetctl config version` 可查。
- `vendor/README` 记录"重写所对照的 assets-produce 基准 commit SHA"(沿用
  `videoctl`/`moonshort-script` 现成做法)。
- IDE 侧加 parity/契约测试(§7),版本或信封形状不符即失败。

## 5. IDE 侧落地(D3 路 B · 纯 Go · 照 videoctl 现成模式)

- **代码与构建**:新增 Go module 源码于 `vendor/assetctl/`;`fork/build.mjs` 加
  `buildAssetctl()`(与 `buildVideoctl()` 并列,`go build ./cmd/assetctl`),产物
  `agents/asset/cli/assetctl/bin/assetctl`(gitignored,构建时出)。**IDE 工具链
  零新增**(仍纯 Go,无 Bun)。
- **登记**:`agents/asset/cli/bindings.json` 增一条 `assetctl` binding
  (`command`/`baseArgs`/`binaryPath`/`description`,与现有 `videoctl` 条目同形)。
- **codex 接线**:第 2 块的 skill staged 进 `$CODEX_HOME/skills/`;`stage-runner.ts`
  现有机制**原样复用**(staging + codex 原生渐进披露 + 不注入 system prompt +
  run 后清理)。host 不写死流程。
- **与 videoctl 关系**:两个独立 Go CLI 并存于 `bindings.json`。`videoctl` = 视频
  投递工作流;`assetctl` = `ATOMIC_TOOL_IDS` 原子能力。**开放细节(§9-O1)**:
  `generate-video-*` / `concat-clips` / `crop-video` 与 `videoctl` 的职责边界
  需在第 1 块 plan 阶段定清,避免重叠或双实现。

## 6. 错误与重试

`assetctl` 严格按 §4-C 出退出码 + 信封。moonshort-ide `agent-adapter` 现有
`errors.ts` / `retry.ts` 按合同分类:`retryable=true` 走退避重试;
`GENERATION_REJECTED`/`config(3)` 不重试、直接上抛给 codex/Workshop 呈现。
`bindings.json` 的 wrapped CLI 层(本仓 §5.5)负责输出解析与分类落地。

## 7. 测试(全局规则 80%+)

- **合同测试**:每颗能力 —— 给定输入 → 断言信封形状、退出码、`config validate`
  与 `config version` 行为符合 §4。
- **重写对拍**:Go 版 vs assets-produce TS 基准(D4),关键能力同输入比对产出与
  错误码,守"翻译不走样"(§9-R1)。基准取 `vendor/README` 钉的 SHA。
- **集成**:codex 跑最小编排(staged skill → 调 `assetctl` 一两颗 → 落地素材),
  验证 `bindings.json` + staging 链路。
- **构建**:`pnpm check` 全绿;`fork/build.mjs` 能产出 `assetctl` 二进制(遵守
  本仓"不主动全量打包"纪律 —— 只验证该构建步骤,不全量出 .app)。

## 8. 拆分与后续(顺序死板 0→1→2→3)

| # | 在哪 | 内容 | 状态 |
|---|---|---|---|
| 0 | assets-produce(临终一次性) | 冻结 §4 接口合同 + 把各颗行为定成可对照基准(TS+`.txt`+knowledge),钉 SHA,归档 | 本 spec 锁定其**对接面**;assets-produce 侧执行细节属其仓库 |
| 1 | moonshort-ide | 按 §4 合同 Go 重写 `ATOMIC_TOOL_IDS`,§5 落地 | 本 spec 覆盖;下一步 writing-plans |
| 2 | moonshort-ide | 上游权威编排 skill + 知识 → codex staged skill(本地 git 兜底);drift 一次性补齐 | **后续另起 spec→plan** |
| 3 | moonshort-ide | Langfuse-first 正文加载 + `skills sync`/`--check` parity,适配进 codex staging(参 assets-produce `2026-05-19-langfuse-skill-loader-design.md` D1/D2/D3/D6/D7;D5 promote 闸的 IDE 等价物 = 结构/frontmatter 有效) | **后续另起 spec→plan**;D2/D5 下成立 |

## 9. 开放细节 & 风险

- **O1 · assetctl↔videoctl 边界**:`generate-video-*`/`concat-clips`/`crop-video`
  与 `videoctl` 是否重叠 —— 第 1 块 plan 阶段定清(候选:assetctl 不收视频生成类,
  全部委派 videoctl;或 videoctl 专注投递、生成类归 assetctl)。
- **R1 · Go 翻译走样**:缓解 = §7 对拍测试 + 钉基准 SHA + 逐颗 PR 评审。
- **R2 · `python-runner` 类能力**:部分原子能力(抠图/matting 等)经 Python 子进程。
  Go 化方案(纯 Go 重写 vs Go 包一层 Python/原生库)第 1 块 plan 定;不在本 spec 收口。
- **R3 · 密钥/网关**:`assetctl` 运行需模型网关凭据;`config validate` 是契约的一
  部分,缺凭据走退出码 3,不得 hard-crash。
- **R4 · 与 Workshop 能力模型一致**:必须遵守 `2026-05-18-workshop-agent-console.md`
  原则五(能力按文件夹约定发现,不在 `agent.json` 写死);assetctl 仅作为 CLI
  binding 被 skill 引用,不引入写死的 stage。

## 10. 关联

- assets-produce 主 spec §2 原则 1/2/4、§15;
  `2026-05-19-langfuse-skill-loader-design.md`(第 3 块依据);
  `2026-05-18-assets-produce-ide-workspace-contract.md`(**非**本 spec 终态,仅备注)。
- moonshort-ide:`2026-05-18-workshop-agent-console.md`(能力模型原则五);
  `vendor/README`(videoctl/moonshort-script 重同步范式 = assetctl 钉 SHA 范式);
  `agents/asset/cli/bindings.json`、`fork/build.mjs`、`packages/mss-workshop/src/stage-runner.ts`。
- 团队规则:本设计为重大技术方案,评审通过后须 `wiki_ingest` 入 mob-wiki
  (写前 `git -C ~/mob-wiki pull`)。
