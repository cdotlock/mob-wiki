---
title: assetctl — 原子能力 CLI 接口合同 v0.1.0 (assets-produce → moonshort-ide)
created: 2026-05-20
updated: 2026-05-20
tags: [assetctl, assets-produce, moonshort-ide, atomic-capability, interface-contract, codex, oss-put]
status: draft
---

# assetctl — 原子能力 CLI 接口合同 v0.1.0

把 assets-produce 的**原子能力**以全 Go 重写吸收进 moonshort-ide：`assetctl` 是 IDE 内 codex（外围编排大脑）临场调度的、冻结接口合同的原子能力 CLI。流程写在 skill 里、不写死在代码里（assets-produce 原则 1/2）。

> 设计 spec：`moonshort-ide/docs/design/2026-05-19-assets-produce-integration-design.md`（项目内 git，未公开；commit `f8cdf81`）
> 实现计划：`moonshort-ide/docs/design/2026-05-19-assetctl-foundation-plan.md`（commit `b38dfda`）
> 关联：[[entities/assets-produce]] · [[concepts/assets-produce-ide-workspace-contract]]（**非**本终态，仅备注）· [[concepts/moonshort-ide-ai-integration]] · [[concepts/four-layer-philosophy]]

## 一句话

给 IDE 里的 codex 一个任务 → 读 staged skill → 临场决定调哪颗原子能力、什么顺序 → 调本地 `assetctl` Go CLI 干活 → JSON 信封 + 落地文件。`videoctl`（视频投递，已有）保持不动，与 `assetctl` 并存。

## 为什么这么做（已锁决策 D1–D6）

- **D1**：终态 = codex 外围编排 + 原子能力 CLI + skill 控制流，流程不硬编码（对齐 assets-produce 原则 1/2；codex 已在 IDE 内）。
- **D3**：打包形态 = **全 Go 重写一步到位，无 Bun 中间态**。assets-produce 仓冻结后无活上游，“两份对齐/stale”反对理由失效；IDE 与 `mss`/`videoctl` 单一 Go 工具链、永久自有。
- **D4**：assets-produce = **捐赠方/参考实现**。其 TS 源 + 每颗 `.txt` 描述 + `knowledge/` 规范 = Go 重写的**行为基准**，基准 commit `assets-produce@48e6eb9`，交接即冻结。
- **D6**：`videoctl` 不动，与新 CLI 并存。
- 优先级：**接口合同的稳定 > 实现细节**。合同冻结，两侧共同遵守；实现可演进，合同改动需升版本号。

## 冻结接口合同 v0.1.0（按实现定稿）

**契约常量**（`assetctl config version` 可查）：`contract = 0.1.0`，`baseline_sha = 48e6eb9`，`assetctl = 0.1.0-dev`。

**A. 能力发现（codex 自检）**
- `assetctl tools list` → JSON 数组，每颗 `{id, summary}`。
- `assetctl tools show <id>` → 该颗输入参数的 JSON Schema（**属性顺序确定**：用 `json.Indent` 字节保真，不经 map 重排——这是 `internal/jsonschema` 包存在的理由，`tools show` 与 `tools schema` 对同一颗必须同序）。
- `assetctl tools schema [--format anthropic|openai]` → LLM 工具表，codex 直接当工具清单。

**B. 能力调用**
- `assetctl run <id> --input <json|@file>`，非 TTY、不阻塞 stdin（无人值守）。
- stdout **一行** JSON 信封：
  `{"ok":bool,"data":{"assets":[{"kind","name","loc"}],...}?,"error":{"code","message","retryable":bool}?,"missing":[...]?}`
- 产物落工作区；`loc` 可本地路径**或** `oss://…`/https URL —— 取用方一律走 `loc`，禁止写死“只读 ./assets”。

**C. 退出码 & 错误分类（给 IDE 重试层用）—— 冻结表**
| 退出码 | 含义 | error.code | retryable |
|---|---|---|---|
| 0 | 成功 | — | — |
| 2 | 用法错误（caller 处理，不出信封） | — | — |
| 3 | 环境/密钥缺失，stdout `{ok:false,missing:[…]}` | (CONFIG_MISSING) | — |
| 4 | 输入非法 / 被拒 / 该 build 未实现 | INVALID_INPUT · GENERATION_REJECTED · NOT_IMPLEMENTED | false |
| 5 | 临时故障（网络/限流），IDE 可重试 | TRANSIENT | true |
| 6 | 内部失败 / 未知 | INTERNAL | 视情形 |

