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

**插帧触发条件（同时满足）**：
1. 同角色（`character` 字段相同）
2. **同 outfit**（从 URL 文件名解析，见下）
3. 不同立绘（url 不同，确有变化）

**不触发**：换 outfit / 换角色 / 出场 / 退场 / 位移；非规范命名（老小说）一律不插帧。

### 决策（已定 + 已实测）：解析 URL 文件名取 outfit，锚定 posture 闭集

走了弯路、用真图测过，结论清晰：

- ❌ **解析规范 `__` token**：作废。实测客户端收到的 `look`（作者短名 `coat_zipped_breath_visible`）/ `url` **都不含 `__`**，规范 token 没下发到客户端。
- ❌ **视觉相似度门控（颜色直方图）**：**实测失败**。24 张真图：换 outfit 但配色像的（`formal_social` vs `evening_gown`）相似度 0.97 误判可插，同 outfit 换姿势的相似度 0.10 误判要跳；最佳阈值仍漏 **37%** 换装去鬼影。无干净阈值 → 不靠谱。
- ✅ **解析 URL 文件名取 outfit**：**实测通过**。2014 张真图 **0 解析失败**，干净分出 28 个 (char, outfit) 组，同 outfit/换 outfit 判定全对。

**原理**：客户端 URL 文件名格式 `{char}_{outfit}_{posture}-{position}-{camera}_{hash}.webp`。
`character` 字段已知 → 剥掉 `{char}_`；posture/position/camera 来自**闭集**（实测全量 NRBI：posture ~10 个、position 13 个、camera 9 个）。锚定 posture 闭集即可无歧义切出 outfit。

```ts
// assets/utils/LookId.ts
// posture 闭集（实测自 NRBI 全量 mapping；新增也只会让解析失败 → 安全跳过不插帧）
const POSTURES = [
  'back_to_camera','lean_forward','lean_back','turn_side','chin_down',
  'chin_up','upright','leaning','seated','walking','crouching','kneeling',
].sort((a,b)=>b.length-a.length);                 // 最长优先，避免后缀误配

// 文件名: {char}_{outfit}_{posture}-{position}-{camera}_{hash}.webp
export function parseOutfit(url: string, character: string): string | null {
  const fn = (url.split('/').pop() ?? '').replace(/\.[a-z0-9]+$/i, '');
  if (!fn.includes('-')) return null;              // 无 descriptor（老小说）→ 不插帧
  const head = fn.split('-')[0];                    // {char}_{outfit}_{posture}
  const prefix = character + '_';
  if (!head.startsWith(prefix)) return null;
  const rest = head.slice(prefix.length);           // {outfit}_{posture}
  for (const p of POSTURES) {
    if (rest === p) return '';
    if (rest.endsWith('_' + p)) return rest.slice(0, -(p.length + 1));
  }
  return null;                                       // 未知 posture → 安全跳过
}

// 唯一判断入口
export function shouldInterpolate(prev, next): boolean {
  if (prev.character !== next.character) return false;
  if (prev.url === next.url) return false;
  const a = parseOutfit(prev.url, prev.character);
  const b = parseOutfit(next.url, next.character);
  return a !== null && b !== null && a === b;        // 同角色同 outfit
}
```

- **靠谱**：纯字符串、确定性、无阈值、无标定。实测 0/2014 失败、判定全对。
- **简单**：~15 行 + 一个 ~12 词常量数组；门控阶段**不解码图片**。
- **零依赖**：不加 step 字段、不改 backend/LS、纯客户端。
- **安全退化**：解析不出（老小说 / 未知 posture）→ 返回 null → 不插帧（瞬切），绝不鬼影。

> 唯一耦合：posture 闭集需与素材管线一致。管线新增 posture 时，旧客户端对该立绘解析失败 → 安全跳过（不鬼影、只是不插帧），不会出错。值得在素材管线 spec 里把 posture 词表标注为"客户端契约"。

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

### 1.2 outfit 门控：新增 `LookId.ts`

