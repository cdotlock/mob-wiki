---
title: Style prompts → Langfuse 权威源迁移（2026-06-02）
updated: 2026-06-02
---

# Style prompts → Langfuse migration

把 NRBI 渲染管线的 **16 个 style_config 风格 family** 从「三处碎片化」迁成 **Langfuse 单一权威源**，并在 Lunaverse IDE 里做成完整的 CRUD 管理面板。是 [[concepts/assetctl-skills-sync-and-staging]]（skill 正文 → Langfuse）的**风格侧同构**：skill 用 `skill_<name>`，style 用 `style_<name>`，同一个 `assets-produce` project。

完整设计 + 实测修正：lunaverse-ide 仓 `docs/design/2026-06-02-style-system-langfuse-migration-design.md`。

## 迁移前的碎片化

同一份「风格」散在四处，互不一致：
- **style_config 表 / `styles.json`** — `render_all.py` 真正读的渲染数据源（16 family，含各 `-scene`/`-outfits`/`-edit` 变体）。
- **style-prompts MCP**（`korean-manga-style` 8 条细分 prompt）— asset-prompt-generator agent skill 用的**另一层**（不同 model 体系 nano-banana、动态 reference 路由、character|scene enum）。
- **IDE `nrbi-styles.json`** — host 的本地兜底 catalog。
- **IDE `langfuse-prompts.ts`** — 半成品 Langfuse reader，硬编码 5 个**不存在**的占位 prompt 名 + **没设 User-Agent**，所以从来没真连上过，永远静默回退本地。

## 四条锁定决策

1. **后台权威源 = Langfuse**（`prompt.mobai-game.com`，project `assets-produce`）。
2. **彻底切换**：Python 渲染管线也直接读 Langfuse，render 侧 `styles.json` 降为应急兜底。
3. **IDE 完整 CRUD + sync**：查看/编辑/新建/归档、改 model、参考图上传 R2、版本历史 + 回滚，编辑后 sync 到 Langfuse，promote production 前过结构 lint 闸。
4. **数据范围 = 只迁 16 个 family**。`korean-manga-style` MCP 那 8 条细分 prompt 是独立层，**本次不迁、不动**（列为 follow-up）。

## 实测硬约束（踩过的坑，务必记住）

- **Cloudflare 1010**：`prompt.mobai-game.com` 在 CF bot 防护后，**每个请求必须带 User-Agent**（urllib 默认 UA 被 1010 拦）。既有 Go 客户端 `vendor/assetctl/internal/skills/langfuse.go` 用 `assetctl-skills/0.1`；本次 TS/Python 客户端统一用 `lunaverse-ide-styles/0.1`。
- **真凭据在 `assets-produce/.env`**（`pk-lf-338a…`）。`lunaverse-backend/.env` 的 `LANGFUSE_*` 是占位假值（`pk-lf-x`，len 9）→ 401。已把真 key 拷进（gitignored）`lunaverse-ide/.env`，host（`readDotEnv(root)`）和 render（`ENV_FILES`）都从这一处读。
- **命名 `style_<name>`**，对齐 `skill_<name>`；config 里放 `category/model/reference_urls/family/variant/placeholder/aspect/generated_preview_url`。render 只读 `prompt` + `config.reference_urls`，IDE 读其余 → 双消费方契约只共享这两项，防漂移。
- **参考图先 OSS→R2 镜像**（`mirror_oss_to_r2.py`，25 张）再 seeding，config 存 R2 URL，零 OSS 泄漏。

## 渲染侧三层兜底（永不 hard-fail）

`render_all.py` 的 `_load_styles()`：① Langfuse production（成功后原子写 cache）→ ② `styles-cache.json`（last-known-good，gitignored，自动刷新）→ ③ `styles.json`（最深静态兜底）。`STYLES_JSON=<path>` 是逃生舱强制本地。实测断网/缺凭据都正确降级。

## 六波实施（均已合 `feat/assetctl-foundation`）

| 波 | 内容 | commit |
|---|---|---|
| W1 | seeding 脚本 + 16 family 推 Langfuse production（参考图全 R2） | `91b3341` |
| W2 | IDE host 读路径重写（动态枚举 `style_*` + UA + 凭据接线） | `4ed828f` |
| W5 | Python render 读 Langfuse + 三层兜底 | `ff5d8f0` |
| W3 | host 写/sync/promote 闸/版本回滚/R2 上传 | `55603b8` |
| W4 | webview 完整 CRUD UI（StyleList/StyleDetail/SyncBar/VersionHistory/ReferenceManager） | `67b76f2` |
| W6 | styles.json 降级为应急快照（README）+ store CRUD 单测 | `fcf7ba1` / `7ad5ee2` |

验证：典型链路 IDE 改→Langfuse→render 生效已分段证；render `_load_styles` 实测 source=langfuse 取到 16 条 R2-ref；TS 788+12+7、Python 6 单测全绿。