配套：`assetctl config validate [<id>]`（缺环境变量 → exit 3，**不得 hard-crash**）；`assetctl config version`。
> 注（PLAN-SANCTIONED）：`config validate` 成功信封是 `{"ok":true}`（`Missing` 字段 `omitempty`，空切片被省）；合同只固定**失败**形状 `{ok:false,missing:[…]}`。这是设计认可的行为，不是缺陷。

**D. 合同边界**：**不带**任何编排/流水线 loop（那是 codex 的职责，塞进 CLI 即违反原则 1）、DB、web UI、session、账号/providers。**只带**：`ATOMIC_TOOL_IDS` 各颗 + 支撑件 + 自检 A + `config validate`。

**E. 防漂移**：合同带语义版本号；`vendor/README` 钉对照基准 SHA（沿用 `videoctl`/`moonshort-script` 范式）；IDE 侧 parity/契约测试，版本或信封形状不符即失败。

## 18 颗原子能力（ATOMIC_TOOL_IDS，单一真相源 = `skill-source.ts`，源序）

`generate-image-nanobanana` `generate-image-gpt` `generate-video-seedance` `generate-sfx-elevenlabs` `generate-music-suno` `concat-clips` `crop-video` `generate-video-happyhorse` `cg-render` `nrbi-render-prompt` `upscale-image` `oss-put` `matting` `hybrid-to-webp` `green-spill-clear` `rgb-unspill` `hole-fill` `cutout`

> 本轮（foundation）**只有 `oss-put` 可跑**（真 Aliyun OSS 上传 + dryRun + 体积/路径校验，注入式 uploader 单测不触网，真网走 `//go:build integration` 选测）；其余 17 颗是可发现的 **NOT_IMPLEMENTED 桩**（exit 4，`retryable=false`，codex 不得重试），保证目录完整。

## IDE 侧落地（纯 Go，照 videoctl 现成模式）

- 源码：Go module 于 `vendor/assetctl/`（`internal/{contract,jsonschema,tools,tools/ossput,tools/iface,cli}` + `cmd/assetctl`）。模块声明 `go 1.23.0`（依赖钉版，与新工具链共存——刻意为之）。
- 构建：`fork/build.mjs` 的 `buildAssetctl()`（与 `buildVideoctl()` 并列，`go build ./cmd/assetctl`）→ `agents/asset/cli/assetctl/bin/assetctl`（gitignored，构建时出）。IDE 工具链零新增。
- 登记：`agents/asset/cli/bindings.json` 增 `assetctl` binding（与 `videoctl` 同形）。
- 重试落地：`agent-adapter` 的 `errors.ts`/`retry.ts` 按 §C 分类；`retryable=true` 退避重试，`GENERATION_REJECTED`/`config(3)` 不重试直接上抛。

## 实现状态（foundation 已完成，2026-05-20）

- 全部 13 个计划任务 + footgun 修复，TDD 落地；每任务两段评审（对规范 + 代码质量）→ 终审 APPROVE。
- 合并进 `moonshort-ide` 本地 `main`（fast-forward `b38dfda..3b70daa`，27 文件 +1891/-1，仅 assetctl 范围）。
- 验证全绿：`gofmt`/`go vet` 干净；`go test -race ./...` 全过；覆盖率 cli 84% / contract 93% / jsonschema 97.5% / tools 100% / ossput 85.1%（`cmd` 仅 main()、`iface` 无逻辑 = 计划认可例外）。`pnpm lint`/`typecheck`/`build`、绑定 `node --test`、`pnpm go:test` 在合并 main 上实跑通过。二进制冒烟对齐冻结合同（单行信封 / NOT_IMPLEMENTED exit4 / config 3 / config version 报 `0.1.0`+`48e6eb9`）。
- **未做（需明确许可）**：`git push` 到 `cdotlock/moonshort-ide`（非本人 namespace，全局规则需逐次同意）；本页对应的 mob-wiki 远端推送同理。

## 开放细节 & 后续（顺序死板 0→1→2→3）

- **O1 · assetctl↔videoctl 边界**：`generate-video-*`/`concat-clips`/`crop-video` 与 `videoctl` 是否重叠——后续 plan 定清（候选：assetctl 不收视频生成类全委派 videoctl；或 videoctl 专投递、生成类归 assetctl）。
- **第 2 块**（另起 spec→plan）：上游权威编排 skill + 知识 → codex staged skill，drift 一次性补齐。
- **第 3 块**（另起 spec→plan）：Langfuse-first 正文加载 + `skills sync`/`--check` parity（D2/D5 下成立）。
- 风险缓解：R1 Go 翻译走样 → 对拍测试 + 钉基准 SHA + 逐颗评审；R2 `python-runner` 类（matting 等）Go 化方案后续 plan 定；R3 缺凭据走 exit 3 不 crash；R4 能力按文件夹约定发现、不写死 stage。
