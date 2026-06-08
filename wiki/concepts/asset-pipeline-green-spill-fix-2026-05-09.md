---
title: Asset Pipeline — Green-Spill Root Cause + RGB Unspill Fix (2026-05-09)
updated: 2026-05-09
related:
  - concepts/asset-matting-hybrid
  - entities/dramatizer-ls
---

# Green-Spill Root Cause + RGB Unspill Fix

诊断 + 修复 NRBI sprite 在前端渲染时人物周围出现绿色边缘 + 头发/肩部内部绿色斑块的问题。

适用范围：所有走 chromakey-hybrid 路径（`to-final.py` 默认）的 sprite，包括 series character + ep_sprites（不影响 scene 背景）。

## 症状

selena ep1 BEAT 1（`@selena look eyes_narrow_thinking`，sprite_id `selena_black_dress_denim_lean_forward-to_face-to_camera_1ba8`）composited 到房间背景上：

- 整个剪影外轮廓有可见绿环（半透明绿色 1-2 px halo）
- 头发右上方 + 左肩位置有几块明显绿斑

实测 5 张 sprite，全部呈现同样问题。判断为**全本性瑕疵**而非个例。

## 根因（双源同因）

```
render-with-style.py     → gen-upscale/<id>.png            (RGB on green, 不是 RGBA)
upscale.py              → gen-upscale/<id>_upscaled.png
to-final.py 内部:
  1. cutout.py --force          (HSV chromakey, feather=0.8)        ← 留 alpha 软边
  2. hole_fill.py
  3. green_spill_clear.py       (delta=5, bright_sum=400)            ← 阈值过松, 漏 spill
  4. detect_matting_failures.py
  5. matting.py (MODNet)        (只对 detect FAIL 的, ~6%)
  6. PNG → WebP Q90 → final/
```

**双源同因 = `green_spill_clear.py --bright-sum 400`：**

```python
# green_spill_clear.py:42
leak = (
    (g > r + delta)        # 绿主导
    & (g > b + delta)
    & (a > 0)              # opaque
    & (r + g + b >= bright_sum)  # ← 这个为"保留深绿衣物"加的阈值
)
```

`bright_sum=400` 注释意图是避免误删深绿色衣服（如 forest-green jacket）。但同时把：

1. **边缘 spill**：`cutout.py feather=0.8` 把 alpha 软化成 1-2 px 渐变带，那一圈像素 RGB 仍是绿幕原色。Brightness ~270 < 400，被放过 → 视觉上整圈绿环
2. **内部 leak**：模型在头发/肩膀 inpaint 时把绿色 bounce light 留在主体内部。Brightness ~125 < 400，被放过 → 视觉上头发斑块

实测 selena_1ba8 数据：

| 指标 | 数值 |
|---|---|
| 边缘像素数 | 19,800 |
| 边缘 mean RGB | (62, **162**, 48) |
| 边缘 G 主导比例 | 85% |
| 边缘 mean R+G+B | 273 (< 400, 被 spill_clear 放过) |
| 内部 leak 像素 | 2,551 |
| 内部 leak mean RGB | (25, **74**, 25) |
| 内部 leak mean R+G+B | 124 (< 400, 被 spill_clear 放过) |

## 修复方案 — RGB Unspill (Phase 3a)

不动 `green_spill_clear` 的逻辑（保留它清深绿衣物的能力），加一步 **chromakey decontamination**（Nuke / DaVinci 行业标准）：

```python
# rgb_unspill.py — 核心算法
mask = (alpha > 0) & (G > max(R, B))
G[mask] = max(R, B)[mask]
```

只动 G 通道，不动 alpha。性质：

- **不破坏剪影**（alpha 不变 → silhouette 与原版完全一致）
- **不消除头发悬空 / cutout 削掉的发丝**（alpha 已经被削，G-unspill 救不回来）
- **idempotent**（已 unspill 的图再跑 mask=∅，noop）
- **绿色衣物安全**：深绿衣物 G 已经 > R 且 > B，压成 max(R,B) 等于把"过分绿"变成"刚好绿"，视觉上保留绿调