位置：`assets/utils/LookId.ts`。职责：从 URL 文件名解析 outfit，判断"同角色同 outfit"。是插帧的**唯一前置闸门**。完整实现见上文「决策（已定 + 已实测）」代码块（`parseOutfit` + `shouldInterpolate`，约 15 行）。纯字符串、无解码、无阈值。

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
    const prev = this.renderedCharacterSlots[slot];   // 含 character + url
    const next = 当前 data;                            // 含 character + url
    if (this.frameInterpolator && shouldInterpolate(prev, next)) {
        this.playInterpolatedLookTransition(slot, prev.url, next.url, targetAlpha);
        return;
    }
    // 换装 / 老小说 / 无插帧器 → 原有瞬切
    this.setCharacterSlotOpacity(slot, targetAlpha);
    return;
}
```

> 门控是纯字符串判断、先于解码，命中才去解码两图跑插帧。

### 1.4 新增方法：`playInterpolatedLookTransition()`

```
async playInterpolatedLookTransition(
  slot: SlotName,
  oldUrl: string,
  newUrl: string,
  targetAlpha: number
): void
  // （门控已在调用前 shouldInterpolate 判过，这里直接插帧）
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

### 1.5 输入预处理（接 1.4）

角色图特殊性：
- 透明背景 PNG（RGBA），RIFE 期望 RGB
- 需要统一处理 alpha：合成到黑色或白色背景后送入模型，输出后重新提取 alpha
- 简单方案：alpha 通道单独做线性插值（`alphaOut = lerp(alphaA, alphaB, t)`），RGB 走 RIFE
- 两张图可能尺寸不同：resize 到统一尺寸（取较大者，对齐到 32 的倍数）

### 1.6 测试方式

**独立 demo 页面优先**（`test/interpolation-demo.html`）：从 `dont-pretend-with-me` 的 mapping.json 取同角色样本对（同 outfit 不同 pose 的正样本 + 换 outfit 的负样本），跑插帧并排对比瞬切。`shouldInterpolate` 已实测无需标定，这里重点看**插帧视觉效果本身**好不好。这是 Phase 1 主路径。

集成验证（次要）：
1. `npm run dev` 启动本地 Web 服务
2. 进入 NRBI 小说，推进到同角色连续换表情的对话
3. 观察门控命中时是否丝滑过渡，换装时是否正确退回瞬切
4. 控制台打印：解析出的 outfit、是否命中、推理耗时、帧数

### 1.7 Phase 1 产出物

- `assets/utils/FrameInterpolator.ts` — ONNX 推理封装
- `assets/utils/LookId.ts` — outfit 解析 + `shouldInterpolate` 门控（已实测）
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
| **误把换装当换表情去插帧** | 鬼影（最严重） | `shouldInterpolate` outfit 解析门控；实测 0/2014 失败 |
| posture 闭集与管线漂移 | 漏插帧（保守） | 未知 posture → 解析失败 → 安全跳过；posture 词表登记为客户端契约 |
| 同 outfit 内大幅度变化（坐→走、侧身） | 插帧可能糊 | 验证后可选：再叠加一个轻量结构差异上限（同 outfit 内也限制大跳变） |
| 透明背景 PNG 插帧出现边缘伪影 | 效果差 | alpha 通道单独线性插值，RGB 合成到纯色背景后推理 |
| ONNX Runtime Web 包体大 | 首屏慢 | 懒加载，不影响核心游戏功能 |
| 低端 Android 无 Vulkan | 无法推理 | 降级到 ncnn CPU (ARM NEON) 或 fallback 瞬间换图 |
| 模型输入要求 32 倍数 | 边缘裁切 | pad 到最近 32 倍数，输出后 crop 回原尺寸 |

## 不做的事

- 不做服务端预计算（成本和工程复杂度不划算）
- 不做 dissolve 过渡（直接上神经网络插帧）
- 不加 step 字段、不改 LS / backend（纯客户端解析 URL）
- 不依赖视觉相似度门控（实测不可靠，已作废）
- 不对换 outfit / 换角色 / 出场 / 退场 / 位移做插帧
- Phase 1 不优化性能（只验证效果）

## 已定决策（含实测依据）

- ✅ **解析 URL 文件名取 outfit**（锚定 posture 闭集），同角色同 outfit 才插帧
- ✅ 纯字符串、确定性、无阈值；**实测 2014 张真图 0 解析失败、判定全对**
- ✅ 不加字段、不改 backend/LS、纯客户端；解析不出 → 安全跳过不鬼影

### 实测记录（2026-06-29）

24 张真图 + 2014 张全量 URL 实测三种方案：
- 解析规范 `__` token：**作废** — token 没下发到客户端
- 视觉颜色直方图门控：**失败** — 无干净阈值，最佳阈值仍漏 37% 换装去鬼影（换 outfit 配色像的 0.97 误判可插、同 outfit 换姿势 0.10 误判要跳）
- **解析 URL 文件名 + posture 闭集锚定：通过** — 0/2014 解析失败，28 个 (char,outfit) 组判定全对 ← 采用
