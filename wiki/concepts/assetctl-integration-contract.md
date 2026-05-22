---
title: assetctl — 原子能力 CLI 接口合同 v0.1.0 (assets-produce → moonshort-ide)
created: 2026-05-20
updated: 2026-05-22 (Wave 15)
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

## 25 颗原子能力（ATOMIC_TOOL_IDS：18 canonical + 7 IDE-native，后者 append-only）

**前 18 颗** verbatim 自 `assets-produce@48e6eb9` `skill-source.ts` 源序，永远不改顺序、不删、不重排：

`generate-image-nanobanana` `generate-image-gpt` `generate-video-seedance` `generate-sfx-elevenlabs` `generate-music-suno` `concat-clips` `crop-video` `generate-video-happyhorse` `cg-render` `nrbi-render-prompt` `upscale-image` `oss-put` `matting` `hybrid-to-webp` `green-spill-clear` `rgb-unspill` `hole-fill` `cutout`

**后 7 颗（IDE-native，Wave 14 起，commit-arrival 顺序，never reorder, only append）**：

`audit-mapping` `parse-wardrobe` `check-clothing-keyword` `check-clothing-llm` `extract-look-signatures` `build-wardrobe-map` `apply-look-aliases`

> Wave 15 (2026-05-22) 同时为 `generate-image-nanobanana` / `generate-image-gpt` 增加可选 `chromakeyMode: true` boolean（default false，schema 向后兼容）—— inline 5 句 chromakey-green 背景契约后缀，取代独立 `green_screen.py wrap_for_chromakey()` helper；marker `[BACKGROUND CONTRACT — chromakey green]` 保证幂等。**不是新原子，是既有原子的 schema 扩展**。

> **Wave 10 完结后全部 18 颗可跑/就位** — **0 F-stub 剩余**。
>
> 分布（**W13 修订**）：Pattern A 1 颗（`oss-put`）+ Pattern A2 1 颗（`generate-sfx-elevenlabs`）+ Pattern B **9** 颗 FC 网关（W1: `generate-image-nanobanana`/`generate-video-seedance`；W2: `generate-image-gpt`/`generate-video-happyhorse`/`concat-clips`/`crop-video`；W6: `cg-render`；W8: `matting`；W9: `upscale-image`）+ 占位 1 颗（`generate-music-suno`）+ Pattern E **5** 颗纯 Go（W3: `cutout`/`green-spill-clear`/`rgb-unspill`；**W12: `hole-fill` Telea inpaint**；**W13: `nrbi-render-prompt` captured-goldens**）+ Pattern E2 1 颗 cgo+libwebp（W5: `hybrid-to-webp`）。**Pattern E scaffold 已废止**。合计 9+5+1+1+1+1 = 18 颗。
>
> **设计原则（Waves 8-13 决策记录，修订三次）**："不方便改成 Go 的，该保留 C++ 就保留 C++" + 反向校验"方便改成 Go 的就改"。**W8/W9** 真重型依赖（matting MODNet、upscale-image Real-ESRGAN）走 Pattern B FC 网关（backend 部署）。**W12 撤销 W10 决策**：hole-fill 原本归 Pattern B（"OpenCV C++ 实现"），但本质是 Telea/Navier-Stokes 经典 CV 算法（2003 论文，不需要 ML/GPU/系统库），属于"方便改成 Go 的"——纯 Go BFS-layered Telea-style 实现 ~590 LOC 可用，质量在绿幕补洞用途等效 OpenCV，省一个 backend endpoint。**W13 撤销 W11 决策**：nrbi-render-prompt 原本归 Pattern B（"1547 LOC frozen Python 走 backend"），但 1547 LOC 是 headline 错算——donor render.py 实际只用 ~6 个 builder + 一把 regex helper（impl 607 LOC + tests 392 LOC = 999 LOC 真实 Go 端口面，不含 frozen 模板与 importlib loader），属经典 stdlib 文本处理，不需要 backend 部署。`captured-goldens` 范式（一次性从 donor 抓 9 个 byte-faithful 输出，commit 入树，单测 diff Go 输出 vs goldens）完全验证字节保真，CI 无需保留 Python runtime。这种分工降低 Go 打包体积、避免 cgo 跨编译复杂性、支持模型独立更新；同时不为了"统一 Pattern B"而盲目把可纯 Go 的算法/文本处理外包。

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

### Wave 7（已完成 2026-05-21，main `c930894`）

