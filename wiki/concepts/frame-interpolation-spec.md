---
title: 角色表情插帧实施方案
tags: [rife, interpolation, animation, cocos, client, spec]
created: 2026-06-29
updated: 2026-06-30
---

角色 look 切换（编译为 `char_show`）原本是瞬间换图，没有过渡。本方案用神经网络插帧（RIFE）生成中间帧，让"同角色同服装、动作小"的换表情/微动作丝滑过渡；其余一律保持瞬间切换。**Phase 1 已真正接进 Web 端**（生产代码，非 demo），核心运行时已在真实浏览器 E2E 验证；Phase 2 推广到 Android/iOS（同模型转 ncnn）。

相关代码：[[entities/lunaverse-client]]。视觉小说展示形态：[[concepts/unfolded-visual-novel]]。

## 核心设计：两道门控，全过才插帧

每次 look 变化按顺序过两道门，**两关都过才用 RIFE，否则保持原瞬间切换**：

| 门控 | 判断方式 | 不过 → |
|---|---|---|
| ① 服装/角色 | 纯字符串 `token.split('__')` 取 char/outfit | 直接切换（换装插帧会鬼影） |
| ② 动作幅度 | **像素**：两帧缩 64×64、over-black 预乘，算 changedFrac + mae | 直接切换（大动作 RIFE 糊成残影） |
| ③ 都过 | 同角色 + 同服装 + 动作小 | **RIFE 插帧** |

### 门控①：解析规范 `__` token 取 outfit（已实测纠正）

> **纠正历史错误**：本 spec 旧版采用"解析 URL 文件名 + posture 闭集锚定"，前提是"规范 `__` token 没下发到客户端"。**该前提实测为假**——`look` 和 `url` **都是完整规范 token，`__` 原样保留**。5 个已编译 NRBI 小说共 **7910/7910 char_show step 100% 规范 `__`**。所以直接 `split('__')` 即可，posture 闭集方案是在解一个假问题，已废。

规范 token：`{char}__{outfit}__{posture}-{position}-{camera}-{expression}.webp`，例 `selena__casual__upright-by_side-to_camera-neutral`。

```ts
// assets/utils/LookId.ts
export function parseCanonicalToken(token: string): { char: string; outfit: string } | null {
  const stem = String(token).split('/').pop()!.replace(/\.[a-z0-9]+$/i, '');
  const parts = stem.split('__');
  if (parts.length < 3) return null;            // 老剧本 / 非规范 → 安全跳过
  return { char: parts[0], outfit: parts[1] };
}
export function shouldInterpolate(prev, next): boolean {
  if (!prev || prev.character !== next.character) return false;
  if (prev.url === next.url) return false;
  const a = parseOutfit(prev), b = parseOutfit(next);   // 优先 look 含 __，否则 url
  return !!a && !!b && a.char === b.char && a.outfit === b.outfit;
}
```

纯字符串、确定性、无阈值、不解码。安全退化：解析不出 → 不插帧。

### 门控②：像素动作幅度（必须看像素，不能看 token）

`position` 字段**不可靠**：实测有对子两帧 `position` 都是 `by_side`，但手臂实际从垂手摆到抱臂。所以动作幅度只能解码后量像素。

度量（解码两端点后、推理前，很便宜）：两帧缩到 **64×64**、over-black 预乘，算 `changedFrac`（max 通道差 > 24 的像素占比）和 `mae`（平均绝对色差 0..255）。

**规则：插帧 ⟺ changedFrac(64) ≤ 0.18 且 mae(64) ≤ 12，否则切换。** 标定锚点（用户亲自看过）：

| 对子 | changedFrac | mae | 判定 |
|---|---|---|---|
| 微表情/微动 (pos2) | 0.07 | 4.7 | 插帧 ✅ |
| 中等摆臂 (pos1) | 0.25 | 15 | 切换 |
| 弯腰→起身 (pos0) | 0.46 | 28 | 切换（用户："动作太大不该用"）|

75 个真实同 char/outfit 对子：41 插 / 34 切。**关键验证**：一个 token 标"只换表情"但像素和 pos0 一样大的对子被正确判为"切换"——像素门控盖过骗人的 token。原则：拿不准就切（漏插无感，糊脸丑）。实现：`FrameInterpolator.measureMotion / isMotionInterpolatable`。canvas 版度量与 sharp 标定版分类一致（浏览器实测）。

## 模型

**实测（2026-06-30）**：标准仓库 `yuvraj108c/rife-onnx` **只有 rife47/48/49，全 `ensemble_True`，全 20MB，没有 rife46、也没有更轻的 ensemble_False**（逐个 HTTP 404 确认）。三者画质/速度实测**等价**（速度只由分辨率决定，不由版本决定）。**选 rife49**（最成熟 + 已验证）。

- 签名：`img0`/`img1` float32 `[1,3,H,W]` + `timestep` float32 `[1]`（rank-1 标量 0..1）→ `output [1,3,H,W]`；H/W 须 32 倍数。
- **N 帧 = N 次独立调用 t=i/(N+1)**（不是旧 spec 的递归二分）。
- 预/后处理：RGBA premult-over-black → /255 → NCHW；输出 un-premultiply，alpha 单独 per-pixel lerp。
- **移动端口径一致**：rife49 = RIFE v4.x，和 native ncnn（rife-ncnn-vulkan 默认 v4.6、也支持 v4.x）同家族。若 native 必须精确 v4.6，那份 ONNX 不在此仓库，需另找源 / 从 PyTorch 导出再转 ncnn（独立一步，待拍板）。

