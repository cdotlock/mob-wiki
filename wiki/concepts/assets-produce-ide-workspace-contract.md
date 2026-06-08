---
title: assets-produce ↔ Lunaverse IDE 工作区契约
tags: [assets-produce, lunaverse-ide, mapping-json, asset-pipeline, contract]
sources: []
created: 2026-05-18
updated: 2026-05-22
---

Lunaverse IDE 通过**打开一个本地工作区文件夹**消费 assets-produce 产物。本页定死 assets-produce 必须保证什么，IDE 才能正确认素材。配套设计文档:assets-produce 仓库 `docs/superpowers/specs/2026-05-18-assets-produce-ide-workspace-contract.md`。

> **2026-05-22 状态更新**:`novels-to-lunascript` 和 `assets-produce` 两个上游仓库已冻结,所有 skill / CLI 都迁入 `lunaverse-ide` 仓库本身(详见下方 "IDE 自带 mapping-patch 工具" 段)。本页约束的"契约"现在由 IDE 内部脚本守。

IDE 内部 AI 架构(Cline / Tab 补全)见 [[concepts/lunaverse-ide-ai-integration]];素材解耦原则见 [[concepts/ls-format]];项目实体见 [[entities/assets-produce]]。

## 关键结论

配合 IDE 需要的能力 assets-produce 大部分已具备(REST Phase 8、oss-put Phase 12、素材编排 Phase 14)。**唯一必须保证的是工作区契约。** 文件夹只是字节放哪;`mapping.json` 才是机器认素材的依据。

## 工作区结构(依据 `feature_parade` demo 实测)

```
<workspace>/
├── .claude/
├── assets/
│   ├── characters/<name>/<look>.<ext>
│   ├── backgrounds/<name>.<ext>
│   ├── cg/<name>.<ext>
│   ├── music/<name>.<ext>
│   └── sfx/<name>.<ext>
├── mapping.json            # 唯一契约:name+kind → 位置
├── <script>.md             # LS 剧本
├── <script>_output.json    # LS 编译产物
└── README.md
```

## 四条硬规则

1. **`mapping.json` 是唯一契约**:IDE / LS 解释器只认它,不扫文件夹。schema 以 IDE 实际解析代码为准。
2. **`assets/` 按 kind 分子目录**:给「用户手动上传素材」一个一眼就懂的入口(决策 B)。
3. **任何新素材自动登记进 `mapping.json`**:agent 生成的、用户手动丢进 `characters/` 的,都必须自动写 mapping 条目。**make-or-break。**
4. **取素材走 mapping 解析,`loc` 可本地路径可 OSS URL**:禁止写死「永远读 `./assets/*`」。守此 → 本地/远程同一套,上云零返工。

## 静默失败 bug 类(为什么规则 3 不可省)

漏登记 = 文件在、IDE/LS 看不见 → 编译期静默跳过或渲染期 404,整段戏丢失且**不报错**。LS wiki 有真实 bug 史(`MRS. KING:` 标签失配 → 8 条 dialogue 静默丢;`@mama_reyes` 无 mapping 键 → 编译静默忽略)。这是反复出现的同构 bug 族,自动登记是唯一根治。

具体在角色立绘这一层,最常见的同构 bug 是:**05 episode-writer 写了 `@<char> show <look>` 或 `<CHAR> [look]:`,但 06 asset-prompt-generator 没枚举这个 `(char, look)`,mapping 不存在,引擎 lookup miss 保留前一帧**。NRBI / chaoreqi-idol 两本都中招过,见下一段。

## IDE 自带 mapping-patch 工具(2026-05-22 加入)

`agents/asset/skills/asset-prompt-generator/patch_mapping.py` 是 IDE 内置的 mapping 完整性自检工具,落点跟 `check_clothing_consistency.py` 并列,目的是把以下两种历史人工补丁通用化:

| 历史先例 | 做了什么 |
|---|---|
| **NRBI** | `compiled/mapping.json` 是手工 baked 的 frozen vendored artifact——某个时刻有人把 `look_alias_map.json` 摊平进 mapping,但脚本没沉淀到任一仓库 |
| **chaoreqi-idol** | 团队在 `_render/patch_mapping.py` 硬编码 15 个 supplementary look(suyongqing 7 + yunchen 8)+ `patch_mapping_aliases.py` 5 个中文 alias |

新工具的能力:

1. **扫描 + 对账**:walk `scripts/*.ls`,三种引用形式(`@char show` / `@char look` / `<CHAR> [look]:`)全部提取,跟 `mapping.assets.characters[char][look]` 比对
2. **分类**:`missing_sprite`(影响画面,退出 1) vs `missing_voice_tag`(`muffled` / `quiet_voice` / `warm_chuckle` 等启发式识别,引擎保留前一帧,信息性)
3. **`--apply`**:把缺失 sprite 写进 mapping,备份原版到 `mapping.pre-patch.backup.json`,**幂等**(再次 apply 不覆盖备份)
4. **`--aliases <json>`**:display 角色名→canonical(中文显示名),per-look alias(`waigong.warm_chuckle` → `waigong.warm_smile`),用户自定义 voice_tag tokens
5. **路径约定自动推断**:从 mapping 现有第一条 character entry 推 `(prefix, subdir, ext)`;`--oss-prefix` `--char-subdir` `--ext` 可覆盖
6. **CI 友好**:`--json` 输出机器可读,退出码 0(干净 OR apply 成功) / 1(dry-run 有 missing_sprite) / 2(环境错)

### 实战验证(2026-05-22 chaoreqi-idol 真本)

```
[patch_mapping] /Users/.../chaoreqi-idol/compiled/mapping.json
  refs=242  hits=212  missing_sprite=2  missing_voice_tag=2
  path convention: crqi/characters/<char>_<look>.webp

── MISSING SPRITE ──
  ✗ 苏咏晴.confident_smirk  (×3)        ← 团队漏渲
  ✗ 苏咏晴.fierce_protective  (×8)       ← 团队 patch_aliases 漏列中文 alias

── MISSING VOICE TAG ──
  ◦ 苏咏晴.muffled  (×1)                ← DELIVERY.md 已标注
  ◦ 苏咏晴.quiet_voice  (×18)            ← DELIVERY.md 只报了 4 次,实际 18 次
```

工具检出了 chaoreqi 团队手撸脚本**真实漏掉的 2 个问题** + 验证了 voice 标签分类正确。

### 使用流程

```bash
# 在 IDE 仓库根目录跑
python3 agents/asset/skills/asset-prompt-generator/patch_mapping.py \
    --book <slug> --root <path/to/book>        # dry-run 对账
python3 agents/asset/skills/asset-prompt-generator/patch_mapping.py \
    --book <slug> --root <path> --apply        # 实际写 mapping
python3 agents/asset/skills/asset-prompt-generator/patch_mapping.py \
    --book <slug> --root <path> --apply \
    --aliases <path/to/aliases.json>           # 配合显示名 / 跨语种 alias
```

详细 schema 与处理 finding 的标准动作见 `agents/asset/skills/asset-prompt-generator/SKILL.md` "## 06 收尾自检:mapping 完整性" 段。

## 不在 assets-produce 职责内

- 跨机器 / CLI Gateway:现在不碰;能力已在代码,真要远程再启用。
- Notion 同步:IDE 侧 pipeline gate 的自动推钩子(只读镜像、无人手填),不是 assets-produce 的事。
- IDE 本体:独立项目(`lunaverse-ide` 仓库)。

## 相关

- [[concepts/lunaverse-ide-ai-integration]] — IDE 内部 AI 架构
- [[concepts/ls-format]] — LS 素材解耦原则(设计原则 #4)
- [[entities/assets-produce]] — 项目实体