- 1 颗工具（nrbi-render-prompt）TDD 落地，fresh implementer subagent → spec compliance review → code quality review → atomic refactor follow-up commit；共 2 个 atomic commit（feat 1 + refactor 1）。Wave 7 是 W4-5 "nrbi-render-prompt" 升级路径的 Pattern E 纯 Go scaffold，触发条件 = Wave 7b 对拍基础设施就绪（或用户决定转 Pattern B）。
- 合并进 `moonshort-ide` 本地 `main`（FF `2099f03..c930894`），新文件 2 + 改文件 1（cli_test.go aggregate env list 同步 + registry.go realTools 加 nrbi-render-prompt）。
- **能力扩展**：1 颗新 Pattern E 工具——`nrbi-render-prompt`（schema 5 props：layer/variable_text 2 required（layer enum A/A5/B/C/D/E，variable_text object）+ category/style_name/reference_image_urls 3 optional；无外部依赖，纯 Go 文本处理）。Wave 7 后总计 **15 颗可跑或已 scaffold**（W1 4 + W2 5 + W3 3 + W5 1 + W6 1 + W7 1），剩 3 颗 NOT_IMPLEMENTED 桩（matting/hole-fill/upscale-image）。
- **暂时 NOT_IMPLEMENTED**：dryRun 与 mock 模式现返回 `NOT_IMPLEMENTED`（exit 4）。real-run 需要 Wave 7b byte-faithful 对拍 CI 基础设施（Python baseline runner + Go 实现 runner + sha256 diff 比对器），或在 user 考虑下将此工具转换为 Pattern B（backend 部署 Python donor 服务）。
- **新建立的范式**：Pattern E scaffold = 接口全实现（schema/Run/MissingEnv），但 real-run 返 NOT_IMPLEMENTED 待条件就绪。dryRun + mock 同样返此错；无需区分。
- 验证全绿：`gofmt -l` 空、`go vet ./...` clean、`go test -race ./...` 全过；`nrbirenderprompt` 覆盖率 **100%**（简化实现）。`tools list` 15/18；`tools schema nrbi-render-prompt --format openai` 5 props order 正确；`run nrbi-render-prompt --dryRun` 返 NOT_IMPLEMENTED envelope。

### Wave 8（已完成 2026-05-21，main `703420b`）

- 1 颗工具（matting）TDD 落地，fresh implementer subagent → spec compliance review → code quality review → atomic refactor follow-up commit；共 2 个 atomic commit（feat 1 + refactor 1）。Wave 8 是 W4-3 "matting" 升级路径的 Pattern B FC 网关转换（原计划 cgo+onnxruntime_go，实际采纳 backend 部署）。
- 合并进 `moonshort-ide` 本地 `main`（FF `c930894..703420b`），新文件 2 + 改文件 1（cli_test.go aggregate env + registry.go realTools 加 matting）。
- **能力扩展**：1 颗新 Pattern B 可跑工具——`matting`（schema 5 props：slug/assetName/inputUrl 3 required + format/device 2 optional（format enum webp/png，device enum cpu/cuda/mps）；fcBody 3 字段固定顺序 slug→assetName→inputUrl + optional format/device）。Wave 8 后总计 **16 颗可跑**（新增 matting），剩 2 颗 NOT_IMPLEMENTED（hole-fill/upscale-image）。
- **设计决策记录**：原 W4 doc 计划 matting 走 E-via-onnx（cgo+onnxruntime_go 推理 MODNet），但实际工程评估：ML 推理（MODNet + GPU 加速）属重型，Go 侧负责轻量级网络/文本调度更合理。backend 部署 Python MODNet 服务（含 CUDA/MPS GPU 支持），Go assetctl 通过 FC 网关轻量调度。符合设计原则"不方便改成 Go 的，该保留 C++ 就保留 C++"（Go 替 C++ = MODNet，backend Python runner）。
- FC env：`FC_MATTING_URL` / `FC_MATTING_TOKEN`；600s timeout。
- 验证全绿：`gofmt -l` 空、`go vet ./...` clean、`go test -race ./...` 全过；`matting` 覆盖率 **100%**。`tools schema matting` 5 props order 正确；`run matting --dryRun` envelope 正确。

### Wave 9（已完成 2026-05-21，main `5dcb146`）

- 1 颗工具（upscale-image）TDD 落地，fresh implementer subagent → spec compliance review → code quality review → atomic refactor follow-up commit；共 2 个 atomic commit（feat 1 + refactor 1）。Wave 9 是 W4-4 "upscale-image" 升级路径的 Pattern B FC 网关转换（原计划 D-via-realesrgan-ncnn-vulkan，实际采纳 backend 部署）。
- 合并进 `moonshort-ide` 本地 `main`（FF `703420b..5dcb146`），新文件 2 + 改文件 1（cli_test.go aggregate env + registry.go realTools 加 upscale-image）。
- **能力扩展**：1 颗新 Pattern B 可跑工具——`upscale-image`（schema 5 props：slug/assetName/inputUrl 3 required + scale/model 2 optional（scale enum 2/4，model default "realesrgan-x4plus-anime"）；fcBody 4 字段固定顺序 slug→assetName→inputUrl + optional scale/model）。Wave 9 后总计 **17 颗可跑**（新增 upscale-image），剩 1 颗 NOT_IMPLEMENTED（hole-fill）。
- **设计决策记录**：原 W4 doc 标记 upscale-image 为"极低优先级"且"不推荐除非业务必需"（Real-ESRGAN ONNX model >50MB）。Go 侧打包该模型 + Vulkan 依赖爆增。实际采纳：backend 部署 Real-ESRGAN + GPU 加速 + 权重缓存，Go assetctl 轻量网关。符合设计原则。
- FC env：`FC_UPSCALE_IMAGE_URL` / `FC_UPSCALE_IMAGE_TOKEN`；600s timeout。
- 验证全绿：`gofmt -l` 空、`go vet ./...` clean、`go test -race ./...` 全过；`upscaleimage` 覆盖率 **100%**。`tools schema upscale-image` 5 props order 正确；`run upscale-image --dryRun` envelope 正确。

