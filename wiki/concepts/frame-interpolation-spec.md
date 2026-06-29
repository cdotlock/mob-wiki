---
title: 角色表情插帧实施方案
tags: [rife, interpolation, animation, cocos, client, spec]
created: 2026-06-29
updated: 2026-06-29
---

角色表情切换（`char_look`）目前是瞬间换图，没有过渡。本方案用神经网络插帧（RIFE/IFRNet）生成中间帧，让表情切换丝滑。分两阶段：Phase 1 在 Web 端验证效果，Phase 2 推广到 Android/iOS。

相关代码：[[entities/lunaverse-client]]。视觉小说展示形态：[[concepts/unfolded-visual-novel]]。

## 核心设计决策

### 为什么是端上推理，不是服务端预计算

- 我们的服务器没有 GPU，CPU 推理一对表情 1-2.5 秒，加上管线/CDN/缓存的工程复杂度不值得
- 角色图在移动端很小（视口 393px，角色 ~300-500px 宽），端上推理成本低
- 小分辨率下 RIFE/IFRNet 推理预估 3-10ms/帧，5 帧 = 15-50ms，远在 200ms 过渡预算内

### 什么时候触发插帧（关键修正）

**先纠正一个错误前提**：LS 现在**只有一个** `@<char> <pose>` 指令（编译为 `char_show`），**没有** `char_look`/`char_show` 之分。AST 注释原话："There is no separate hide / look / move node"。所以"LS 层面已经语义化为同角色换表情"是**错的**——LS 不区分换表情还是换衣服，两者都是 `char_show`。客户端的 `inferCharacterMotionKind()` 仅靠"同角色 + 不同 URL"判断，**会把换装也当成换表情**，直接插帧会产生鬼影。这是必须修的。

**真正的判断依据：立绘命名 token**。生产立绘（NRBI/recanon 管线）遵循规范化 token：

```
{char}__{outfit}__{posture}-{position}-{camera}-{expression}
```

backend 已有解析器 `lunaverse-backend/scripts/_seed-helpers/avatar-pose.ts`：outfit = 第 2 个 `__` 段，expression = 最后一个 `-` 段。例：
- `sera__black_turtleneck_charcoal_trousers__upright-by_side-to_camera-neutral`
- `camila__casual_default__lean_forward-by_side-to_camera-smile`

**插帧触发条件（必须三者同时满足）**：
1. 同角色（token 第 1 段相同，且 `character` 字段相同）
2. **同 outfit**（token 第 2 段相同）— 这是之前漏掉的关键
3. 只有 posture/position/camera/expression 变化（第 3 段不同）

**不触发**：
- **换 outfit / 换装**（第 2 段不同）— 视觉差异太大，插帧鬼影。这是最重要的排除项
- 不同角色之间切换
- 角色出场（无前一帧可插）、退场、位移

### 决策（已定）：视觉相似度门控，不依赖命名

**为什么放弃命名解析**：实测当前 4 部小说编译产物，客户端收到的 `char_show.look`（作者短名如
`coat_zipped_breath_visible`）和 `url`（拍平的 `selena_casual_upright-...`）**都不含 `__`**。规范
`__` token 只存在于 recanon 中间表示/mapping key，**没下发到客户端**。而 URL 把 `__` 拍平成 `_`
后无法可靠切分——outfit 多词（`formal_evening`/`casual_default`/`black_tee_jeans`）紧接 posture 也
是 `_` 连接（`casual_default_seated`、`formal_evening_walking`），没有 per-novel 词表分不清边界。
让整个功能依赖"把 token 推进 `look` 字段"的跨仓管线改动，太脆。

**换个角度**：真正要判断的不是"同 outfit"，而是**"这两张图够不够像，插帧会不会鬼影"**。
"同 outfit"只是它的代理。直接量这件事更稳——而且**插帧本来就要解码两张图**，顺手算个相似度几乎免费。

