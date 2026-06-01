---
title: Second-Chorus 素材流水线（自包含 / 云端可跑 / 可复用模板）
updated: 2026-06-01
---

# Second-Chorus 素材流水线

一套**自包含、env 驱动、可断点续跑**的剧集素材生产流水线。从 06 资产清单出发，
端到端生成全部立绘/背景/音效 → 超分抠图 → 传阿里云 OSS → 产出 `mapping.json`
（素材名→OSS URL）。可在本机或 **Claude Code 云端 Routine** 跑。

代码在 `cdotlock/moonshort-ide` 仓库 `tools/second-chorus-pipeline/`，分支
`feat/assetctl-foundation`。后续换别的小说复用这套，主要换"输入源"，代码几乎不动。

## 全局数据流

```
小说原文
 └─【上游 authoring（dramatizer-mss，AI agent 生成，不在本流水线）】
      02 角色 bible（人设+服装） / 03 剧情结构 / 05 分集 MSS 脚本
      06 资产清单（从脚本抽取每个角色每表情一行 + 背景 + 音乐 + 音效）
        ├ 02-ep-character-sprites/ep-character-sprites.review.csv
        ├ 01-series-characters/series-character-prompts.md（角色 appearance）
        ├ 03-backgrounds/backgrounds.review.csv
        └ 90-review/asset_inventory.review.json（含 sfx buckets）
 └─【本流水线 tools/second-chorus-pipeline/】
      build_tasks.py  06 清单 → tasks.json（N 个渲染单元）
      normalize.py    （04）实体名归一化 + 对齐校验闸（见下）
      render_all.py   分阶段渲染（series→anchors→sprites→bg→sfx）
      finalize.py     收尾 → mapping.json（素材名→OSS URL）+ MORNING_SUMMARY.txt
 └─ mapping.json + 所有素材在 OSS
 └─【再下游，本轮未做】mss compile（脚本+mapping→episode JSON）→ 提交后端 → admin 上线
```

## 五个渲染阶段（render_all.py，严格按依赖顺序）

| 阶段 | 风格（styles 表 name） | 输入 | 产出 |
|---|---|---|---|
| ① series 底图 | `Webtoon_01` | 风格参考图 + 角色 appearance 文字 | 角色定妆照（身份锚），绿幕 |
| ② anchors 服装锚 | `Webtoon_01-outfits` | ①底图 + 服装文字 | 角色穿某套衣服 |
| ③ sprites 立绘 | `Webtoon_01-edit` | ②服装锚 + 表情/姿势文字 | 每个 beat 的立绘 |
| ④ bg 背景 | `YA_Impasto_scene`（无明确风格时的默认 bg 风格） | 场景文字 | 背景图，**不抠图（保持不透明）** |
| ⑤ sfx 音效 | ElevenLabs | 音效描述文字 | 音效 mp3 |

**每张图/立绘的子链**（assetctl 原子）：
`generate-image-gpt`（mob-ai 出图，绿幕）→ `process-cutout`（FC/Modal：2x 超分 + MODNet 抠图 → 透明 webp）→ `oss-put`（传 OSS，返回永久 URL）。
背景不同：`generate-image → upscale-image → 不抠图`。

**三层锁身份**：series→anchors→sprites 每层拿上一层当参考图，保证同角色几百张
立绘"同一个人、同一套衣服"。

## 关键设计

1. **断点续跑**：`state.json` 记录每单元状态，重跑跳过 `done`。
2. **风格走本地快照**：`style/styles.json` 是从风格服务器（`8.133.3.63` 的 PG `styles` 表）
   dump 的快照，打包进 repo，云端不连内网。换画风改这个文件 / 重 dump。Webtoon 家族 =
   `Webtoon_01` / `Webtoon_01-outfits` / `Webtoon_01-edit`；还有 Arcane / Kyoto_Animation / YA_Impasto。
3. **密钥全 env**：mob-ai 出图 / OSS / Modal(FC) 超分抠图 / ElevenLabs / Wavespeed —— 本机读
   `moonshort-backend/.env`+`moonshort-ide/.env`，云端读 Routine 环境变量。脚本自动把
   `MOB_AI_API_KEY` 映射成 assetctl 要的 `MOB_AI_KEY`。

## normalize.py（04 实体名归一化）

把"MSS 脚本 ↔ 06 清单 ↔ mapping"三者实体名对齐。**检测全机械、零 LLM，判定权在人**。

- `audit --scripts <脚本目录> --source <06目录>`：抽脚本所有实体引用（角色 look / @bg / @sfx /
  &music）+ 机械检测别名候选（大小写/下划线/前后缀包含/编辑距离1）+ 查"脚本引用 vs 06 清单"对齐缺口。