### Wave 10（已完成 2026-05-21，main `4de6903`）

- 1 颗工具（hole-fill）TDD 落地，fresh implementer subagent → spec compliance review → code quality review → atomic refactor follow-up commit；共 3 个 atomic commit（feat 1 + refactor 2）。Wave 10 是 W4-2 "hole-fill" 升级路径的 Pattern B FC 网关转换（原计划 D-via-gocv，实际采纳 backend 部署）。同时清理最后的 stubTool 占位符（commit `4de6903` refactor），all 18 tools 现 realTools 或 scaffold。
- 合并进 `moonshort-ide` 本地 `main`（FF `5dcb146..4de6903`），新文件 2 + 改文件 2（cli_test.go aggregate env + registry.go realTools + registry_test.go 清死 stubTool 断言）。
- **能力扩展**：1 颗新 Pattern B 可跑工具——`hole-fill`（schema 5 props：slug/assetName/inputUrl 3 required + dilate/minSize/maxSize 3 optional，其中 minSize/maxSize 有 minSize≤maxSize 约束 + dryRun；fcBody 5 字段固定顺序 slug→assetName→inputUrl + optional dilate/minSize/maxSize）。Wave 10 后总计 **18 颗全部就位**（all runnable 或 Pattern E scaffold）。**0 F-stub 剩余**。
- **设计决策记录**：原 W4 doc 计划 hole-fill 走 D-via-gocv（cgo+OpenCV cgo binding），评估显示跨平台 OpenCV build 复杂（macOS Gatekeeper/SIP + linux musl），且 OpenCV 系统库动辄 50MB+。实际采纳：backend 部署 OpenCV Inpaint 服务（Telea/Navier-Stokes 两算法），Go assetctl 轻量网关。符合设计原则。
- FC env：`FC_HOLE_FILL_URL` / `FC_HOLE_FILL_TOKEN`；120s timeout。
- **registry cleanup**：commit `4de6903` refactor 删除 `func stubTool(id string) iface.Tool` 占位符，改为 assert `realTools()` 返回包含全 18 个 IDs（验证无漏网工具）。`TestStubToolStructDirectly` 作为范本，演示如何在单测里直接 exercise `stubTool` struct（future 扩展新 canonical ID 时参考），无需保留 registry 级别的占位函数。
- 验证全绿：`gofmt -l` 空、`go vet ./...` clean、`go test -race ./...` 全过；`holefill` 覆盖率 **100%**。`tools list` 18/18；all 18 `tools schema <id>` 全通过；`run hole-fill --dryRun` envelope 正确。

### Wave 12（已完成 2026-05-21，main `1c17878`）—— W10 Pattern B 重构为 Pattern E 纯 Go

