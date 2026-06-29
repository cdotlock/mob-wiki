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

### 决策（已定）：纯客户端解析规范 token，一套规则统一判断

- ✅ 纯客户端解析，**不加任何 step 字段**，不改 backend/编译器
- ✅ 只认规范 token；不规范的老剧本**不考虑**（解析不出 = 不插帧，保持现状瞬切）
- ✅ 一套简单规则统一判断，不做视觉相似度兜底、不做表情距离门控（保持简单）

**规则依据规范 token**（唯一可靠、可无歧义切分的形式）：

```
{char}__{outfit}__{posture}-{position}-{camera}-{expression}
```

`split('__')` → `[char, outfit, descriptor]`，三段制 = 规范；段数 ≠ 3 即判为不规范，不插帧。

```ts
// assets/utils/LookToken.ts
interface LookToken { char: string; outfit: string; descriptor: string; expr: string }

function parseLookToken(s: string): LookToken | null {
  const parts = s.split('__');
  if (parts.length !== 3) return null;            // 非规范 → null
  const [char, outfit, descriptor] = parts;
  if (!char || !outfit || !descriptor) return null;
  const expr = descriptor.slice(descriptor.lastIndexOf('-') + 1);
  return { char, outfit, descriptor, expr };
}

// 唯一的判断入口
function shouldInterpolate(prevToken: string, nextToken: string): boolean {
  const a = parseLookToken(prevToken), b = parseLookToken(nextToken);
  if (!a || !b) return false;                     // 任一不规范 → 不插帧
  return a.char === b.char                        // 同角色
      && a.outfit === b.outfit                    // 同 outfit（关键）
      && a.descriptor !== b.descriptor;           // 确有姿态/表情变化
}
```

**为什么不解析 URL 文件名**：URL 把 `__` 拍平成 `_`，多词 posture 会产生歧义无法可靠切分。
例 `camila_formal_social_lean_forward-...`：outfit 是 `formal_social` 还是 `formal_social_lean`?
posture 是 `lean_forward` 还是 `forward`? 单下划线分不清。`__` 三段制无此问题。

> **实现依赖（实现前确认）**：`shouldInterpolate` 解析的 token 必须是带 `__` 的规范形式。
> 实测当前 4 部小说编译产物里，`char_show.look` 和 `url` **都不含 `__`**（look 是作者短名如
> `coat_zipped_breath_visible`，url 是拍平的 `selena_casual_...`）。规范 `__` token 目前只存在于
> recanon 中间表示/mapping key。**需确认 recanon 后/生产管线把规范 token 写进客户端可见的字段
> （建议复用 `look`，非新增字段）**。这正是"后面都是规范的"要落到 `look` 字段上的含义。
> 若确认 `look` 会是规范 token，则上面规则零改动直接生效。

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

### 1.2 outfit 门控：新增 `LookToken.ts`

位置：`assets/utils/LookToken.ts`。职责：解析规范 token，判断两个立绘是否"同角色同 outfit"。是插帧的**唯一前置闸门**。完整实现见上文「决策（已定）」的代码块（`parseLookToken` + `shouldInterpolate`，约 15 行）。

### 1.3 修改 `StoryWnd.playCharacterMotion()`

位置：`assets/bundles/play/story/StoryWnd.ts:3391`

当前代码：
```typescript
if (kind === 'look') {
    this.setCharacterSlotOpacity(slot, targetAlpha);
    return;
}
```

改为：
```
if (kind === 'look') {
    const prev = this.renderedCharacterSlots[slot];   // 含 look + url
    const next = 当前 data;                            // 含 look + url
    // outfit 门控：只有同角色同 outfit、仅表情/姿态变化时才插帧
    if (this.frameInterpolator && shouldInterpolate(prev, next)) {
        this.playInterpolatedLookTransition(slot, prev.url, next.url, targetAlpha);
        return;
    }
    // 其他情况（换装 / 老小说无 token / 无插帧器）→ 保持原有瞬切
    this.setCharacterSlotOpacity(slot, targetAlpha);
    return;
}
```

> 注意：`char_show` step 当前下发的 `look` 是作者短名，可能解析不出 token。Phase 1 用方案 B（解析不出就不插帧）。若走方案 A，则 backend 在 step 上补 `outfit`/`expression` 字段，`shouldInterpolate` 直接读字段，不再解析。

### 1.3 新增方法：`playInterpolatedLookTransition()`

```
async playInterpolatedLookTransition(
  slot: SlotName,
  oldUrl: string,
  newUrl: string,
  targetAlpha: number
): void
  // 1. 获取旧图和新图的 ImageBitmap（旧图从缓存取，新图等 setSpriteUrl 加载完成）
  // 2. 调 frameInterpolator.interpolate(oldImg, newImg, 3)
  // 3. 得到 3 张中间帧 ImageBitmap
  // 4. 播放帧动画：oldImg → frame1 → frame2 → frame3 → newImg
  //    每帧 50ms，总计 200ms
  // 5. 帧动画结束后，sprite 显示 newUrl（正常状态）
```

