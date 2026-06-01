---
title: V10 抠图遗漏 sharpen_alpha bug + 修复（2026-05-28）
updated: 2026-05-28
---

# V10 抠图遗漏 sharpen_alpha 步骤 — halo 根因 + 修复

## TL;DR

`generate-upscale-matting/matting.py` 的 V10 重构（2026-05-12，作者关注修 hallucination）把 legacy `_matte_array` 末尾的 **`sharpen_alpha()` 步骤丢了**。后续从这份代码 port 到 `moonshort-ide/modal-comfy/matting_v10.py` 的 Modal endpoint 一并遗漏。

结果：从 Modal matting endpoint 出来的 sprite alpha=255（完全实体）只占 ~2.5%，半透明带占 ~25%；本应是 ~26% 实体 + ~1% 半透明（V4 5070ti baseline）。整个角色身体处于半透明状态 → 深色 / 饱和背景合成时出现明显亮 **halo**。

修复一行半：在 `matte_v10()` 末尾 `return` 前加 `alpha = sharpen_alpha(alpha)`。修复后 alpha 分布与 V4 baseline 完全一致（误差 <1pp）。

**影响范围**：2026-05-12 起所有走 Modal `matting` endpoint 的 sprite。**NRBI-rewrite EP1-8 整批 591 张全部受影响。**

## 数据证据（selena 同一角色 chin_up pose）

| 来源 | a=0% | **a=255%** | **semi%** | 备注 |
|---|---|---|---|---|
| V4 5070ti（legacy `_matte_array`，含 sharpen_alpha） | 73.0 | **26.3** | **0.7** | 干净，无 halo |
| nrbi-rewrite OSS（Modal V10 port，无 sharpen_alpha） | 72.7 | **2.5** | **24.8** | 满身 halo |
| 修复后 Modal（V10 + sharpen_alpha） | 72.6 | **26.6** | **0.8** | 干净 ✓ |

`sharpen_alpha` 公式（line 191-196 of canonical matting.py）：
```python
return np.clip((alpha.astype(np.int32) - 10) * 255 // (192 - 10), 0, 255).astype(np.uint8)
```
- alpha < 10 → 0
- alpha > 192 → 255
- 中间区间线性拉伸

## 根因分析

两条 pipeline 在 canonical `generate-upscale-matting/matting.py` 里：

| Pipeline | 调用栈 | 含 sharpen_alpha? |
|---|---|---|
| **V4 legacy** `_matte_array` | MODNet → chromakey gate → unmix → edge decontam → **sharpen_alpha** → stack | ✓ |
| **V10 `_matte_array_v10` → `matte_v10`** | MODNet → matte_v10（hard_bg + CC + spill + halo dilate + orphan cleanup） | ✗ |

V10 设计目标是修 **hallucination 类问题**（leg-gap 假洞、negative-space 误填、furniture 抢救），完全没考虑 alpha 锐化。`matte_v10` 内部只把背景设 0、把 rescue 区设 255，对 MODNet 输出的 soft body（典型值 180-250）完全不动。

Modal port (`moonshort-ide/modal-comfy/matting_v10.py`) 抄的是 V10 路径，忠实地继承了这个遗漏。`SHARPEN_LO=10` / `SHARPEN_HI=192` 常量留在 modal port 里但没人用 — 这是这个 bug 的指纹。

## 时间线 / 为什么 V4 NRBI 没事而 nrbi-rewrite 出事

- **2026-05-12 前**：5070ti 服务跑 legacy `_matte_array`（含 sharpen_alpha）。V4 NRBI 整批就是那时渲的 → 干净。
- **2026-05-12**：作者部署 V10 到 Windows 5070Ti（`docs/superpowers/handoffs/2026-05-12-v10-windows-deploy.md`）。专注修 leg-gap 假洞。**未察觉 alpha 软化退化**。
- **2026-05-21**：Modal `matting` endpoint 用 V10 port 上线（`comfyui-modal-deploy`）。
- **2026-05-26**：NRBI-rewrite bootstrap 调 Modal `postprocess_modal.py` 跑 153 sprites（实际入 OSS 591 张含 alias）。**整批 alpha 软化 → 全部带 halo**。
- **2026-05-28**：用户在 demo 上看到 selena 立绘亮边 → 诊断 → 找到根因。

## 修复（2026-05-28）

### 长期（已部署）

[`moonshort-ide/modal-comfy/matting_v10.py`](https://github.com/AugustZAD/Dramatizer-MSS) (本地 path)：

1. 加 `sharpen_alpha()` 函数（从 canonical 抄）
2. 在 `matte_v10()` 末尾 `return` 前调一次

`.venv/bin/modal deploy app.py` 重新部署，7.4s 完成。

验证：用同样的 raw 绿幕 PNG 调新 endpoint，输出 alpha 分布 `a=0=72.6% / a=255=26.6% / semi=0.8%` ≈ V4 baseline（误差<1pp）。

### 短期止血（已执行）

OSS bucket `mobai-file` 的 `nrbi-rewrite/*.webp`（top-level 591 张）批处理：
- 拉 → 备份到 `nrbi-rewrite/_backup_pre_sharpen_2026-05-28/<name>.webp`（idempotent，HEAD 已存就跳）
- 套 sharpen_alpha → 编码 WebP Q90 method=6 → 覆盖回原 key
- ProcessPool 8 workers + done-file 跟踪，kill-safe

脚本：`novels-to-moonscript/_test_runs/2026-05-28_batch-vs-single-and-halo-smoke/d-oss-sharpen-fix/sharpen_oss_sprites.py`

OSS key 不变 → 前端 hard reload 即可，**不需要 reseed / 重编译 MSS**。

## 留给以后的教训

1. **重构关键算法时必须做行为契约对照 test**。canonical → port 复制时，应该有 1 张 reference sprite + alpha 分布 fixture（a=0 73%, a=255 26%, semi 0.7% ±2pp）。任何 port 跑同一张 sprite alpha 分布偏离 fixture 5pp 都该 fail。
2. **常量留下来但函数没了 = 抄漏信号**。modal port 里 `SHARPEN_LO=10 / SHARPEN_HI=192` 是 dead code 状态，应该被 lint 警告。
3. **视觉 halo 不一定是 spill 问题**。v10 已经有 spill suppression（Step 4 改 G channel）。这次 halo 是身体半透明导致的"全身渗透"，跟绿色 spill 无关。诊断要先看 alpha 分布而非 RGB。
4. **`SHARPEN_LO/HI = 10/192` 是 lo/hi 钳位阈值不是参数**。10 = 噪声地板，192 = 接近实体的开始。这两个值在 canonical 是常量、不调，因为 MODNet 训练就是这个 distribution。

## 相关页

- [[concepts/asset-matting-hybrid]] — 整体抠图流水线（A 默认 + B 兜底）
- [[concepts/asset-pipeline-green-spill-fix-2026-05-09]] — 另一类问题（绿色 RGB spill，与本 bug 无关）
- [[concepts/comfyui-modal-deploy]] — Modal matting endpoint 部署 spec