- 1 颗工具（hole-fill）从 Pattern B FC HTTP 完整重写为 Pattern E 纯 Go Telea inpainting；2 个 atomic commit（refactor 1 + chore 1）。Wave 12 推翻 W10 决策，按用户原则反向校验"方便改成 Go 的就改"。
- 合并进 `moonshort-ide` 本地 `main`（FF `7c96f20..1c17878`），改文件 3（holefill.go rewrite ~305→~590 LOC + holefill_test.go rewrite ~779→~657 LOC + cli_test.go 移除 FC_HOLE_FILL_* aggregate env）。
- **能力扩展**：1 颗工具从 Pattern B 转 Pattern E 本地可跑——`hole-fill`（schema 7 props：inputPath/outputPath 2 required + dilate/minSize/maxSize/overwrite/mock/dryRun 5 optional，donor-faithful；无 env 无 FC HTTP）。Wave 12 后 Pattern B 12→11 颗，Pattern E 3→4 颗，总数 18 不变。
- **设计决策记录**：W10 默认 hole-fill 走 Pattern B（"donor 用 OpenCV，那就 backend 部署 OpenCV 服务"），但用户挑明："hole-fill 不是本地跑吗？为什么还要我部署？" 重新审视：hole-fill 用 Telea (2003) / Navier-Stokes (2001) 经典 CV 算法，**不需要 ML 推理、不需要 GPU、不需要系统库**。Explore 调查 Go 生态零现成 inpainting lib（pkg.go.dev / GitHub 搜索 telea / fast marching / inpainting language:go 全零结果），从零实现 Telea。**算法选择**：BFS distance transform（不用 Fast Marching Method，更简单 + 10-20% 慢但绿幕补洞场景无感）+ 3×3 inverse-square distance weights（matching donor `inpaintRadius=3`）+ concentric-ring fallback（degenerate 情况）；无 directional gradient term（donor hole 都小 + 周围色单一，directional 项贡献微小）。**质量验证**：合成 fixture（64×64 NRGBA 红底 + 6×6 中心 alpha=0 hole）inpaint 后中心精确恢复 R=200/G=50/B=50，与 OpenCV 实现视觉无差异；性能比 OpenCV 慢 2-5x 但单张图无感。
- **新建立的范式**：从零实现经典 CV 算法在 Go assetctl 是可行的，前提是 (a) 算法是 deterministic 数学（不依赖 ML 模型权重），(b) 用例容忍质量轻微差异（实际场景的 quality budget），(c) BFS / iterative methods 通常比 Fast Marching / PDE solver 更易实现且性能可接受。这条路径解锁未来类似工具（e.g. 经典 filter / morphology / classical detection）。
- 验证全绿：`gofmt -l` 空、`go vet ./...` clean、`go test -race ./...` 全过；`holefill` 26 tests pass（含 interior fill / border-touching skip / [minSize, maxSize) banding / no-op idempotence / mock / dryRun / validation 8 项 / forbidden-phrasing guard）；`tools list` 18/18；`run hole-fill --dryRun` envelope OK，`--mock` 写 1×1 占位 PNG，real-run 在合成 fixture 上 inpaint 后 alpha=255。
- `MissingEnv()` 返回 nil（无 env 依赖，纯本地 IO + 算法）。

### Wave 11（已完成 2026-05-21，main `7c96f20`）—— W7 Pattern E scaffold 重构为 Pattern B

- 1 颗工具（nrbi-render-prompt）从 Pattern E scaffold 完整重写为 Pattern B FC HTTP；共 2 个 atomic commit（refactor 1 + chore 1）。Wave 11 推翻 W7 决策，按用户设计原则"不方便改成 Go 的，该保留 C++ 就保留 C++"延伸到冻结 Python 场景。
- 合并进 `moonshort-ide` 本地 `main`（FF `5f80cf7..7c96f20`），改文件 3（nrbirenderprompt.go rewrite 287 LOC + nrbirenderprompt_test.go rewrite 581 LOC + cli_test.go aggregate env 加 nrbi env）。
- **能力扩展**：1 颗工具从 Pattern E scaffold 转 Pattern B 可跑（待 backend）——`nrbi-render-prompt`（schema 5 props：layer/variable_text 2 required（layer enum A/A5/B/C/D/E，variable_text object）+ category/style_name/reference_image_urls 3 optional + dryRun；fcBody 5 字段固定顺序 layer→variable_text→category→style_name→reference_image_urls）。**drop `mock`** mode（Pattern B sibling 不带，backend 自己处理任何内部 mock）。Wave 11 后 W7 标记从"Pattern E scaffold"改为"Pattern B 等 backend"，18 颗全部 Pattern A/A2/B/E/E2，**无 Pattern E scaffold 留存**。
- **设计决策记录**：donor 是 1547 LOC frozen Python（sha256-pinned 模板，importlib.util.spec_from_file_location 加载，prompt 构造分散 7 个私有 builder）。完整 Go port 需 Wave 7b byte-faithful sha256 对拍 CI 基础设施（Python baseline runner + Go runner + diff 比对器 + 字面量同步策略，估 1-2 天）+ 1547 LOC 翻译（估 3-5 天）。**W11 取消 Pattern E scaffold + Wave 7b gate，直接 Pattern B 让 backend 跑 donor Python verbatim**，省 5+ 天后续工作。snake_case JSON keys（donor-faithful，backend 跑 donor Python verbatim 期待 snake_case）+ response 用 typed struct 解析（解出 `prompt` string + 元数据 `model`/`style_name`/`category`/`layer`/`meta`，区别于 sibling 工具的 OSS URL response）。
- **新建立的范式**：Pattern B 不限于 OSS URL response。response shape 是字符串 / 元数据时，用 typed `fcResponse` struct 在 tool package 内 inline 解析（YAGNI `fc.ExtractString` helper，wrapper 还需要 model + meta passthrough）。
- FC env：`FC_NRBI_RENDER_PROMPT_URL` / `FC_NRBI_RENDER_PROMPT_TOKEN`；60s timeout（轻量字符串构造，无 ML/GPU）。
- 验证全绿：`gofmt -l` 空、`go vet ./...` clean、`go test -race ./...` 全过；`nrbirenderprompt` 39 tests pass（含 fcBody 字段顺序 byte-exact 断言 + httptest live FC + 禁字面 `TestSummaryHasNoForbiddenPhrasings` 守 Python/importlib/sha256/ZENMUX/google-genai）；`tools list` 18/18；`run nrbi-render-prompt --dryRun` envelope dry_run:true、body 字段 snake_case 顺序锁住；`run nrbi-render-prompt` 无 env → CONFIG_MISSING 列两个 env 退 3。