- `check --scripts --source`：对齐闸 —— 脚本每个引用必须在清单里有，否则非零退出（发布前/CI 闸）。
- `apply --scripts --alias-map <json> [--write]`：按人确认的 `alias_map.json`（别名→正名）
  **改写 MSS 脚本**用正名（即"标准名称替换回 mss"），默认 dry-run，`--write` 才改且备份 .bak。

注意：audit 的"前后缀包含"会把真·变体（`practice_room` vs `practice_room_a`、走廊白天/凌晨）
也列为候选 —— 这是预期噪音，人判为"不合并"即可，工具绝不自动合并。

## 云端 Routine 配置（claude.ai/code/routines）

> 建 Routine + 配密钥**只能在浏览器 UI**（API 不接受 env/network/setup 字段）；但
> 监控/拿结果走 git（云端把 state/mapping commit 回分支，`git fetch` 即可看进度）或
> `RemoteTrigger` API。详见 repo 内 `ROUTINE_SETUP.md`。

- **Repo**：`cdotlock/moonshort-ide`；prompt 里第一句 `git checkout feat/assetctl-foundation`
  （默认 clone main，但 assetctl 的 `process-cutout` 只在 feat 分支）。
- **Setup script**：只留 `#!/bin/bash` + `echo ok`。**不能在 setup 里跑 git/build** —— setup 在
  repo clone **之前**执行，git 操作会 `fatal: not a git repository` exit 128。build assetctl 交给
  prompt 阶段的 run.sh（那时已 clone+checkout）。
- **Network → Custom**，放行：`ai.mob-ai.cn`、`*.aliyuncs.com`、`*.modal.run`、`api.elevenlabs.io`，
  勾"默认包管理器"。
- **Env vars**：MOB_AI_API_KEY / OSS_*（6个）/ FC_PROCESS_*（超分抠图）/ FC_UPSCALE_IMAGE_* /
  ELEVENLABS_API_KEY / WAVESPEED_API_KEY。
- **Permissions**：开 "Allow unrestricted git push"（让它 commit 回 feat 分支）。
- **Trigger**：API（可手动 Run now）。

## 踩过的坑（务必记住）

1. **微信目录会被清**：素材/脚本第一件事是复制到稳定盘（仓库内），绝不在
   `xwechat_files/.../msg/file/` 里工作 —— 过夜被清光过一次。
2. **assetctl 返回信封是 `{"ok":true,"data":{...}}`**，URL 在 `data.oss_url` 或
   `data.assets[0].loc` —— 早期脚本读 `d["result"]` 全判失败、无限重试卡死。
3. **mob-ai 直连要带正常 User-Agent**（如 `curl/8`），否则 Cloudflare 403 / error 1010。
4. **ElevenLabs 免费层封数据中心 IP**：云端跑 sfx 全报 `detected_unusual_activity, Free Tier
   usage disabled`（额度没用完也封）。解法：本机跑 sfx（直连 200 正常）或升级付费层。视觉素材
   不受影响（走 mob-ai / Modal）。
5. **并发别开太大**：mob-ai 网关高并发会掐 TLS（SSLEOFError）。workers=8 稳妥，靠
   assetctl 内置重试 + 脚本 4 次退避双层兜底自愈。

## 换新小说怎么复用

1. 新小说重跑上游 02→06 authoring（dramatizer-mss），产出该剧 06 资产清单。
2. 把新剧 `06-asset-prompt-generator/` 放进 `source/`（或改 `SC_SOURCE_DIR`）。
3. `normalize.py audit` 看命名漂移 + 对齐缺口；有真别名就填 `alias_map.json` → `apply --write`。
4. 改 `build_tasks.py` 的 `SLUG`（OSS 路径前缀）；若角色清单完整删掉 `cha` 兜底。
5. styles 不动（除非换画风）。
6. 云端：复制现成 Routine，改 prompt 剧名，密钥/网络整套复用。
7. 跑：`build_tasks → normalize check → render_all（分阶段）→ finalize`。

## second-chorus 最终结果（2026-06-01）

617/617 全完成：12 series + 24 anchors + 435 sprites + 119 bg + 27 sfx，全部 OSS，
`mapping.json` 0 缺口（脚本↔素材名经 normalize check 验证对齐）。sfx 因免费层 IP 风控本机补跑。
关联：[[concepts/villain-season-demo]]、[[concepts/assetctl-integration-contract]]、
[[concepts/asset-matting-hybrid]]、[[concepts/production-pipeline-two-phase]]。