**门控：裁剪区域颜色直方图比较**（位姿无关、outfit 敏感）：

```ts
// assets/utils/LookSimilarity.ts
// a、b 是插帧已经解码好的两张 bitmap。判断"够像 → 可插帧"。
function interpolationSafe(a: ImageBitmap, b: ImageBitmap): boolean {
  const S = 48;                                   // 缩略尺寸
  const ha = clothingHist(a, S), hb = clothingHist(b, S);
  return histIntersection(ha, hb) >= THRESHOLD;   // 经验阈值，Phase 1 标定
}

// 取下 2/3（服装区），对 alpha>0 像素做粗量化 RGB 直方图（如每通道 4 bins = 64 bins）
function clothingHist(img, S) { /* 离屏 canvas 缩放 → getImageData → 下 2/3 → 量化累计 */ }
function histIntersection(p, q) { /* Σ min(p_i,q_i) / Σ p_i，∈[0,1] */ }
```

- **位姿无关**：直方图忽略像素位置，同 outfit 大幅度换姿势（抬手/侧身）颜色分布不变 → 仍判定可插帧。
- **outfit 敏感**：换衣服 → 服装区颜色分布变 → 判定不安全 → 退回瞬切。
- **表情通过**：脸是小区域，不主导直方图 → 换表情仍可插帧（正是我们要的）。
- **命名无关**：新老小说、任何管线都适用，**零管线依赖、不加字段、纯客户端**。
- **安全退化**：误判只会"少插一次帧"（退回瞬切），不会鬼影。

**`character` 字段先做快速短路**：`kind === 'look'` 已隐含同角色（同槽同角色不同 url）；若需跨槽判断，
先比 `character` 字段（干净 slug），不同角色直接跳过，连解码都省。

> 阈值 `THRESHOLD` 在 Phase 1 用同 outfit / 换 outfit 样本对标定（NRBI 小说能从 mapping 文件名肉眼
> 分出 outfit，拿来当 ground truth 调阈值）。Phase 1 先用全局缩略 MAE 也行，够看效果；生产用直方图更稳。

> 可选未来 fast-path：若某天规范 `__` token 真的下发到 `look`，可加一层"同 char 同 outfit"名字快判，
> 命中就免去直方图。但**不作为依赖**，视觉门控是主路径。

### 模型选择

**Phase 1（Web 验证）**：RIFE v4 ONNX — HuggingFace 上有现成导出（`TensorStack/RIFE` ~21.5MB 或 `yuvraj108c/rife-onnx`），通过 ONNX Runtime Web WASM 后端做 CPU 推理。

**Phase 2（原生端）**：IFRNet-Small ncnn — 参数量是 RIFE 一半，PSNR 更高，`nihui/ifrnet-ncnn-vulkan` 已有移植。或继续用 RIFE v4 ncnn（~10MB）。

## Phase 1：Web 端验证

目标：在浏览器里跑通同角色同 outfit 的表情/姿态插帧，验证视觉效果。CPU 推理，不要求实时性能。

### 1.1 新增模块：`FrameInterpolator`

位置：`assets/utils/FrameInterpolator.ts`

职责：
- 加载 ONNX 模型（懒加载，首次需要插帧时触发）
- 接收两张图片（旧表情、新表情），输出 N 张中间帧
- 管理模型生命周期和内存

```
接口设计（伪代码）：

class FrameInterpolator {
  private session: ort.InferenceSession | null

  async init(): Promise<void>
    // 懒加载 onnxruntime-web + RIFE ONNX 模型
    // WASM 后端（CPU），不依赖 WebGPU

  async interpolate(
    imageA: HTMLImageElement | ImageBitmap,
    imageB: HTMLImageElement | ImageBitmap,
    numFrames: number  // 3 或 5
  ): Promise<ImageBitmap[]>
    // 1. 两张图 resize 到模型输入尺寸（32 的倍数，如 384×512）
    // 2. 归一化到 [0,1]，拼接为 (1, 6, H, W) tensor
    // 3. 递归插帧：先插 t=0.5，再插 t=0.25 和 t=0.75...
    // 4. 输出解码回 ImageBitmap 数组

  dispose(): void
    // 释放 ONNX session 和 GPU/CPU 内存
}
```