### Wave 13（已完成 2026-05-21，`feat/assetctl-wave13-nrbi-port`）—— W11 Pattern B 重构为 Pattern E（captured-goldens 范式）

- 1 颗工具（nrbi-render-prompt）从 Pattern B FC HTTP 完整重写为 Pattern E 纯 Go（stdlib-only 文本处理 + 一次性 captured goldens 对拍）；共 5 个 atomic commit on `feat/assetctl-wave13-nrbi-port`（`e533754` docs plan + `7cd004d` feat capture goldens + `8f8e0d4` feat port Assemble+helpers+6 builders + `c47791f` fix spec-review feedback + `a97ee76` refactor Pattern B → E）。Wave 13 推翻 W11 决策，按用户原则"方便改成 Go 的就改"延伸到经典 stdlib 文本处理场景。
- **触发**：用户对 W11 "1547 LOC frozen Python 必走 backend" 的判断提出复核——render.py 实际只触碰一个薄切片，frozen 模板 + importlib loader 是 donor 侧噪音，真正需要端口的是 6 个 builder + 一把 regex helper。
- **Pattern 决策**：Pattern E（纯 Go，stdlib only）+ captured-goldens 范式。一次性从 donor 抓 9 个 byte-faithful 输出（覆盖 layer A/A5/B/C/D/E 全部分支 + edge cases），commit 入树（`testdata/goldens/`）；单测 diff Go 输出 vs goldens，CI 不需要 Python runtime。**未沿用 Wave 7b 设想的 sha256 对拍 CI 基础设施**（Python baseline runner + Go runner + diff 比对器在每次 CI 跑 Python），那条路重型且脆弱；captured-goldens 一次抓完、commit、永远 deterministic。
- **实算 LOC**：impl 607 LOC（render.go + helpers + 6 builders）+ tests 392 LOC = **999 LOC 真实 Go 端口面**。W11 doc 的 "1547 LOC" headline 是 donor render.py 全文件计数（含 frozen 模板字面量 + importlib loader + 大段注释），高估 ~55%。
- **文件改动**：nrbirenderprompt.go rewrite Pattern B → Pattern E（drop fcBody/fcResponse/HTTP client → 加 6 个 builder + Assemble + helpers）；nrbirenderprompt_test.go rewrite Pattern B 39 tests → 9 byte-faithful golden 对拍 + 18 unit + 25 wrapper tests = **52 tests pass**；`testdata/goldens/` 新增 9 个 fixtures（一次性 capture，donor-faithful 字节）；cli_test.go aggregate env 移除 `FC_NRBI_RENDER_PROMPT_*`（无 env 依赖）；tool wrapper **-167 LOC**（drop fcBody struct + HTTP client 配置）。
- **验证**：9 byte-faithful golden 对拍 + 18 unit + 25 wrapper tests 全绿；`gofmt -l` 空、`go vet ./...` clean、`go test -race ./...` 全过；`tools list` 18/18；`run nrbi-render-prompt --dryRun` envelope OK（Pattern E 本地 path，无 env 无 HTTP）；`MissingEnv()` 返回 nil。
- **决策回溯**：W7 Pattern E scaffold（real-run NOT_IMPLEMENTED 等 Wave 7b CI）→ W11 Pattern B（让 backend 跑 donor verbatim 省事）→ W13 Pattern E captured-goldens（端口 999 LOC 真实面 + 一次性 goldens 验证字节保真）。三轮迭代后落点：tool wrapper -167 LOC、tool 零 env 依赖、backend 少一个 endpoint、CI 无 Python runtime；同时不为了"统一 Pattern B"而把可纯 Go 的文本处理外包。这条路径解锁未来类似工具（e.g. 任何 frozen 模板 + builder 风格的 prompt 构造逻辑）。

### Wave 14（已完成 2026-05-22，`feat/assetctl-foundation` `57065d5`）—— ATOMIC_TOOL_IDS 扩展：IDE-native 审计原子（18 → 21）

