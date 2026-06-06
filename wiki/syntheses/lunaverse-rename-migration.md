---
title: Lunaverse 全量改名迁移方案（moonshort → Lunaverse / MSS → Lunascripts / .mss → .ls）
tags: [rename, migration, lunaverse, lunascripts, decision-record]
sources: [raw/2026-06-06-lunaverse-rename-recon.md]
created: 2026-06-06
updated: 2026-06-06
---

本页是 "moonshort → **Lunaverse**"、"MSS（MoonShort Script）→ **Lunascripts**，扩展名 `.mss`/`.mss.md`/`.md` → **.ls**" 全量改名的执行方案与建议。改名横跨 **9 个独立 git 仓库**、约 **1 万处字符串占用** + **~575 个脚本文件需物理改名**，且文件扩展名当前是「三套并存」。本方案的核心主张：**把改动分成"安全文本层"与"高危身份/状态/契约层"两类，前者机械批量、后者带兼容垫片分阶段切换，外部平台身份默认保留为 legacy、但携带旧名的仓库全部改名**。证据见 [source](../raw/2026-06-06-lunaverse-rename-recon.md)。

## 1. 命名映射总表（替换的唯一真相）

| 旧 | 新 | 适用范围 |
|---|---|---|
| `MoonShort` / `Moonshort` / `moonshort`（项目、平台、品牌） | **Lunaverse** | 人可见品牌、显示名 |
| `moonshort`（小写 slug / 标识符） | **lunaverse** | 代码标识符、命名空间、目录 slug |
| `MoonShort Script` / `MSS`（语言/格式名） | **Lunascripts** | 语言名、文档、aliases |
| `MSS` / `mss`（缩写，作标识符前缀如 `mssUrl`） | **LS** / `ls`（`lsUrl`） | 代码标识符缩写 |
| `.mss` / `.mss.md` / `.md`(作脚本) | **.ls**（三端统一） | 规范扩展名；预览时手动加 `.md` 成 `.ls.md`，编译器仍接受 |
| `moonscripts/`（内容根目录） | **lunascripts/** | 内容根、OSS 路径段 |
| `mss`（Go CLI 二进制名） | **lsc**（见 §4 决策 D4，**不要用 `ls`**） | 命令名 |
| `cdotlock/moonshort-ide` | **cdotlock/lunaverse-ide** | repo + Go module + 本地目录 |
| `cdotlock/moonshort-script` | **cdotlock/lunascripts**（见 D2） | repo + Go module + 二进制 |
| `cdotlock/moonshort-backend` | **cdotlock/lunaverse-backend** | repo（本地目录仍叫 backend） |
| `AugustZAD/Dramatizer-MSS` | **AugustZAD/dramatizer-ls** | repo + 本地目录 |
| `Rydia-China/moonshort` | **Rydia-China/lunaverse-client** | repo + 本地目录（去空格），详见 §3.5 |
| `packages/mss-*`（IDE 6 包） | `packages/ls-*` | 包目录 + 包名 |
| `skills/mss-*`（backend 5 技能） | `skills/ls-*` | 技能目录 + SKILL.md `name:` + Langfuse 名 |

> 缩写用 `ls` 还是 `lunascript`？建议：**代码标识符用 `ls`**（短、与 `.ls` 一致），**人可见文档/类名用 `Lunascript(s)`**。

## 2. 改动分两类（决定"怎么切"的根本原则）

**A 类 — 安全文本层（机械批量，仓库本地，不需协调）**：品牌字串、UI 文案、注释、README/文档、纯代码标识符。改错了顶多编译报错或显示不对，可见、可回滚。
**B 类 — 高危层（必须带兼容/迁移，常需跨仓或外部协调，会"静默失败"）**：① 文件扩展名 + 物理文件；② App/包身份（bundle id、包名、Go module）；③ 持久化状态（DB 列、存档 JSON 键、localStorage、用户设置）；④ 外部耦合（域名、URL scheme、API 路由、env var、OSS bucket、Firebase、Railway）；⑤ 仓库/目录名。

A 类怎么做都行；**所有风险都在 B 类**。下面 §3 专讲 B 类。

## 3. 高危项（B 类）逐项策略

### 3.1 文件扩展名 `.ls`（全项目最易踩坑）
现状三套并存（详见 [recon §2](../raw/2026-06-06-lunaverse-rename-recon.md)）：IDE 用 `.mss`、编译器只认 `.md`、backend 生产内容是 `.mss.md`（263 个）。统一到 `.ls` 必须**同时**改：
- 编译器入口 `moonshort-script/cmd/mss/main.go:243` 的 `HasSuffix(".md")`；decompiler 输出 `decompiler.go:132,140` 的 `".mss.md"`；`api_server.py:190` 的收文件判断。
- IDE 语言注册 `mss-lang/package.json`（`.mss`/`source.mss`/`onLanguage`/`workspaceContains`）+ `mss.tmLanguage.json` 全部 scope 名 + `mss-studio` 的 `filenamePattern`。
- dramatizer-mss `compile_mss.py:78` 的 `glob("*.md")`。
- 物理改名 ~575 个脚本文件（backend 263 `.mss.md` + dramatizer 336 `.md` + IDE fixtures + moonshort-script testdata）。

**已定方案（三端统一到 `.ls`，编译器一起改）**：编译器（含 `moonshort-script/cmd/mss/main.go:243` 的 `.md` 判断）、IDE、生产管线全部以 `.ls` 为规范扩展名；decompiler 默认输出从 `.mss.md` 改为 `.ls`。
- **预览用 `.ls.md`**：内容本就是 markdown 编码，谁要用 GitHub/编辑器预览，自己把文件加个 `.md` 成 `name.ls.md` 即可；**编译器同时接受 `.ls` 与 `.ls.md`**（剥掉尾部 `.md`），所以预览命名的文件照样能编译。IDE 只注册 `.ls`，`.ls.md` 在 IDE 外按 markdown 渲染——这正好取代旧的 `.mss.md`，方向反过来（默认 `.ls`、按需加 `.md`）。
- **切换法（带兼容窗口）**：① 编译器/IDE/管线先同时接受 `.ls` + `.ls.md` + 旧后缀（`.md`/`.mss.md`/`.mss`）；② `git mv` 批量改 ~575 文件到 `.ls`、默认产出翻到 `.ls`；③ 全链路（编译→播放→快照测试）跑绿后，移除对旧后缀的接受（**保留 `.ls.md` 预览支持**）。

### 3.2 App/包身份
- **macOS bundle id `com.moonshort.ide` / Windows AppUserModelId / MSI GUID / `win32MutexName` / `dataFolderName .moonshort-ide`**：改 bundle id = 对用户变成**新 app**（孤立旧设置、断自动更新、断文件关联）；改 mutex 名会**多开实例并存→数据损坏**。**建议默认保留**，只改显示名（`nameShort/nameLong`、菜单、关于）。若坚持改，必须出**迁移构建**：读旧 `.moonshort-ide` userData → 迁到新目录；并接受一段时间双 URL scheme。
- **Android bundle id `com.mobai.moonshort` + Firebase 项目 `moonshort-1`**：受 Google Play / Firebase 控制台控制，改 = 重新注册 + 新签名 + 新 `google-services.json` + 数据迁移。**强烈建议保留为 legacy**，只改显示名。
- **npm 包名**（`moonshort-ide`、`@moonshort-ide/*`、`@moonshort/mob-agent-foundation`、cocos `moonshort`）与 **IDE 扩展 `publisher: moonshort`**：内部未发布的可随仓库改；已发布/被 workspace 引用的要同步所有引用方。
- **Go module `github.com/cdotlock/moonshort-script` / `.../moonshort-ide/minigamectl`**：改 module path 要同步**所有 import + 所有 vendored 副本 + `lsp-server/go.mod` 的本地 replace**，否则 build 挂。建议与 GitHub repo 改名放同一个窗口做。

### 3.3 持久化状态（绝不原地改，走增量迁移）
- **Prisma 列 `Episode.mssUrl`/`mssAssetId`**：参照本团队 [[concepts/railway-production-deploy]] 的 **additive-only 零删库 cutover**——加 `lsUrl`/`lsAssetId`、双写、回填、确认后再删旧列。**不要**在生产 rename-in-place。
- **存档 JSON 键 `mssKey` / 会话 `san` 槽位**（`attribute-slots.ts`/`save-service.ts`）：键名写进了玩家存档；改名要么保留旧键、要么写存档迁移脚本，否则旧档读不出。
- **localStorage 前缀 `moonshort_`**（cocos `AppSession.ts`）：客户端启动时做一次 `moonshort_* → lunaverse_*` 键迁移。
- **VS Code 配置键 `moonshort.*`**：扩展激活时迁移 `moonshort.* → lunaverse.*`（或读时双键兜底），否则用户丢 API key/路径设置。

### 3.4 外部耦合
- **API 路由 `/api/internal/compile-mss`、`/decompile-mss`**：先**新增** `/compile-lunascript` 并让旧路由 alias 转发 → 迁调用方（dream-agent/admin/测试）→ 再下线旧路由。
- **env var**（`MSS_API_*`、`MOONSHORT_*`、`R2_BUCKET`、`POSTGRES_DB`、`MSS_PATH`、`MOONSHORT_SCRIPT_DIR`）：代码读新名、`os.environ.get(NEW) or get(OLD)` 兜底一段时间，再清旧名。
- **域名 `gateway.moonshort.com` / `app.moonshort.ai`**、**Railway 服务 `moonshort-script-production`**：属 DNS/Ops，需运维窗口；建议**最后做或保留**，与 repo 改名解耦。
- **OSS bucket `moonshort-resource` / R2 `moonshort` / OSS 路径段 `/moonshort-script/testdata/`**：bucket 改名通常不可逆/代价高；**建议保留 bucket 名**（它只是存储位置，不是品牌门面），只在新写入时用新前缀，或建镜像双写后切。快照测试里 baked 的 OSS 路径**随重新生成而变，不手改**。

### 3.5 仓库/目录名（用户已决定：携带旧名的仓库全部改名）
真实远端核验后，**5 个仓库的名字带 moonshort/mss，全部改名**；改名跨 **3 个 GitHub namespace**（cdotlock / AugustZAD / Rydia-China），注意各自访问权限：

| 当前远端 | 建议新名 | 本地目录 | 备注 |
|---|---|---|---|
| `cdotlock/moonshort-ide` | `cdotlock/lunaverse-ide` | moonshort-ide → lunaverse-ide | Go module `.../moonshort-ide/minigamectl` 同改 |
| `cdotlock/moonshort-script` | `cdotlock/lunascripts`（D2） | moonshort-script → lunascripts | Go module `github.com/cdotlock/moonshort-script` + 所有 import + vendored 副本 + `lsp-server/go.mod` 本地 replace |
| `cdotlock/moonshort-backend` | `cdotlock/lunaverse-backend` | backend（本地目录不带旧名，可不动） | 文档/CLAUDE.md 里 "moonshort-backend" 字样同改 |
| `AugustZAD/Dramatizer-MSS` | `AugustZAD/dramatizer-ls` | dramatizer-mss → dramatizer-ls | 保留 dramatizer 品牌、去 -mss |
| `Rydia-China/moonshort` | `Rydia-China/lunaverse-client` | "moonshort cocos client" → lunaverse-cocos-client | repo 名直接叫 moonshort；改名需 Rydia-China org 权限；本地目录顺手去空格 |

**不带旧名、需你确认是否一并改的 4 个仓库**（携带的是 MobAI 公司品牌或通用名，不是 MoonShort）：`cdotlock/assets-produce`、`AugustZAD/Dramatizer`、`cdotlock/mob-mini-agent`、`cdotlock/mobai-agent`。默认**不改**（mob* 是 MobAI 公司品牌，与本次 MoonShort→Lunaverse 是两个轴）。

通用规则：
- 逐仓改、各自 commit/push；顶层 `/Users/Clock/moonshort/` **不是** git 仓，没有"一把梭"。
- GitHub repo 改名会自动留旧名 301 重定向，但**本地 remote URL + Go module path + 跨仓引用（Railway 服务名 `moonshort-script-production`、GitHub mirror 链接、CI）要手动更新**，否则 build/部署挂。
- 目录/文件一律 `git mv` 保历史。

## 4. 执行前必须拍板的决策（建议默认值已给）

- **D1（部分已定）仓库名 = 改；外部平台身份 = 建议保留。** 用户已决定**所有携带旧名的仓库全部改名**（见 §3.5 表）。其余外部不可变身份（macOS/Android bundle id、Firebase `moonshort-1`、OSS/R2 bucket、域名、Railway 服务名）**建议仍保留为 legacy，只改显示名**——改动代价是"用户数据迁移 + 商店/平台重注册 + 运维窗口"，与品牌收益不成比例。**待确认**：§3.5 里 4 个不带旧名的仓库（assets-produce / Dramatizer / mob*）是否也改。
- **D2 语言仓库 `moonshort-script` 叫什么？** 建议 **`lunascripts`**（与语言名一致、最干净）；备选 `lunaverse-script`（与 `lunaverse-ide` 成系列）。**二选一会改动所有 Go import + OSS 路径，需先定。**
- **D3（已定）扩展名三端统一到 `.ls`**，编译器一起改；不丢预览——按需手动加 `.md` 成 `.ls.md`，编译器仍接受。详见 §3.1。
- **D4 CLI 二进制 `mss` → ?** 建议 **`lsc`**（lunascript compiler）。**不要用裸 `ls`**（与 Unix `ls` 冲突）。
- **D5 backend 的 "Noval" 品牌是否一并改？** "Noval" 与 "MoonShort" 是两个品牌；本次指令只点名 MoonShort。**建议默认：Noval 不在本次范围**（DB `noval_demo`、CLI `noval`、容器 `noval-*` 保留），除非另行确认。
- **D6 代码缩写用 `ls` 可接受吗？** 建议接受（`mssUrl→lsUrl`、`scan_mss→scan_ls`、`compile_mss→compile_ls`）。

## 5. 推荐执行顺序（按"先安全、后高危、带兼容"分阶段）

> 每个阶段在**每个仓库内**用**原子提交**，按全局规则 push 到各仓 main（IDE 仓有专属分支约定，见其 CLAUDE.md）。先定 §4 决策再开工。

- **Phase 0 决策冻结**：拍板 D1–D6，锁定 §1 映射表。
- **Phase 1 安全文本层（A 类，可并行所有仓）**：品牌字串、UI 文案、注释、README/docs 的 `MoonShort→Lunaverse`、`MSS→Lunascripts`。不碰扩展名/身份/键名。零协调、可立即上。
- **Phase 2 仓库内代码标识符（A 类，逐仓）**：`moonshort→lunaverse`、`mss→ls` 标识符；IDE `packages/mss-*→ls-*`、backend `skills/mss-*→ls-*`（含 SKILL.md `name:`、测试断言、Langfuse 名）。
- **Phase 3 扩展名统一（B 类①，跨仓协调）**：编译器/IDE/管线**先双收** `.ls`+旧 → `git mv` 物理改名 ~575 文件 + `moonscripts/→lunascripts/` → 全链路跑绿 → 去旧后缀接受。
- **Phase 4 跨仓契约（B 类②④，一个窗口内）**：Go module path、CLI 二进制名、API 路由 alias、env var 兜底、npm 包名 + 引用方；GitHub repo 改名同窗口做。
- **Phase 5 持久化迁移（B 类③，按 additive-only）**：DB 加列双写回填、存档/ localStorage / VS Code 设置迁移脚本。生产参照 [[concepts/railway-production-deploy]] / [[concepts/supabase-backend-bootstrap]]。
- **Phase 6 外部身份（B 类，仅当 D1=改）**：bundle id / Firebase / 域名 / bucket，需 Ops + 商店协调，放最后；IDE 改身份后要重打 `.app`（≈20 分钟，且安装路径 `/Applications/Moonshort IDE.app` 与扩展目录名都变）。
- **Phase 7 知识库自身**：见 §7。

## 6. 提醒：所有东西怎么切 + 容易静默失败的点

1. **逐仓操作**：9 个 git 仓各自改、各自 commit/push；顶层目录非 git，无单次全局提交。
2. **一律 `git mv`** 改文件/目录名以保留历史，尤其 ~575 个脚本与 `moonscripts/`。
3. **不要 naive `sed -i`**：排除 `node_modules/.git/dist/build/.next/out/__pycache__/.venv/vendor/*.lock/*.map`；用 `\bmss\b` 与 `\.mss` 限定词边界，避免误伤英文单词/URL/GUID 里的 `mss` 子串；`moonscripts` 要整体改成 `lunascripts`（不是把 "moonshort" 抠出来）。
4. **不要动 MSS 指令词汇**：`@episode/@choice/@gate/@signal/@affection/@butterfly/@cg/@minigame` 是语言语义，不是品牌；改了破坏所有现存脚本。
5. **带兼容窗口的项**：编译器双收扩展名、env var 双读、API 路由 alias、URL scheme 双注册、DB additive 双写、设置/存档迁移——都遵循"先加新、跑绿、再删旧"。
6. **会静默失败的清单**：扩展名漏改 → 编译器扫不到 / 高亮失效；Go module path 漏改 → vendored 副本 build 挂；存档键 `mssKey`/`san` 改了无迁移 → 旧档读不出；技能目录改了但 Langfuse 名 / 测试断言没同步 → agent 取不到技能；快照 JSON 里 OSS 路径手改 → 快照测试挂。
7. **测试同步**：fixture 改名、硬编码技能名断言、含 OSS 路径的快照——随改名一起更新或重新生成。
8. **Langfuse 重传**：backend dream-agent 技能改名后需用新名重新上传。
9. **顺手收益**：`moonshort cocos client` 去空格；三套扩展名收敛成一套。

## 7. 这份知识库（mob-wiki）本身也在范围内

wiki 里这些页**文件名与内容都含旧名**，改名时要同步（建议 Phase 1 一起做）：
- 实体页：[[entities/moonshort-script]]、[[entities/moonshort-ide]]、[[entities/moonshort-backend]]、[[entities/moonshort-client]]、[[entities/dramatizer-mss]]、[[entities/mobai-agent]]（描述含 "Moonshort platform"）。
- 概念页：[[concepts/mss-format]]、[[concepts/mss-spec-redesign-2026-06]]、[[concepts/moonshort-ide-ai-integration]]、[[concepts/signal-int-backend]]、[[concepts/stable-step-id]] 等含 MSS/moonshort 的页。
- 综合页：[[syntheses/cloud-deployment-architecture]]（"How Moonshort transitions..."）。
- 改 wiki 页名会改变 `[[wikilinks]]` 与 `index.md` 条目，需一并更新（属 wiki lint 范畴）。

## Sources
- [2026-06-06 Lunaverse 改名勘察报告](../raw/2026-06-06-lunaverse-rename-recon.md)
- 相关：[[concepts/railway-production-deploy]]、[[concepts/supabase-backend-bootstrap]]、[[concepts/four-layer-philosophy]]