**依赖**：`onnxruntime-web`（npm 包，~2MB gzip）。模型文件 ~21.5MB，从 CDN 或 assets 加载。

**递归插帧策略**：RIFE 单次调用只生成 1 张中间帧（t=0.5）。要生成 N 帧需递归：
- 3 帧：A→M→B（1 次推理）然后 A→M1→M→M2→B（再 2 次推理），取 M1, M, M2
- 5 帧：4 次推理（二叉递归）
- Phase 1 先固定 3 帧（3 次推理），后续可调

### 1.2 视觉门控：新增 `LookSimilarity.ts`

位置：`assets/utils/LookSimilarity.ts`。职责：对两张已解码 bitmap 做服装区直方图比较，判断插帧是否安全。是插帧的**唯一前置闸门**。完整实现见上文「决策（已定）」代码块（`interpolationSafe` + `clothingHist` + `histIntersection`，约 25 行）。命名无关、零管线依赖。

### 1.3 修改 `StoryWnd.playCharacterMotion()`

位置：`assets/bundles/play/story/StoryWnd.ts:3391`

当前代码：
```typescript
if (kind === 'look') {
    this.setCharacterSlotOpacity(slot, targetAlpha);
    return;
}
```

改为（注意门控在两图解码后才判，所以决策逻辑挪进 `playInterpolatedLookTransition`）：
```
if (kind === 'look') {
    const prevUrl = this.renderedCharacterSlots[slot]?.url ?? null;
    const nextUrl = 当前 data.url;
    if (prevUrl && this.frameInterpolator) {
        // 内部：解码两图 → interpolationSafe(a,b)?
        //   安全 → 跑 RIFE 播帧序列
        //   不安全（换装/差异大）或无前图 → 退回瞬切 setCharacterSlotOpacity
        this.playInterpolatedLookTransition(slot, prevUrl, nextUrl, targetAlpha);
        return;
    }
    this.setCharacterSlotOpacity(slot, targetAlpha);
    return;
}
```

> `kind === 'look'` 已隐含同角色（同槽不同 url）。门控只需视觉相似度——两图都得先解码，正好插帧也要解码，合一步。

### 1.4 新增方法：`playInterpolatedLookTransition()`

```
async playInterpolatedLookTransition(
  slot: SlotName,
  oldUrl: string,
  newUrl: string,
  targetAlpha: number
): void
  // 1. 获取旧图和新图的 ImageBitmap（旧图从缓存取，新图等 setSpriteUrl 加载完成）
  // 2. 视觉门控：interpolationSafe(oldImg, newImg)?
  //      false（换装/差异大）→ 直接 setCharacterSlotOpacity 瞬切，return
  // 3. 调 frameInterpolator.interpolate(oldImg, newImg, 3)
  // 4. 得到 3 张中间帧 ImageBitmap
  // 5. 播放帧动画：oldImg → frame1 → frame2 → frame3 → newImg
  //    每帧 50ms，总计 200ms
  // 6. 帧动画结束后，sprite 显示 newUrl（正常状态）
```

**帧动画播放**：用 Cocos 的 `schedule` 或 `tween` + `call` 链，每 50ms 将中间帧的 ImageBitmap 写入 sprite 的 Texture2D。已有的 `VideoTexturePlayer` 里有 canvas → Texture2D 的管线可参考。

### 1.4 模型加载时机

- **不在启动时加载** — 21.5MB 模型会拖慢首屏
- **第一次需要插帧时懒加载** — 首次有约 1-3 秒加载延迟，此次 fallback 到瞬间换图
- **后续即时生效** — 模型已在内存
- 可选：在进入剧情阅读阶段时预加载（用户此时在看内容，有空闲时间）