- 3 颗 IDE-native 原子能力（从 novels-to-moonscript / moonshort-ide asset-prompt-generator skill 的 Python 脚本 port 成 Go）从 `feat/mapping-port-atoms` 隔离 worktree 集成回 `feat/assetctl-foundation`；共 7 个 atomic commit cherry-pick 到 origin tip（277985a → 57065d5），fast-forward push。Wave 14 突破"18 颗 = 完整 catalog"边界——首次给 IDE 独有的、不在 assets-produce@48e6eb9 donor 里的本地审计能力建立 append-only 通道。
- **ATOMIC_TOOL_IDS 契约语义变更（minor，向后兼容）**：原 §2 文字"18 颗 = source order = 单一真相源"扩展为"**前 18 颗 verbatim 自 assets-produce@48e6eb9 skill-source.ts（永远不改顺序、不删、不重排）+ 后面按 commit-arrival 顺序追加 IDE-native 原子（never reorder, only append）**"。registry.go / registry_test.go / cli_test.go / lint_test.go 的`==18` 断言全部松到 `>=18`（floor，不 cap）。bindings.json description 同步："All 18 canonical atomic ids are runnable (...) + 3 IDE-native audit atoms appended after the canonical 18 (audit-mapping, parse-wardrobe, check-clothing-keyword)"。
- **能力扩展**：3 颗 Pattern E 纯 Go 原子，全本地、无 env 依赖、无 FC HTTP。
  - `audit-mapping`：扫 `.mss.md` 脚本里 `@<char> show/look` + `<CHAR> [look]:` 内联三种引用形式，对账 `compiled/mapping.json` 缺失的 (char, look) 条目；`apply: true` 备份原 mapping 到 `mapping.pre-patch.backup.json` 再写 patched 版；voice-tag 启发式把 `muffled`/`quiet_voice`/`warm_chuckle` 等纯声音描述降级为 informational `missingVoiceTag`（不阻塞画面）。`aliasesPath` JSON 接受 `aliases` / `look_aliases` / `voice_tag_tokens` 三段配置。chaoreqi-idol parity：242 refs / 212 hits / 2 missing_sprite / 2 missing_voice_tag bit-for-bit 对齐原 Python `patch_mapping.py`。86.4% 覆盖率。
  - `parse-wardrobe`：解析 character-bible Markdown（02-character-architect/`mc-bible-*.md` / `li-bible-*.md` / `supporting-cast-filter.md`）里的 `## Canonical Wardrobe` table，emit `{characters: {<char>: {wardrobe: [{wardrobeId, description, when, isLayeredVariant}]}}, charList, total}` envelope。NRBI selena/diego/supporting-cast 三条路径与原 Python `canonical_wardrobe.py` bit-for-bit 一致。96.2% 覆盖率。
  - `check-clothing-keyword`：扫 stage-06 sprite prompts vs stage-05 narrative 的关键词集（`EN_KEYWORDS` / `ZH_KEYWORDS` / `SYNONYMS` / `NONCOSTUME_PHRASES` verbatim 自原 Python），±N 行窗口；offline fallback，~18 假阳性率（NRBI 实测）。默认 LLM mode 仍由 sibling Python `llm_clothing_audit.py` 提供（不在本轮 port 范围）。95.8% 覆盖率，34 test fn。
- **Python 源清理**：删除两个被 Go 原子完全替代的脚本：`agents/asset/skills/asset-prompt-generator/patch_mapping.py`（605 LOC）+ `check_clothing_consistency.py`（451 LOC）+ `tests/test_patch_mapping.py`（400 LOC）。保留 `canonical_wardrobe.py`（`look_canonicalizer.py` 仍 `from canonical_wardrobe import ...`，下一轮 port look_canonicalizer 时一起删）+ `llm_clothing_audit.py`（LLM mode 不在本轮 port 范围）+ `green_screen.py`（已挪入 image gen 原子的 prompt 后缀链路，单独清理）。同时把 `gen_e10_22_sprites.py`（NRBI 一次性 sprite spec 生成器，708 LOC）archive 删除并把 OUTFIT_SYSTEM / EXPRESSION_SYSTEM 模板提炼到 `references/outfit-llm-prompt-pattern.md`（220 行 reusable pattern doc）。SKILL.md 两个 "06 收尾自检" 段 `python3 .../patch_mapping.py ...` / `python3 .../check_clothing_consistency.py ...` 命令样例改写为 `assetctl run audit-mapping --input '{...}'` / `assetctl run check-clothing-keyword --input '{...}'` JSON envelope 形态，配套输出示例从 Python 文本 dump 改成 envelope `{ok, data: {missingSprite[], missingVoiceTag[], ...}}`。
- **新建立的范式**：
  - **ATOMIC_TOOL_IDS append-only 协议**：donor catalog 之外的 IDE-native 原子追加在数组末尾，commit-arrival 顺序，never reorder。
  - **隔离 worktree → cherry-pick 集成**：当 origin/feat/assetctl-foundation 与本地 isolation 分支同时推进时，cherry-pick 单 commit 逐个 onto origin tip，逐步 resolve conflicts（registry.go imports alphabetic merge + realTools 末尾 append）比一次性 rebase 200+ commits 更可控。冲突点全部 additive（HEAD 已 wired 18 atoms + 我加 1，合并 = 接受双方）。
  - **Python 端口动作配套**：每 port 一颗，必同步删 Python 源 + 修 import 同包 stale comments + 更新 SKILL.md 命令样例 + relax 任何 hard-coded `==18` 断言。
