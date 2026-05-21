---
title: Asset Matting Hybrid (A 默认 + 检测 + B 兜底)
updated: 2026-05-22
status: superseded
superseded_by: ESRGAN ×2 + MODNet + V10 服务端全链（2026-05-12 起 donor 上线，2026-05-22 IDE 侧迁移完成）
---

# Asset Matting Hybrid (A 默认 + 检测 + B 兜底)  ⛔ SUPERSEDED

> **2026-05-22 起本页冻结。** 这套 "chromakey 主路径 + MODNet 兜底" 的混合架构整体被替代：
> donor (`moonshort-backend/generate-upscale-matting`) 自 2026-05-12 起把全量 NRBI 主流程升级到
> **ESRGAN ×2 → MODNet → V10 服务端后处理 (hard-bg + size-filtered CC + spill suppression + unmix
> + edge decontam + alpha sharpen + feather)**。MODNet 不再是 "兜底"，而是主路径；HSV chromakey
> + hole_fill + green_spill_clear 这套 V4-era 后处理已从 IDE 侧 (`asset-renderer/SKILL.md` Layer
> 6-9) 删除。详见：
>
> - **donor 真相源**：`~/MobAI/moonshort-backend/generate-upscale-matting/matting.py` `V10_*` 常量 + `matte_v10()`
> - **IDE 迁移设计**：`docs/design/2026-05-22-asset-renderer-v10-migration-design.md`（moonshort-ide repo）
> - **IDE 实现**：`agents/asset/skills/asset-renderer/postprocess_v10.py`（oss-put → upscale-image → matting → HTTP GET）
> - **modal-comfy 端**：`modal-comfy/matting_v10.py`（port of donor v10）+ `modal-comfy/app.py` `handle_matting` 端点
>
> 下面 §1-§N 是 2026-05-06 当时的设计快照，**仅作历史记录**。不要按这个架构新开发；任何新代码应直接走 V10 全链。

---

novels-to-moonscript / asset-renderer 的抠图流水线架构 —— 让 chromakey 主路径自动检测翻车、用 MODNet 兜底，而不是单方案替换。