**帧动画播放**：用 Cocos 的 `schedule` 或 `tween` + `call` 链，每 50ms 将中间帧的 ImageBitmap 写入 sprite 的 Texture2D。已有的 `VideoTexturePlayer` 里有 canvas → Texture2D 的管线可参考。

### 1.4 模型加载时机

- **不在启动时加载** — 21.5MB 模型会拖慢首屏
- **第一次需要插帧时懒加载** — 首次有约 1-3 秒加载延迟，此次 fallback 到瞬间换图
- **后续即时生效** — 模型已在内存
- 可选：在进入剧情阅读阶段时预加载（用户此时在看内容，有空闲时间）

### 1.5 输入预处理

角色图特殊性：
- 透明背景 PNG（RGBA），RIFE 期望 RGB
- 需要统一处理 alpha：合成到黑色或白色背景后送入模型，输出后重新提取 alpha
- 简单方案：alpha 通道单独做线性插值（`alphaOut = lerp(alphaA, alphaB, t)`），RGB 走 RIFE
- 两张图可能尺寸不同：resize 到统一尺寸（取较大者，对齐到 32 的倍数）

### 1.6 测试方式

**独立 demo 页面优先**（`test/interpolation-demo.html`）：手动选两张同角色同 outfit 立绘（从 `dont-pretend-with-me` 这类 NRBI 小说的 mapping.json 取同 outfit、不同 expression 的 token 对），跑插帧、并排对比"瞬切 vs 插帧"。不依赖完整游戏流程，迭代最快。这是 Phase 1 看效果的主路径。

集成验证（次要）：
1. `npm run dev` 启动本地 Web 服务
2. 进入 NRBI 小说，推进到同角色连续换表情的对话
3. 观察 `shouldInterpolate` 命中时是否有丝滑过渡，换装时是否正确退回瞬切
4. 控制台打印：是否命中门控、解析出的 char/outfit/expr、推理耗时、帧数

### 1.7 Phase 1 产出物

- `assets/utils/FrameInterpolator.ts` — ONNX 推理封装
- `assets/utils/LookToken.ts` — token 解析 + outfit 门控
- `StoryWnd.ts` 中 `kind === 'look'` 分支改动（加门控）
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
| **误把换装当换表情去插帧** | 鬼影（最严重） | outfit 门控 `shouldInterpolate`；解析不出 token 一律不插帧 |
| `look` 字段是短名、解析不出 outfit | 漏插帧（保守，可接受） | Phase 1 保守不插帧；Phase 2 走方案 A 由 backend 下发 outfit 字段 |
| 命名规范跨小说不统一 | 覆盖面有限 | Phase 1 只覆盖 NRBI 小说；老小说不插帧不影响现状 |
| 透明背景 PNG 插帧出现边缘伪影 | 效果差 | alpha 通道单独线性插值，RGB 合成到纯色背景后推理 |
| 表情差异太大（闭眼→大笑）产生鬼影 | 效果差 | 验证后决定是否再加表情距离门控（同 outfit 内也限制大跳变） |
| ONNX Runtime Web 包体大 | 首屏慢 | 懒加载，不影响核心游戏功能 |
| 低端 Android 无 Vulkan | 无法推理 | 降级到 ncnn CPU (ARM NEON) 或 fallback 瞬间换图 |
| 模型输入要求 32 倍数 | 边缘裁切 | pad 到最近 32 倍数，输出后 crop 回原尺寸 |

## 不做的事

- 不做服务端预计算（成本和工程复杂度不划算）
- 不做 dissolve 过渡（直接上神经网络插帧）
- **不对换 outfit / 换角色 / 出场 / 退场 / 位移做插帧**（只做同角色同 outfit 的表情/姿态切换）
- Phase 1 不优化性能（只验证效果）
- Phase 1 不改 LS / backend（用客户端 token 解析；改字段是 Phase 2 方案 A）

## 已定决策

- ✅ 纯客户端解析规范 `__` token，不加字段、不改 backend
- ✅ 老剧本（解析不出 token）不考虑，直接不插帧
- ✅ 一套规则（`shouldInterpolate`）统一判断，不加视觉相似度兜底、不加表情距离门控

## 唯一实现前确认项

**规范 token 必须出现在客户端可见字段**（建议复用 `char_show.look`）。当前编译产物 `look`/`url` 都是非规范形式，需确认 recanon 后/生产管线把规范 `char__outfit__...` token 写入 `look`。确认后规则零改动生效；若 token 在别的字段，仅改 `shouldInterpolate` 的取值来源一行。