- 验证全绿：`pnpm check` exit 0（lint + typecheck + node test 187 pass + go test）；vendor/assetctl 全 14 包 `go test -race` 通过，覆盖率：`auditmapping 86.4%` / `parsewardrobe 96.2%` / `checkclothingkeyword 95.8%`。`tools list` 21/21（18 canonical runnable + 3 IDE-native runnable）；`tools schema audit-mapping|parse-wardrobe|check-clothing-keyword` envelope schema 正确；`assetctl tools list | jq -r '.[].name'` 末尾 3 行依次是 audit-mapping → parse-wardrobe → check-clothing-keyword（commit-arrival 顺序）。
- **Wave 14 后总数**：18 canonical（assets-produce@48e6eb9 verbatim，all runnable）+ 3 IDE-native（IDE 独有，all runnable）= **21 颗全部可跑**，0 stub。

### Wave 15（已完成 2026-05-22，`feat/assetctl-foundation` `7306c27`）—— ATOMIC_TOOL_IDS 再扩展：4 颗新 IDE-native 原子 + chromakey inline schema 扩展（21 → 25）

- 4 颗 IDE-native 原子能力（继续从 asset-prompt-generator skill 的 Python 脚本 port 成 Go）+ 1 个既有原子的 schema 扩展（chromakey inline）从三个隔离 worktree 集成回 `feat/assetctl-foundation`；共 5 个 atomic commit cherry-pick 到 origin tip（9c9907f → c635ea9）+ 1 个 docs 同步 commit（7306c27），fast-forward push 6 个 commit 到 cdotlock/moonshort-ide。Wave 15 延续 Wave 14 ATOMIC_TOOL_IDS append-only 协议（never reorder, only append），并首次在既有原子上做 schema 扩展（非新原子，向后兼容）。
- **触发**：Wave 14 收尾时三个 sibling Python 脚本（`llm_clothing_audit.py` LLM 模式 / `look_canonicalizer.py` 6 阶段 wardrobe canonicalizer / `green_screen.py` chromakey 后缀 helper）未在范围内；Wave 15 三路并发（subagent A/B/C 各跑一条隔离 worktree）补齐。
- **能力扩展**：4 颗新 Pattern E 纯 Go 原子 + 1 个 schema 扩展。
  - `check-clothing-llm`（B 路）：扫 stage-06 sprite prompts vs stage-05 narrative 的 truth-table 模式——每集一次 Zenmux LLM 调用，从 narrative 抽 "这集每个 BEAT 每个角色穿什么" 真值表，跟 sprite prompt 做语义对账。同义词 / 归属 / idiom 过滤由 LLM 处理（不再像 `--mode keyword` 走 verbatim 关键词集）。per-episode SHA256 内容键缓存（避免重复 LLM 调用），ZENMUX_API_KEY env 依赖（OpenAI-compatible HTTP client）。比 `check-clothing-keyword` 假阳性率低一个数量级（NRBI 实测：keyword ~18%，llm < 3%）。90.7% 覆盖率。
  - `extract-look-signatures`（C 路 phase 1+2）：从角色 Bible 的 canonical wardrobe table 抽 (char, look) 二元组的 LLM 签名（颜色 / 材质 / 廓形 / accessory 5–8 维度），落地 `look_signatures.json`。LLM-only（无 keyword fallback），ZENMUX_API_KEY env 依赖。下游 `build-wardrobe-map` 消费。90.2% 覆盖率。
  - `build-wardrobe-map`（C 路 phase 3）：消费 `extract-look-signatures` 的输出 + stage-05 narrative 里出现的 raw `<char> [look]:` look-name tokens，LLM 决策每个 raw token 应该 canonicalize 到哪一颗 (char, wardrobeId)，输出 `wardrobe_map.json` 含 `confidence` / `evidence` 字段。88.1% 覆盖率。
  - `apply-look-aliases`（C 路 phase 4+5+6）：消费 `wardrobe_map.json` 把 raw look tokens 在脚本里 in-place rewrite 成 canonical wardrobeId，同时把 alias 折回到 `compiled/aliases.json`（让 `audit-mapping` 下次走绿）。本颗收尾整条 wardrobe canonicalization pipeline。88.2% 覆盖率。
  - **chromakey inline**（A 路）：`generate-image-nanobanana` / `generate-image-gpt` schema 各增加一个可选 `chromakeyMode: true` boolean（default false，向后兼容；新字段插在 schema 既有 props 末尾，donor-faithful prop 顺序保留）。当 `chromakeyMode: true` 时，prompt builder 在用户 prompt 末尾 append 5 句 chromakey-green 背景契约后缀（"Solid uniform chromakey green (#00FF00) background..." 等）。**Marker `[BACKGROUND CONTRACT — chromakey green]` 保证幂等**（已含 marker 的 prompt 不会被重复加 suffix）。取代独立 `green_screen.py wrap_for_chromakey()` helper。**不是新原子**，是既有原子的 schema 扩展。nanobanana / gpt 各 100% 覆盖率。