## Phase 1：已落地到 Web（生产集成）

### 模块
- `assets/utils/LookId.ts` — 门控①（服装，纯字符串）。
- `assets/utils/FrameInterpolator.ts` — ONNX 封装：loader + 门控②像素度量 + interpolate + 共享常量。
- `assets/bundles/play/story/StoryWnd.ts` — `kind==='look'` 钩子 + 门控② + 播帧 + 旧图保持。

### Web 集成方式（关键工程决策）
- **加载**：注入 `<script>` 用全局 `window.ort`（UMD `ort.wasm.min.js`），**不走** dynamic import——绕开 Cocos 打包器（之前隐患）。`.mjs` dynamic import 作为 dev 兜底。
- **单线程 WASM，不开 COOP/COEP**：开跨域隔离会**破坏 R2 跨域立绘加载**，得不偿失。`numThreads=1`（除非页面已 isolated）。
- **运行时+模型**放 `build-templates/web-mobile/vendor/interp/`（`ort.wasm.min.js` + wasm + `rife49.onnx`），构建拷进 `build/web-mobile/vendor/interp/`。33MB 二进制 **gitignore**，`scripts/fetch-interp-assets.mjs` 拉取（固定版本 + md5 校验）；构建产物自包含。
- **默认开启**：web 默认开，`?interp=0` kill switch；native/非 DOM/任何失败 → 回退瞬切（try/catch 兜底，绝不破坏场景）。

### 帧数 / 时序 / 自然度
- **5 张中间帧**（用户认可"四五个够了"），**每帧 50ms**，整段 morph ≈ 300ms（微表情真实节奏 150–400ms）。
- **插帧分辨率 maxSide 256**（160×256，小动作干净，速度是 384 两倍）；**临时播放纹理 ~显示分辨率 512**（旧图保持 + 中间帧不比之前的清晰图糊），最后落到全分辨率新图。
- **自然度关键修复**：`renderCharacterSlot` 会先把槽位换成新图，导致预计算的 ~1.25s 里"闪新图→倒带→morph"。改为**预计算期间保持显示旧表情**，算完再 morph→新，统一临时纹理承载，无倒带无尺寸错配。
- 常量都在 `FrameInterpolator.ts` 顶部：`INTERP_NUM_FRAMES / INTERP_MAX_SIDE / INTERP_FRAME_SECONDS / INTERP_DISPLAY_MAX_SIDE / MOTION_*`。
- 性能：单线程 ~250ms/帧@256，5 帧预计算 ~1.25s，藏在"继续显示旧表情"里；快速点过会被生成令牌取消 → 优雅回退。

### 验证状态
- **已浏览器 E2E 验证**（esbuild transpile 真实 `FrameInterpolator.ts` + `cc` shim，真立绘 + 真模型）：`window.ort` 单线程加载 OK、门控分类三个全对、interpolate 5 帧@160×256 画面干净无鬼影、TS 严格编译通过。
- **未验证**：`cocos build` 本身（本机无 Cocos 编辑器 / `cocos` 不在 PATH），最后构建冒烟需在有编辑器的机器跑 `npm run build` + `npm run dev`。Cocos 胶水（`Texture2D.uploadData`/`SpriteFrame`）照搬 `VideoTexturePlayer` 模式，风险低。

## Phase 2：Android / iOS（待 Phase 1 审核通过）

- **模型**：同 RIFE v4.x 转 ncnn（`rife-ncnn-vulkan` 成熟）。`FrameInterpolator.init()` 现在 native 返回 false（回退瞬切），native 路径走 JSB 桥接 ncnn，公共接口不变。
- **Android**：ncnn + Vulkan（API 24+），低端降级 ncnn CPU(NEON) 或瞬切。
- **iOS**：ncnn + Metal（或 iOS 26 `VTFrameProcessor` 系统级插帧，若目标版本够高可免自带模型）。
- **门控①②纯客户端、平台无关**，原样复用。

## 风险与缓解

| 风险 | 缓解 |
|---|---|
| 误把换装当换表情插帧 → 鬼影 | 门控① `__` token 精确解析，7910/7910 实测 0 误判 |
| 同 outfit 内大动作插帧糊 | **门控②像素动作幅度**（changedFrac≤0.18 & mae≤12）已实现，pos0 类正确切换 |
| token `position` 不反映真实动作 | 不信 token，量像素 |
| ORT/模型 33MB 拖首屏 | 懒加载，首次插帧才加载；gitignore + fetch 脚本 |
| 跨域隔离破坏 R2 立绘 | 不开 COOP/COEP，单线程 |
| 透明边缘伪影 | alpha 单独 lerp，RGB over-black 推理 |

## 不做 / 已废

- 不做服务端预计算、不做 dissolve（直接神经插帧）、不加 step 字段 / 不改 LS·backend（纯客户端 token）。
- **已废**：解析 URL 文件名 + posture 闭集锚定（基于"`__` 没下发"的假前提）；视觉颜色直方图门控（无干净阈值，漏 37% 换装去鬼影）。

## 实测记录

- 2026-06-29：`__` token 100% 下发（7910/7910），推翻 posture 闭集；rife49 在 ORT-Web WASM 可加载可跑，RIFE 单张形变 >> 朴素 cross-dissolve 双影。
- 2026-06-30：仓库只有 rife47/48/49 ensemble_True（等价）；像素动作门控标定 cf≤0.18 & mae≤12@64；`window.ort` 单线程 loader + 门控 + interpolate 浏览器 E2E 通过；效果对比视频（瞬切 vs RIFE morph + 大动作 gate demo）已产出。
