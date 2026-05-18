---
title: assets-produce ↔ Moonshort IDE 工作区契约
tags: [assets-produce, moonshort-ide, mapping-json, asset-pipeline, contract]
sources: []
created: 2026-05-18
updated: 2026-05-18
---

Moonshort IDE 通过**打开一个本地工作区文件夹**消费 assets-produce 产物。本页定死 assets-produce 必须保证什么，IDE 才能正确认素材。配套设计文档:assets-produce 仓库 `docs/superpowers/specs/2026-05-18-assets-produce-ide-workspace-contract.md`。

IDE 内部 AI 架构(Cline / Tab 补全)见 [[concepts/moonshort-ide-ai-integration]];素材解耦原则见 [[concepts/mss-format]];项目实体见 [[entities/assets-produce]]。

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
├── <script>.md             # MSS 剧本
├── <script>_output.json    # MSS 编译产物
└── README.md
```

## 四条硬规则

1. **`mapping.json` 是唯一契约**:IDE / MSS 解释器只认它,不扫文件夹。schema 以 IDE 实际解析代码为准。
2. **`assets/` 按 kind 分子目录**:给「用户手动上传素材」一个一眼就懂的入口(决策 B)。
3. **任何新素材自动登记进 `mapping.json`**:agent 生成的、用户手动丢进 `characters/` 的,都必须自动写 mapping 条目。**make-or-break。**
4. **取素材走 mapping 解析,`loc` 可本地路径可 OSS URL**:禁止写死「永远读 `./assets/*`」。守此 → 本地/远程同一套,上云零返工。

## 静默失败 bug 类(为什么规则 3 不可省)

漏登记 = 文件在、IDE/MSS 看不见 → 编译期静默跳过或渲染期 404,整段戏丢失且**不报错**。MSS wiki 有真实 bug 史(`MRS. KING:` 标签失配 → 8 条 dialogue 静默丢;`@mama_reyes` 无 mapping 键 → 编译静默忽略)。这是反复出现的同构 bug 族,自动登记是唯一根治。

## 不在 assets-produce 职责内

- 跨机器 / CLI Gateway:现在不碰;能力已在代码,真要远程再启用。
- Notion 同步:IDE 侧 pipeline gate 的自动推钩子(只读镜像、无人手填),不是 assets-produce 的事。
- IDE 本体:独立项目(`moonshort-ide` 仓库)。

## 相关

- [[concepts/moonshort-ide-ai-integration]] — IDE 内部 AI 架构
- [[concepts/mss-format]] — MSS 素材解耦原则(设计原则 #4)
- [[entities/assets-produce]] — 项目实体