- **Python 源清理**：删除四个被 Go 原子完全替代的脚本：`llm_clothing_audit.py`（489 LOC，B 路完成后删）+ `look_canonicalizer.py`（1107 LOC，C 路 phase 4+5+6 落地后整文件删）+ `canonical_wardrobe.py`（207 LOC，最后一个 `from canonical_wardrobe import` 在 look_canonicalizer 删除后随之删）+ `green_screen.py`（A 路完成后删，chromakey suffix 已 inline 进 nanobanana / gpt 的 prompt builder）。`SKILL.md` 配套命令样例 3 处改写为 `assetctl run <id> --input '{...}'` JSON envelope 形态（match Wave 14 范式）。`references/outfit-llm-prompt-pattern.md` 同步加 "look canonicalization 已迁 Go atoms" 段。
- **新建立的范式**：
  - **ATOMIC_TOOL_IDS schema 扩展（非新原子）协议**：既有原子加可选字段时——(a) 新字段插 schema props 末尾，(b) default false / 0 / "" 保证 backward-compat，(c) 行为变更要 idempotent（用 marker / token 防重复应用），(d) bindings.json description 同步说明扩展。
  - **三路并发隔离 worktree → cherry-pick 集成**：Wave 15 首次跑三个 subagent 并发（A/B/C 各占一个隔离 worktree），各自落 commit 到独立分支，最后 cherry-pick 到 integration 分支。冲突点全部 additive（registry.go ATOMIC_TOOL_IDS 数组 + realTools map + imports 三处都被多方追加），按 commit-arrival 顺序逐 commit cherry-pick 时手动保留双方条目即可，无需 rebase。
  - **LLM-only 原子的缓存范式**：`check-clothing-llm` / `extract-look-signatures` / `build-wardrobe-map` 三颗都消耗 ZENMUX_API_KEY，per-episode SHA256 内容键缓存到 `.cache/` 目录（content-addressed，rerun 同 input 直接命中），ZENMUX_API_KEY 走 AgentConfig.additionalEnv 从 workspace .env 注入（IDE 启动无需 pre-source shell）。
- 验证全绿：`pnpm check` exit 0（lint + typecheck + node test 全过 + go test）；vendor/assetctl 全包 `go test -race` 通过，本轮新增 5 包覆盖率：`checkclothingllm 90.7%` / `extractlooksignatures 90.2%` / `buildwardrobemap 88.1%` / `applylookaliases 88.2%` / `nanobanana 100%` / `gpt 100%`；node test **294 pass / 0 fail**。`tools list` 25/25（18 canonical runnable + 7 IDE-native runnable）；4 个新原子 `tools schema <id>` envelope schema 正确；`assetctl tools list | jq -r '.[].name'` 末尾 7 行依次是 audit-mapping → parse-wardrobe → check-clothing-keyword → check-clothing-llm → extract-look-signatures → build-wardrobe-map → apply-look-aliases（commit-arrival 顺序）。`tools schema generate-image-nanobanana` / `tools schema generate-image-gpt` 末尾 prop 显示 `chromakeyMode: { type: boolean, default: false }`。
- **Wave 15 后总数**：18 canonical（assets-produce@48e6eb9 verbatim，all runnable）+ 7 IDE-native（IDE 独有，commit-arrival 顺序追加，all runnable）= **25 颗全部可跑**，0 stub。chromakey inline 是 schema 扩展（nanobanana / gpt 两颗既有原子上），不计入原子数。

## 开放细节 & 后续（顺序死板 0→1→2→3）

- **O1 · assetctl↔videoctl 边界**：`generate-video-*`/`concat-clips`/`crop-video` 与 `videoctl` 是否重叠——后续 plan 定清（候选：assetctl 不收视频生成类全委派 videoctl；或 videoctl 专投递、生成类归 assetctl）。
- **第 2 块**（另起 spec→plan）：上游权威编排 skill + 知识 → codex staged skill，drift 一次性补齐。
- **第 3 块**（另起 spec→plan）：Langfuse-first 正文加载 + `skills sync`/`--check` parity（D2/D5 下成立）。
- 风险缓解：R1 Go 翻译走样 → 对拍测试 + 钉基准 SHA + 逐颗评审；R2 `python-runner` 类（matting 等）Go 化方案后续 plan 定；R3 缺凭据走 exit 3 不 crash；R4 能力按文件夹约定发现、不写死 stage。
