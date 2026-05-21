---
title: assetctl — 原子能力 CLI 接口合同 v0.1.0 (assets-produce → moonshort-ide)
created: 2026-05-20
updated: 2026-05-20
tags: [assetctl, assets-produce, moonshort-ide, atomic-capability, interface-contract, codex, oss-put, generate-image-nanobanana, generate-video-seedance, generate-sfx-elevenlabs]
status: draft
---

# assetctl — 原子能力 CLI 接口合同 v0.1.0

把 assets-produce 的**原子能力**以全 Go 重写吸收进 moonshort-ide：`assetctl` 是 IDE 内 codex（外围编排大脑）临场调度的、冻结接口合同的原子能力 CLI。流程写在 skill 里、不写死在代码里（assets-produce 原则 1/2）。

> 设计 spec：`moonshort-ide/docs/design/2026-05-19-assets-produce-integration-design.md`（项目内 git，未公开；commit `f8cdf81`）
> 实现计划：`moonshort-ide/docs/design/2026-05-19-assetctl-foundation-plan.md`（foundation，commit `b38dfda`）· `moonshort-ide/docs/design/2026-05-20-assetctl-wave1-plan.md`（Wave 1，commit `accd681`）
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

> Wave 6 完结后**共 14 颗可跑**（W1 4 颗 + W2 5 颗 + W3 3 颗 + W5 1 颗 + W6 1 颗）：Pattern A 1 颗（`oss-put`）+ Pattern A2 1 颗（`generate-sfx-elevenlabs`，直连 ElevenLabs + Aliyun OSS 二次上传）+ Pattern B **7** 颗 FC 网关（`generate-image-nanobanana`/`generate-image-gpt`/`generate-video-seedance`/`generate-video-happyhorse`/`concat-clips`/`crop-video`/**`cg-render`**）+ 占位 1 颗（`generate-music-suno`，Suno 无官方 API，返回确定性 placeholder）+ Pattern E 3 颗纯 Go 像素处理（`cutout` HSV 抠像/`green-spill-clear` leak mask/`rgb-unspill` G-channel clamp，PNG + WebP 输出）+ Pattern E2 1 颗 cgo + libwebp（`hybrid-to-webp`）。其余 **4 颗**仍是 **NOT_IMPLEMENTED 桩**（exit 4，`retryable=false`，codex 不得重试）：`nrbi-render-prompt`/`matting`/`hole-fill`/`upscale-image`（Wave 4 doc 中列出 W4-2/W4-3 lib 评估实验 + W4-5 业务驱动作为升级条件）。
>
> **`cg-render` Pattern B 是 scaffolding（W6）**：Go 侧完整 schema/body/MissingEnv/error mapping/dryRun 全部就位，覆盖率 100%；real-run 需要 backend 提供 `FC_CG_RENDER_URL` + `FC_CG_RENDER_TOKEN`，未设时返回 `CONFIG_MISSING`（exit 3）——与 nanobanana 缺 env 时行为一致。

## IDE 侧落地（纯 Go，照 videoctl 现成模式）

- 源码：Go module 于 `vendor/assetctl/`（`internal/{contract,jsonschema,aliyun,fc,imageio,webpio,tools,tools/iface,tools/ossput,tools/nanobanana,tools/seedance,tools/sfxelevenlabs,tools/gpt,tools/happyhorse,tools/suno,tools/concatclips,tools/cropvideo,tools/cutout,tools/greenspillclear,tools/rgbunspill,tools/hybridtowebp,cli}` + `cmd/assetctl`）。模块声明 `go 1.23.0`（依赖钉版，与新工具链共存——刻意为之）。Wave 1 抽出 **共享包**两枚：`internal/aliyun/`（OSS uploader 工厂，多工具共用）+ `internal/fc/`（FC gateway HTTP client，Pattern-B 工具共用，含 `Endpoint`/`Config`/`CallError`/`Client`/`Call`/`ExtractURL`/`MapError`/`IsHTTPS`）；Wave 2 在 `internal/jsonschema/` 加入 `Enum()` 与 `ObjectProp()`，让结构化数组（如 happyhorse `media[]`）能正确表达 `items: { type:"object", properties:..., required:... }`；Wave 3 新增 `internal/imageio/`（PIL-兼容 `RGBToHSV` H∈[0,360)/S/V∈[0,1] + `GaussianBlurAlpha` 可分离 1D 内核 clamp-edge + `ReadPNG`/`WritePNG`/`PromoteRGBA`/`ValidateInputPath`/`ValidateOutputPath`/`WritePlaceholderPNG`），供 3 颗纯 Go 像素处理工具共用。
- 构建：`fork/build.mjs` 的 `buildAssetctl()`（与 `buildVideoctl()` 并列，`go build ./cmd/assetctl`）→ `agents/asset/cli/assetctl/bin/assetctl`（gitignored，构建时出）。IDE 工具链零新增。
- 登记：`agents/asset/cli/bindings.json` 增 `assetctl` binding（与 `videoctl` 同形）。
- 重试落地：`agent-adapter` 的 `errors.ts`/`retry.ts` 按 §C 分类；`retryable=true` 退避重试，`GENERATION_REJECTED`/`config(3)` 不重试直接上抛。

## 实现状态

### Foundation（已完成 2026-05-20，main `3b70daa`）

- 全部 13 个计划任务 + footgun 修复，TDD 落地；每任务两段评审（对规范 + 代码质量）→ 终审 APPROVE。
- 合并进 `moonshort-ide` 本地 `main`（fast-forward `b38dfda..3b70daa`，27 文件 +1891/-1，仅 assetctl 范围）。
- 验证全绿：`gofmt`/`go vet` 干净；`go test -race ./...` 全过；覆盖率 cli 84% / contract 93% / jsonschema 97.5% / tools 100% / ossput 85.1%（`cmd` 仅 main()、`iface` 无逻辑 = 计划认可例外）。`pnpm lint`/`typecheck`/`build`、绑定 `node --test`、`pnpm go:test` 在合并 main 上实跑通过。二进制冒烟对齐冻结合同（单行信封 / NOT_IMPLEMENTED exit4 / config 3 / config version 报 `0.1.0`+`48e6eb9`）。

### Wave 1（已完成 2026-05-20，main `c7e7f0c`）

- 5 个任务（W1-1 → W1-5）TDD 落地；每任务两段评审 + 评审反馈 cleanup commit。共 17 个 atomic commit（feat 5、fix 2、refactor 5、test 3、docs 1、build 1）。
- 合并进 `moonshort-ide` 本地 `main`（fast-forward `accd681..c7e7f0c`，新增 8 文件，含 `internal/aliyun/` + `internal/fc/` + 3 个新 tool 包）。
- **能力扩展**：4 颗可跑（oss-put + nanobanana + seedance + sfxelevenlabs），覆盖三种实现 pattern（A · OSS 直连；A2 · 直连 vendor + OSS 二次上传；B · FC 网关 → mob-ai）。
- **共享件**：`internal/aliyun/`（多工具复用 OSS uploader）+ `internal/fc/`（Pattern-B FC HTTP client）+ `internal/jsonschema/` 扩展（Number/Array/Pattern/MinLen/MaxLen/Min/Max/ExclusiveMin/MinItems/MaxItems，11-key marshal 顺序锁定）。
- **接口扩展**：`iface.Tool.MissingEnv() []string` 加入接口；`config validate`（无 `<id>`）改为聚合所有 runnable tool 的 `MissingEnv()` 去重+排序后返回。
- 验证全绿：`gofmt -l` 空、`go vet ./...` clean、`go vet -tags=integration ./...` clean、`go test -race -count=1 ./...` 全过。
- 覆盖率（race + cover）：`aliyun 87.0%` / `cli 88.7%` / `contract 92.9%` / `fc 92.3%` / `jsonschema 98.8%` / `tools 94.1%` / `nanobanana 100.0%` / `ossput 98.1%` / `seedance 100.0%` / `sfxelevenlabs 95.8%`（全部超过 plan 阈值 ≥80%；多颗满 100%）。
- IDE 主仓 main 上 `pnpm lint` / `pnpm typecheck` / `pnpm go:test` 实跑通过；二进制冒烟：`tools list` 18 颗（4 runnable + 14 NOT_IMPLEMENTED）、`tools schema --format anthropic|openai` 各 18 个 descriptor、`config validate` 缺环境返回 sorted 9-entry missing 列表、3 颗新工具 `run ... --input '{...,"dryRun":true}'` 各自返回符合合同的单行信封，body 字段顺序与 donor 字节一致（FC 工具 donor body 序固定经 fcBody struct 强制，非 `map[string]any` 字母序）。
- **未做（需明确许可）**：`git push` 到 `cdotlock/moonshort-ide`（非本人 namespace，全局规则需逐次同意）；本页对应的 mob-wiki 远端推送同理。

### Wave 2（已完成 2026-05-20，main `b8b7f94`）

- 5 个任务（W2-1 → W2-5）TDD 落地；每任务两段评审（W2-1 完整跑过双段评审，其余因 pattern 已成熟改走实施+轻评审）。共 10 个 atomic commit（feat 7、refactor 3：2 颗 jsonschema 扩展 + 1 颗 happyhorse media schema 重构）。
- 合并进 `moonshort-ide` 本地 `main`（fast-forward `30718f3..b8b7f94`，新增 10 文件 1909 +/0 -）。
- **能力扩展**：5 颗新可跑工具——`generate-image-gpt`（B · FC，default `gpt-image-1`）、`generate-video-happyhorse`（B · FC，结构化 `media[]` 数组 + 可选 enum 字段 resolution/ratio/duration）、`generate-music-suno`（确定性 placeholder · 上游 Suno 无官方 API，返回固定占位信封）、`concat-clips`（B · FC，纯 FFmpeg 拼接）、`crop-video`（B · FC，纯 FFmpeg 裁剪）。Wave 2 后总计 **9 颗可跑**（含 W1 的 4 颗），剩 9 颗 Python 桩。
- **共享件再扩展**：`internal/jsonschema/` 加 `Enum(values...)` 与 `ObjectProp(s *Schema, desc)`（嵌套对象 items，marshal 顺序锁定为 type → minLen → maxLen → pattern → enum → minimum → maximum → exclusiveMin → items → minItems → maxItems → properties → required → description）。
- **新建立的范式**：placeholder 工具同样实现 `iface.Tool` 接口，`MissingEnv()` 返回 nil，`Run()` 直返固定信封（dryRun 与 default 同路径，符合 donor 规约）。FC body field 顺序通过专用 fcBody struct 强制；nested object schema 通过 `ObjectProp` 表达，不再使用 flat-Prop hack。
- 验证全绿：`gofmt -l` 空、`go vet ./...` clean、`go test -race ./...` 全过。覆盖率（race + cover，新工具）：`gpt 100.0%` / `happyhorse 94.3%` / `suno 100.0%` / `concatclips 100.0%` / `cropvideo 100.0%` / `jsonschema 99.1%`（含 ObjectProp 100%）。整体覆盖率 96.2%。
- IDE 主仓 main 上 `pnpm lint` / `pnpm typecheck` / `pnpm go:test` 实跑通过；二进制冒烟：`tools list` 18 颗（**9 runnable** + 9 NOT_IMPLEMENTED）、5 颗新工具 `dryRun` envelope body 字段顺序与 donor TS 一致（gpt: prompt → model；happyhorse: action → prompt → media；concat: clipUrls 单字段；crop: videoUrl → startTime → endTime；suno: placeholder 字段集与 metadata 一致）。

### Wave 3（已完成 2026-05-20，main `bea7017`）

- 5 个任务（W3-1 → W3-5）TDD 落地，每任务 fresh implementer subagent → spec compliance review → code quality review → atomic follow-up commit；共 10 个 atomic commit（feat 5、refactor 4、docs 1）。pattern decision doc 已闭环：Wave 3 实现 3 颗 Pattern E（纯 Go 像素重写），剩余 6 颗 F (stub) 留给 Wave 4 升级评估（见 `docs/design/2026-05-20-assetctl-wave4-stub-upgrade-evaluation.md`）。
- 合并进 `moonshort-ide` 本地 `main`（fast-forward `a14b5fb..bea7017`，新增 12 文件 +约2200 行 / 0 删，含 plan doc + 4 个 internal/imageio 文件 + 3 个 tool 实现 + 3 个 tool 测试 + registry 1 行）。
- **能力扩展**：3 颗新可跑工具——`cutout`（E · HSV 抠像，hueLow/hueHigh/satMin/valMin/feather 五参数 + 可选高斯 feather + 旧 alpha 保留 min 语义）；`green-spill-clear`（E · RGBA 泄漏 mask + zero，非 RGBA 输入 promote+passthrough）；`rgb-unspill`（E · Nuke 风格 G 通道 clamp 到 max(R,B)，Wave 3 仅 .png 输出，.webp 输出推迟 Wave 4 评估 libwebp cgo）。Wave 3 后总计 **12 颗可跑**（W1 4 + W2 5 + W3 3），剩 6 颗 F-stub。
- **新共享层**：`internal/imageio/` 包提供 PIL-兼容 `RGBToHSV(r, g, b uint8) (h, s, v float64)`（H 度数 [0,360)，S/V [0,1]，textbook 公式）+ `GaussianBlurAlpha(alpha, w, h, sigma)`（可分离 1D 高斯 + clamp edge + sigma≤0 守卫返回 identity copy）+ PNG I/O wrappers（ReadPNG/WritePNG/PromoteRGBA/ValidateInputPath/ValidateOutputPath/WritePlaceholderPNG）。stdlib-only，零新 go.mod 依赖。
- **新建立的范式**：本地输出工具（无 OSS 上传）envelope = `data.assets[0].loc` 为绝对本地路径（合同 §4-B 明确允许）；mock 模式写 1×1 stdlib NRGBA PNG（不复刻 donor 手工 struct+zlib 字节，合同只要求 "valid PNG"）；image.Decode 类型 switch 处理 `*image.NRGBA`（donor 8-bit color-type-6 默认路径）+ `*image.RGBA`（premultiplied caller 路径，via PromoteRGBA 自动 unpremultiply）+ 其他类型（Gray/Paletted 等）一律 PromoteRGBA write-through。
- 验证全绿：`gofmt -l` 空、`go vet ./...` clean、`go test -race ./...` 全过。覆盖率（race + cover，新工具与 imageio）：`imageio 92.3%` / `cutout 91.6%` / `greenspillclear 90.3%` / `rgbunspill 91.7%`（全部超过 plan 阈值 ≥90%）。其余包覆盖率与 Wave 2 持平或微增。
- IDE 主仓 main 上 `pnpm lint` / `pnpm typecheck` / `pnpm go:test` 实跑通过；二进制冒烟：`tools list` 18 颗（**12 runnable** + 6 NOT_IMPLEMENTED）、3 颗新工具 `mock:true` envelope 内容与字段顺序符合合同（`tool`/`input_path`/`output_path`/`params`/`assets[0].{kind:image,name,loc}` + `mock:true`），物理产物为 1×1 transparent NRGBA PNG。
- **未做（需明确许可）**：`git push` 到 `cdotlock/moonshort-ide`（非本人 namespace，全局规则需逐次同意）；本页对应的 mob-wiki 远端推送同理。Wave 4 stub 升级评估 doc 已在 main，作为 Wave 5+ 决策输入。

### Wave 4 stub 升级评估（已完成 2026-05-20，main `14594de`）

**不实现任何工具，只做评估**。Wave 4 是从 Wave 3 起新增的一个评估阶段，目的是给剩下 6 颗 F-stub 找出"什么条件下值得升 E/D"——结论写在 `docs/design/2026-05-20-assetctl-wave4-stub-upgrade-evaluation.md`，作为 Wave 5+ 实施优先级的决策输入。

**评估矩阵**：6 颗 F-stub × 升级路径 × 阻塞条件

| F-stub | 候选升级路径 | 评估阶段 | 结论摘要 |
|---|---|---|---|
| `hybrid-to-webp` | E · cgo + libwebp (chai2010/webp) | W4-1 ✅ PoC done | macOS arm64 native ✅ 直接通过（libwebp C 源 v1.4.0 自带，无系统依赖；assetctl 体积 +约 3 MB）；linux 跨编译 ❌ 需 zig/musl-cross 工具链（约 0.5–1 人天） |
| `rgb-unspill` .webp 子能力 | E · 同上 | W4-1 ✅（合并评估） | 同 hybrid-to-webp 结论；Wave 3 实现已留 `.webp` 输出拒绝路径，升级即解除 |
| `hole-fill` | E · cgo + gocv (OpenCV) | W4-2 ❌ PoC 未做 | 需系统 libopencv 安装（重量级），跨平台 build 复杂度高；不及 W4-1 经济 |
| `matting` | E · cgo + onnxruntime_go + MODNet | W4-3 ❌ PoC 未做 | 需 onnxruntime 动态库 + MODNet onnx 权重缓存策略；Apple Silicon benchmark 待跑 |
| ~~`cg-render`~~ | B · FC 网关 scaffolding | **W6 ✅ 2026-05-21** | Go 侧 Pattern B 完整落地（套 nanobanana 模板，无 ZENMUX/Python 痕迹，回归 guard 测锁定）；待 backend 提供 `FC_CG_RENDER_URL` + `FC_CG_RENDER_TOKEN` 才能 real-run（缺 env → `CONFIG_MISSING` exit 3）|
| `upscale-image` | D · cgo + Real-ESRGAN ONNX | W4-4 业务驱动 | 体积爆增（>50 MB ONNX）+ Apple Silicon GPU 加速复杂；**不推荐除非业务必需** |
| `nrbi-render-prompt` | E · 文本处理（无外部依赖） | W4-5 业务驱动 | 升级简单，等 nrbi 业务需求成型再做对拍基础设施 |

**W4-1 PoC 实测（2026-05-20）**：在 `/tmp/w4-1-webp-eval/` 写了最小 main.go 用 `github.com/chai2010/webp v1.4.0`。macOS arm64 `go build` 直接通过——chai2010/webp 内联 libwebp C 源（无需 `brew install webp`）；3.8 MB binary，编码 1×1 红色 NRGBA → 72 字节有效 VP8 WebP。Linux amd64 跨编译失败（macOS SDK 头不含 linux syscalls，cgo 解析 `setresuid`/`setresgid` 失败）——这是预期结果，验证了 doc 中 "linux 升级需 cross toolchain" 的预测。

**Wave 4 决策**：W4-1 是最低成本 F→E 候选（2 颗能力解锁，3 MB binary 代价，macOS 立即可用，linux 需 0.5-1 人天 toolchain）。其余 5 颗（W4-2/3/4/5）触发条件 = Block 2 编排 skill 实际调用频次 + 业务需求成型，不在 Wave 5 范围内。Wave 4 评估阶段闭环；W4-2/W4-3 PoC 留待业务驱动启动。



### Wave 5（已完成 2026-05-20，main `8900997`）

- 5 个任务（W5-1 → W5-5）TDD 落地，每任务 fresh implementer subagent → spec compliance review → code quality review → atomic follow-up commit；共 10 个 atomic commit（plan 1 + feat 4 + refactor 3 + test 1 + build 1）。Wave 5 引入 **assetctl 第一个 cgo 依赖**：`github.com/chai2010/webp v1.4.0`（内置 libwebp C 源，零系统依赖）；零 brew install libwebp 必需。
- 合并进 `moonshort-ide` 本地 `main`（fast-forward `90d7280..8900997`，新增 5 文件 +约 2400 行 / 改 3 文件 +约 250 行）。
- **能力扩展**：1 颗新可跑工具 + 1 颗 Wave 3 工具扩展输出格式——`hybrid-to-webp`（E2 · cgo + libwebp，schema 与 donor 一致 7 字段：quality/method/overwrite/mock/dryRun，method 接受参数但 chai2010/webp 用 libwebp 默认 method 内部封装，对 donor 行为是已记录的发散）；`rgb-unspill` 扩 `.webp` 输出（新增 `webpQuality` schema 字段 default 90；mock + `.webp` 经 W5-3 review 找到 bug 后修正——`mock:true` + `.webp` 现在产物为有效 WebP，不再是 PNG 假冒）。Wave 5 后总计 **13 颗可跑**（W1 4 + W2 5 + W3 3 + W5 1），剩 5 颗 NOT_IMPLEMENTED 桩。
- **新共享层**：`internal/webpio/` 包提供 `WriteWebP(img image.Image, path string, opts WriteOptions) error` + `WritePlaceholderWebP(path string) error` + `WriteOptions{Quality float32, Lossless bool}` + 私有 `nrgbaToRGBA` helper（取 imageio.PromoteRGBA 的 `*image.NRGBA` 返回值转 `*image.RGBA` 避免 chai2010/webp 内部 `toRGBAImage` 慢路径）。
- **新建立的范式**：Pattern E2 = cgo + bundled C 源；Go 字段命名 WebP 初始词大小写（`WebPQuality`、`WriteWebP`，不是 `Webp...`）；mock 模式按输出扩展名分支到对应 placeholder writer（不能一律写 PNG）；可选 numeric param 用 `*int` 区分 omitted vs explicit zero（Wave 3 沿用）。
- **构建基础设施**：`fork/build.mjs` 的 `buildAssetctl()` 加入 `CGO_ENABLED=1` + 检测 `HOST_GO` 与 `target` 是否一致；若跨编译，设 `CC="zig cc -target X"` 与 `CXX="zig c++ -target X"`，并验证 `zig version` 可调用否则 `fail()` 报清晰错误。`ZIG_TARGETS` 映射：`linux/amd64=x86_64-linux-musl`、`linux/arm64=aarch64-linux-musl`、`windows/amd64=x86_64-windows-gnu`。macOS host → macOS target **不需要 zig**（native cc 处理 cgo）；`mss` / `mss-lsp` / `videoctl` 维持纯 Go，不受影响。
- 验证全绿：`gofmt -l` 空、`go vet ./...` clean、`go vet -tags=integration ./...` clean、`go test -race ./...` 全过。覆盖率：`webpio 94.4%` / `hybridtowebp 93.5%` / `rgbunspill 91.7%`（含 .webp 路径全覆盖）。其余包未回归。
- 跨编译 smoke（用最终 fork/build.mjs 的等价 `go build` invocation）：
  - macOS arm64 native（CGO_ENABLED=1，无 CC）：11.6 MB Mach-O
  - Linux amd64 via `zig cc -target x86_64-linux-musl`：18.8 MB statically-linked ELF
  - Linux arm64 via `zig cc -target aarch64-linux-musl`：18.1 MB statically-linked ELF
  - 三个目标全部 chai2010/webp（libwebp C 源）编译通过，无系统 libwebp 依赖
- IDE 主仓 main 上 `pnpm lint` / `pnpm typecheck` / `pnpm go:test` 实跑通过；二进制冒烟：`tools list` 18 颗（**13 runnable** + 5 NOT_IMPLEMENTED）、`hybrid-to-webp mock:true` envelope 含 `assets[0].loc` + `mock:true`，物理产物 = 1×1 transparent WebP（`file out.webp` 报 RIFF Web/P）；`rgb-unspill mock:true outputPath=.webp` 同样产出有效 WebP（W5-3 MEDIUM bug fix 后）。
- **未做（需明确许可）**：`git push` 到 `cdotlock/moonshort-ide`（非本人 namespace，全局规则需逐次同意）；本页对应的 mob-wiki 远端推送同理。Wave 4 doc 中余下 4 个升级候选（W4-2 gocv `hole-fill` / W4-3 onnxruntime_go `matting` / W4-4 backend `cg-render` / W4-5 业务驱动 `nrbi-render-prompt`，含拒绝候选 `upscale-image`）维持 deferred 直至业务驱动启动。

### Wave 6（已完成 2026-05-21，main `2099f03`，推 `dev/assets-produce-integration-2026-05-21`）

- 1 颗工具（cg-render）TDD 落地，fresh implementer subagent → spec compliance review → go-reviewer code quality review → atomic refactor follow-up commit；共 3 个 atomic commit（feat 2 + refactor 1）。Wave 6 是 W4-4 "backend 端点" 路径的 Go 侧 scaffolding，触发条件 = 后续 backend 同事提供 `FC_CG_RENDER_URL` + `FC_CG_RENDER_TOKEN`。
- 合并进 `moonshort-ide` 本地 `main`（FF `70efdd0..2099f03`），新文件 2 + 改文件 2（cli_test.go aggregate env list 同步 + registry.go realTools 加 cg-render）。
- **能力扩展**：1 颗新 Pattern B 可跑工具——`cg-render`（schema 7 props：slug/cgName/prompt/referenceImageUrls 4 required + panelCount/model/dryRun 3 optional；fcBody 6 字段固定顺序 slug→cgName→prompt→model→panelCount→referenceImageUrls，**panelCount 与 referenceImageUrls 都不带 `omitempty`**——backend 拿到的 body shape 永远稳定）。Wave 6 后总计 **14 颗可跑**（W1 4 + W2 5 + W3 3 + W5 1 + W6 1），剩 4 颗 NOT_IMPLEMENTED 桩。
- **新建立的范式（一次性回归 guard）**：donor `cg-render.ts` / `cg-render.txt` 字面上说"via ZENMUX (google-genai)"——这是 donor 的 Python 时代字面，新 Go 实现走 FC 网关（=mob-ai 路由），新 summary/comments/identifiers 一律不沾 ZENMUX/Python/google-genai。`TestSummaryHasNoZenmuxOrPython` 单测同时断言 summary 含 "FC endpoint" + 拒绝 ZENMUX/Python/google-genai 字眼，是回归 guard 锁死字面层契约的范本。
- **命名一致性 fix**：code-quality review 抓到 `params.ReferenceImageURLs` (URL acronym) vs `fcBody.ReferenceImageUrls` (Urls) 文件内不一致——sibling tools 全用 `Urls`（nanobanana/gpt/seedance/happyhorse），cg-render 沿用 sibling 形（json tag `referenceImageUrls` 不变，wire 字节不变）；同时清死 `stubResponse` test helper（W1-4/W1-5 dead-helper 反 pattern 复发）。
- 验证全绿：`gofmt -l` 空、`go vet ./...` clean、`go test -race ./...` 全过；`cgrender` 覆盖率 **100%**。`tools list` 14 runnable + 4 stubs；`tools schema cg-render --format openai` 7 props order 正确；`run cg-render --dryRun` envelope body 在 donor 顺序，`panelCount:1` 默认 emit。
- **未做**：backend 真端点（业务驱动）；wiki 远端推送（用户 2026-05-21 仅授权 `dev/*` 分支推 `cdotlock/moonshort-ide`，wiki main 推未授权）；Wave 4 doc 中余下 4 个升级候选维持 deferred（W4-2 `hole-fill` / W4-3 `matting` / W4-5 `nrbi-render-prompt` / `upscale-image`）。

## 开放细节 & 后续（顺序死板 0→1→2→3）

- **O1 · assetctl↔videoctl 边界**：`generate-video-*`/`concat-clips`/`crop-video` 与 `videoctl` 是否重叠——后续 plan 定清（候选：assetctl 不收视频生成类全委派 videoctl；或 videoctl 专投递、生成类归 assetctl）。
- **第 2 块**（另起 spec→plan）：上游权威编排 skill + 知识 → codex staged skill，drift 一次性补齐。
- **第 3 块**（另起 spec→plan）：Langfuse-first 正文加载 + `skills sync`/`--check` parity（D2/D5 下成立）。
- 风险缓解：R1 Go 翻译走样 → 对拍测试 + 钉基准 SHA + 逐颗评审；R2 `python-runner` 类（matting 等）Go 化方案后续 plan 定；R3 缺凭据走 exit 3 不 crash；R4 能力按文件夹约定发现、不写死 stage。