### 1.5 输入预处理（接 1.4）

角色图特殊性：
- 透明背景 PNG（RGBA），RIFE 期望 RGB
- 需要统一处理 alpha：合成到黑色或白色背景后送入模型，输出后重新提取 alpha
- 简单方案：alpha 通道单独做线性插值（`alphaOut = lerp(alphaA, alphaB, t)`），RGB 走 RIFE
- 两张图可能尺寸不同：resize 到统一尺寸（取较大者，对齐到 32 的倍数）

### 1.6 测试方式

**独立 demo 页面优先**（`test/interpolation-demo.html`）：从 `dont-pretend-with-me` 的 mapping.json 取样本对——靠文件名肉眼分出 outfit（`camila_casual_default_*` vs `camila_evening_gown_*`），凑「同 outfit 不同 expression」正样本 + 「换 outfit」负样本。对每对：① 跑插帧并排对比瞬切 ② 打印 `interpolationSafe` 的直方图相似度。用正负样本标定 `THRESHOLD`。这是 Phase 1 主路径。

集成验证（次要）：
1. `npm run dev` 启动本地 Web 服务
2. 进入 NRBI 小说，推进到同角色连续换表情的对话
3. 观察门控命中时是否丝滑过渡，换装时是否正确退回瞬切
4. 控制台打印：直方图相似度、是否命中、推理耗时、帧数

### 1.7 Phase 1 产出物

- `assets/utils/FrameInterpolator.ts` — ONNX 推理封装
- `assets/utils/LookSimilarity.ts` — 视觉门控（服装区直方图）
- `StoryWnd.ts` 中 `kind === 'look'` 分支改动（接门控 + 播帧）
- RIFE ONNX 模型文件（CDN 托管或本地 assets）
- 独立 demo 页面（`test/interpolation-demo.html`）
- 效果对比截图/录屏 + 门控正确性记录（同 outfit 插帧 / 换装瞬切）

## Phase 2：推广到 Android 和 iOS

Phase 1 效果验证通过后执行。

### 2.1 模型切换

Web 端验证效果后，原生端可以选更优模型：
- **IFRNet-Small ncnn**：参数量约 5M，质量比 RIFE 更好，`ifrnet-ncnn-vulkan` 已有现成移植
- **RIFE v4 ncnn**：~10MB，`rife-ncnn-vulkan` 成熟稳定
- 两者都有 ncnn 格式模型，可直接用

### 2.2 Android 集成

**推理后端**：ncnn + Vulkan GPU

**集成方式**：
1. 将 `rife-ncnn-vulkan`（或 `ifrnet-ncnn-vulkan`）的核心代码（`rife.cpp`, `warp.cpp`, shader 文件）编译为静态库
2. 通过 JNI bridge 暴露 `interpolate(Bitmap frameA, Bitmap frameB, float timestep): Bitmap` 接口
3. Cocos 侧通过 `jsb` (JavaScript Binding) 调用 native 方法

**文件位置**：
- `native/engine/common/Classes/NativeFrameInterpolationBridge.cpp` — C++ 实现
- `native/engine/common/Classes/NativeFrameInterpolationBridge.h` — 头文件
- `native/engine/android/` — Android JNI 胶水
- `assets/utils/FrameInterpolator.ts` — 统一接口，Web 用 ONNX，native 用 JSB

**模型文件**：打包进 APK assets（~10MB），或首次使用时从 CDN 下载到本地缓存。

**Vulkan 兼容性**：Android 7.0+（API 24）支持 Vulkan。低端设备降级到 ncnn CPU（ARM NEON 优化）。

### 2.3 iOS 集成

**推理后端**：ncnn + Metal（通过 MoltenVK 或 ncnn 原生 Metal 后端）