## 修复 vs 替代方案

| 路线 | 范围 | 修绿斑 | 修头发悬空 | 耗时（全本） |
|---|---|---|---|---|
| **G-unspill (Phase 3a)** | 在已抠完 final.webp 上 G 通道修复 | ✅ | ❌ | ~5 分钟 |
| MODNet 重抠 (Phase 3b) | 从 `_raw/` 绿幕原图走神经网络抠图 | ✅ | ✅ | ~7 小时 CPU |
| MODNet + G-unspill | 两者叠加，最干净 | ✅ | ✅ | ~7.5 小时 |

2026-05-09 选 G-unspill 全本（用户决定先救火，头发悬空原版本就有，不引入回归）。

## 实测验证（2026-05-09）

selena_1ba8 单张 BEFORE → AFTER（G-unspill）：

| 指标 | BEFORE (5/8 OSS) | AFTER (Phase 3a) |
|---|---|---|
| 边缘 mean G | 162 | **65** |
| 边缘 G 主导比例 | 85% | **0%** |
| 内部 leak 像素 | 2551 | **0** |
| 改动像素数 | — | 22,179 (1.41%) |
| 改的内容 | — | 只 G 通道，alpha 不动 |

5 张 sprite spot-check：edge_G 均从 ~150 → ~55，interior leak 均从几千 → 0。

## 落地位置

- **脚本**：`lunaverse-backend/generate-upscale-matting/rgb_unspill.py`（133 行）
- **CLI**：`python3 rgb_unspill.py --root <dir> --workers 8`
- **2026-05-09 全本运行**：3289 张文件 → ok=3084 skip=189（RGB 模式自动跳过）err=16（PIL 打不开的 broken webp，跟 unspill 无关）。耗时 5.6 分钟。
- **OSS sync**：`sync_to_oss.py --force` 推送 3173 个 task 到 `mobai-file/nrbi/`，全部成功（↑3173 ↻0 ✗0）

## 后续根治建议

将 `rgb_unspill.py` 集成进 `to-final.py` 的 `run_chromakey_hybrid()`，作为 `green_spill_clear` 之后必跑的一步。这样下次跑 to-final 不会再产生绿环 sprite，也不需要事后人工补救。建议位置：`to-final.py:165` 之后增加 `subprocess.run([sys.executable, str(SCRIPT_DIR / "rgb_unspill.py"), "--paths", paths_arg], check=True)`。

## 已知遗留问题

- **16 张 javier sprite corrupted**：5/9 to-final 当时写盘失败，PIL 无法打开。需要重跑 to-final 这 16 个 ID 才能修复。清单：

```
ep1/javier_carhartt_workwear_upright-to_face-to_camera_bd23.webp
ep1/javier_casual_lean_back-extended-to_object_cd69.webp
ep1/javier_casual_lean_forward-extended-to_floor_fa97.webp
ep1/javier_casual_seated-by_side-to_floor_4eeb.webp
ep1/javier_casual_seated-clasped-side_65b4.webp
ep1/javier_casual_seated-extended-to_object_923f.webp
ep1/javier_casual_seated-holding-to_floor_5f20.webp
ep1/javier_casual_seated-holding-to_object_316b.webp
（同样的 8 个文件名也 corrupt 在 ep_sprites/ 顶层）
```

- **头发悬空** = `cutout.py feather=0.8` 削掉的发丝，G-unspill 救不了。如果要救必须走 MODNet 重抠（~7 小时全本）。

## 相关

- [[concepts/asset-matting-hybrid]] — chromakey-hybrid pipeline 总体设计
- [[entities/dramatizer-ls]] — novels-to-lunascript skill workflow
- novels-to-lunascript：`docs/superpowers/plans/2026-05-09-recovery-status.md`（含 unspill 段补丁）