> 完整 spec：[novels-to-moonscript/docs/superpowers/specs/2026-05-06-matting-hybrid-design.md](https://github.com/cdotlock/moonshort-backend) (项目内 git，未公开)

## 1. 背景：为什么不直接换模型

`asset-renderer` Layer 6 走 HSV chromakey（`cutout.py`），有两类稳定翻车：

1. **主体含绿色像素**：衣服 / 配饰落在 hue ∈ [80°, 160°]，被一并抠掉。例：`selena_green_dress.png` 裙子下半被打成洞。
2. **深色衣服 SV 误判**：HSV 阈值 `S>=0.30 V>=0.25` 在「深色衣服 + 阴影」边缘把暗色像素误归类为绿屏。例：`selena_casual.png` 黑色长袖胸前被抠出大洞（5.8 万像素）。

`green_spill_clear.py` 是 chromakey 边缘 spill 的事后修补，对**主体本身被抠**这种结构性故障无效。

**直觉解法是「换 MODNet portrait matting 替换 chromakey」**，不可行的原因：

- 单张 5s vs <1s（350 张全本 30 分钟 vs 6 分钟）
- 11 张回归里 MODNet 在 3 张明显输 chromakey（priya / mrs_ashby / ximena 飘逸长 gown / 深色长裤被识别成黑色 blob）
- 重依赖 `torch + ckpt` (~600MB)

## 2. A/B 实验数据（2026-05-06）

11 张代表性 NRBI anchor PNG（绿屏原图），对比：

- **Pipeline A**：`cutout.py` (HSV chromakey) + `green_spill_clear.py` —— 现状
- **Pipeline B**：MODNet + 4 步后处理（unmix → edge_decontaminate → alpha_sharpen），来自 sister 项目 Dramatizer-MSS

| 样本 | A holes% | B holes% | 谁赢 |
|---|---:|---:|---|
| selena_green_dress | **17.0%** | 0.17% | **B WIN** |
| selena_casual | 0.42% (body-gap **103k**) | 0.13% | **B WIN** |
| camila_lavender_silk_outfit | 0.45% | 0.23% | TIE |
| diego_shirtless_jeans | 4.23% (腿间空隙 false alarm) | 3.87% | TIE |
| mr_ashby_formal_evening_suit | 2.17% | 1.67% | TIE |
| mrs_ashby_formal_gown | 1.00% | **3.01%** | **A WIN** |
| priya_evening_gown | 0.81% | **8.27%** | **A WIN** |
| weston_basketball_uniform | 2.26% | 2.16% | TIE |
| camila_bathrobe | 0.89% | 0.56% | TIE |
| ximena_nurse_uniform | 1.97% | **5.17%** | **A WIN** |
| mr_bellamy_luxury_three_piece | 2.10% | 1.84% | TIE |

**汇总：B WIN 2，A WIN 3，TIE 6。**

### 关键发现：失败模式互不重叠

| 方案 | 失败模式 | 触发条件 |
|---|---|---|
| A (chromakey) | 主体被当背景抠掉 | 主体颜色 hue ∈ [80°, 160°] / 深色衣服 SV 接近阈值边缘 |
| B (MODNet) | 主体识别错（黑 blob + 白洞） | 飘逸长 gown / 深色长裤 / 训练分布外的画风 |

A 在 selena 绿裙、黑长袖上失败；B 在 priya / mrs_ashby gown / ximena 长裤 上失败。互不重叠 → 互为兜底是免费的质量提升。

## 3. 设计：A 默认 + 检测 + B 兜底

### 流程

```
渲染原图 (绿屏 RGB)
    ↓
[Layer 6] cutout.py (chromakey)
    渲染输出先 cp 到 _raw/ 备份
    再就地抠图 → series/<id>.png (RGBA)
    ↓
[Layer 8] green_spill_clear.py (现状不变)
    ↓
[Layer 9] detect_matting_failures.py (新)
    扫所有 RGBA → detect_report.json
    判定：holes% > 3% OR body_gap_px > 100,000 → FAIL
    ↓
[Layer 10] matting_modnet.py (新)
    对 detect_report 标 FAIL 的：
      1. 从 _raw/ 取绿屏原图
      2. 备份当前 A 输出到 _a_backup/
      3. 跑 MODNet + 4 步后处理
      4. 覆盖 series/<id>.png
      5. 落 matting_log.json
```

### 为什么是「A 默认」不是「B 默认」

| 方案 | 全本耗时（350 sprite） |
|---|---|
| A 默认 + B 兜底 ~10% | A 6min + B 3min = **~9min** |
| B 默认 + A 兜底 | B 30min + A 10s = ~30min |

11 张样本里 A 在 9 张 OK（A WIN 3 + TIE 6），真翻车 2 张。A 是日常路径，B 是兜底。

### 关键设计决定

1. **B fallback 跳过 Real-ESRGAN upscale**：MODNet 内部强制 resize 到 ~512 短边，input 768 vs 1536 对识别能力几乎无影响。跳过 → 输出 768×1376（跟 A 一致）→ 下游 OSS / mapping / canonical_wardrobe 契约零改动。单张 5s vs 完整 80s（16 倍快）。
2. **4 个独立 CLI，不做 orchestrator**：跟现有 `cutout.py` / `green_spill_clear.py` / `hole_fill.py` 同构，可单独 rerun / debug。Layer 9 后可以人审 `detect_report.json` 再决定要不要触发 Layer 10。
3. **只对未来新 sprite 生效，不重渲历史**：cutout.py 加 `--backup-to` 默认 `_raw`。已有 NRBI sprite 没有 `_raw/`，跑 Layer 10 时遇到这种情况 skip + warn。
4. **detector 阈值**：`holes_pct > 3.0% OR body_gap_px > 100,000` —— 由 11 张样本回归得出，覆盖所有真阳性（diego_shirtless 是无害 false positive 来自腿间空隙）。
5. **A 输出备份到 `_a_backup/`**：B 重跑可能也翻车（指标会改但不一定全好），保留 A 副本让 reviewer 有 ground for 回滚。
6. **`matting_log.json` 落决策日志**：每 sprite 的 backend / 指标 / 决策，下游 reviewer 可读这个日志做精准复盘。

### Detector 算法（关键修正）

```
solid = alpha >= 240
closed = morphological_closing(solid, disk=10)  # 闭合腿间空隙等窄缝
filled = binary_fill_holes(closed)               # 填闭合后剩下的内部洞
holes  = (filled & ~closed).sum()                # 真正的内部洞
```

原版 `binary_fill_holes(solid)` 会把「两腿之间的合法空隙」也当 hole 算，导致 diego_shirtless 这种站姿样本误判 FAIL（实测 4.23% holes，全是腿间空隙）。引入 `closing(disk=10)` 先填窄缝、`fill_holes` 再补内部洞，两者配合得到「真正的、structurally enclosed by silhouette」的洞。

## 4. 目录结构

```
asset-img/<book-slug>/
├── _raw/                ← 新增：cutout 备份原图
│   ├── series/character_<id>.png      (绿屏 RGB, B 兜底输入)
│   └── ep_sprites/<ep>/<sprite>.png
├── _a_backup/           ← 新增：B 重跑前备份 A 输出
│   └── series/character_<id>.png      (RGBA, 仅 fail 触发 B)
├── series/              ← 不变（最终交付，B 触发后被覆盖）
├── ep_sprites/          ← 不变
├── detect_report.json   ← 新增：Layer 9 输出
├── matting_log.json     ← 新增：每 sprite 决策 + 指标
└── img_review.md        ← 现有
```

## 5. 组件清单

| 组件 | 文件 | 状态 |
|---|---|---|
| chromakey 抠图 | `skills/asset-renderer/cutout.py` | 改（加 `--backup-to`） |
| 边缘 spill 清理 | `skills/asset-renderer/green_spill_clear.py` | 不变 |
| 内部洞补丁 | `skills/asset-renderer/hole_fill.py` | 不变（escape hatch） |
| 翻车检测 | `skills/asset-renderer/detect_matting_failures.py` | **新增** |
| MODNet 兜底 | `skills/asset-renderer/matting_modnet.py` | **新增** |
| 依赖安装 | `skills/asset-renderer/setup_matting_env.sh` | **新增**（torch venv 隔离） |

## 6. 性能（NRBI 全本 350 sprite）

| 阶段 | 当前 | 实施后 |
|---|---:|---:|
| Layer 6 cutout | ~60s | ~60s（备份多几秒） |
| Layer 8 green_spill | ~10s | ~10s |
| Layer 9 detect | — | ~30s |
| Layer 10 MODNet on ~10% fail | — | ~3min |
| **总计** | **~70s** | **~5min** |

加 ~4 分钟换「绿衣 / 黑衣 chromakey 翻车自动修复」+ 详尽决策日志。一次性 setup ~60s（torch + MODNet ckpt 下载）。

## 7. YAGNI 边界（不做的事）

| | 不做的事 | 理由 |
|---|---|---|
| 1 | Real-ESRGAN ×4 → ÷2 upscale | 对识别能力无影响；下游契约会破 |
| 2 | Pixel-level A/B merge | 复杂度高，A B 边缘风格不同，merge 易劣化 |
| 3 | retroactive 重渲已有 NRBI sprite | scope 外，独立任务 |
| 4 | 一键 orchestrator 命令 | 4 个独立 CLI 已足 |
| 5 | 颜色直方图预筛选（输入侧） | detector 后置审计已够 |

## 8. 引用资源

- 实验对比图：`/tmp/matting_compare/v2/compare_final_AB.png` + `~/Desktop/matting_AB/`
- 原始 zip：`~/Downloads/generate-upscale-matting.zip`（来自 Dramatizer-MSS sister 项目）
- [MODNet (ZHKKKe)](https://github.com/ZHKKKe/MODNet) - AAAI 2022, Apache 2.0, 26MB ckpt
- [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.2.5.0) (本 spec scope 外)

## 9. 状态

- 2026-05-06 design spec 写完 + ingest 入 wiki
- 下一步：`superpowers:writing-plans` 出实施 plan，TDD 落地