**集成方式**：
1. 同样用 ncnn 静态库，编译 target 为 arm64 iOS
2. 通过 Objective-C++ bridge 暴露接口
3. 文件：`native/engine/common/Classes/NativeFrameInterpolationBridgeIOS.mm`

**未来可选**：iOS 26 引入了 `VTFrameProcessor`（系统级插帧 API），如果目标版本提升到 iOS 26 可以直接用系统能力，不需要自带模型。

### 2.4 统一接口设计

`FrameInterpolator.ts` 提供统一接口，内部按平台分发：

```
平台检测：
  Web    → ONNX Runtime Web (WASM/WebGPU)
  Native → JSB 调用 ncnn (Vulkan/Metal/CPU)

调用方式统一：
  interpolator.interpolate(imgA, imgB, numFrames) → Promise<ImageBitmap[] | Texture2D[]>
```

### 2.5 性能预算

| 平台 | 推理后端 | 预估单帧耗时（~400px） | 3 帧总耗时 |
|------|---------|----------------------|-----------|
| Web（桌面 CPU） | ONNX WASM | 100-300ms | 300-900ms |
| Web（桌面 WebGPU） | ONNX WebGPU | 20-50ms | 60-150ms |
| Android（旗舰 Vulkan） | ncnn Vulkan | 3-10ms | 9-30ms |
| Android（中端 CPU） | ncnn NEON | 30-80ms | 90-240ms |
| iOS（A15+ Metal） | ncnn Metal | 2-8ms | 6-24ms |

Phase 1 的 Web CPU 推理会比较慢（可能 300-900ms），但目的是验证**视觉效果**，不是验证性能。性能问题在 Phase 2 原生端自然解决。

## 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| **误把换装当换表情去插帧** | 鬼影（最严重） | 视觉门控 `interpolationSafe`：服装区直方图不够像就退回瞬切 |
| 阈值标偏（太松→鬼影 / 太紧→少插帧） | 效果/覆盖 | Phase 1 用正负样本对标定；偏紧（宁可少插也不鬼影） |
| 换 outfit 但配色相近（灰休闲↔灰正装） | 偶发误判可插帧 | 同角色相近配色插帧通常仍可接受；必要时叠加边缘/结构特征 |
| 透明背景 PNG 插帧出现边缘伪影 | 效果差 | alpha 通道单独线性插值，RGB 合成到纯色背景后推理 |
| ONNX Runtime Web 包体大 | 首屏慢 | 懒加载，不影响核心游戏功能 |
| 低端 Android 无 Vulkan | 无法推理 | 降级到 ncnn CPU (ARM NEON) 或 fallback 瞬间换图 |
| 模型输入要求 32 倍数 | 边缘裁切 | pad 到最近 32 倍数，输出后 crop 回原尺寸 |

## 不做的事

- 不做服务端预计算（成本和工程复杂度不划算）
- 不做 dissolve 过渡（直接上神经网络插帧）
- **不依赖立绘命名解析**（规范 token 没下发到客户端，URL 拍平后不可靠）
- 不加 step 字段、不改 LS / backend（纯客户端视觉门控）
- 不对换角色 / 出场 / 退场 / 位移做插帧
- Phase 1 不优化性能（只验证效果）

## 已定决策

- ✅ **视觉相似度门控**（服装区直方图），不依赖命名、零管线依赖、纯客户端、不加字段
- ✅ 直接量"两图够不够像、插帧会不会鬼影"，比解析 outfit 名更稳；新老小说通吃
- ✅ 一套门控统一判断；不安全就退回瞬切，安全退化（最多少插一次帧，不鬼影）
- ✅ 阈值 Phase 1 用 NRBI 样本对标定

> 备注：之前考虑的"解析规范 `__` token"方案作废——实测 token 没下发到客户端（`look` 是作者短名、`url` 拍平了 `__`），多词 outfit/posture 无法可靠切分。视觉门控绕开整个命名问题。
