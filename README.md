# Mob-Wiki

团队 LLM 知识库。基于 Karpathy LLM-Wiki 模式。

仓库: https://github.com/cdotlock/mob-wiki

## Setup（每人执行一次）

### 第 1 步：Clone + 安装

```bash
git clone https://github.com/cdotlock/mob-wiki.git ~/mob-wiki
cd ~/mob-wiki
uv sync --python 3.12 --extra dev --frozen
```

### 第 2 步：注册 MCP Server

```bash
claude mcp add -s user mob-wiki -- "$HOME/mob-wiki/.venv/bin/python" "$HOME/mob-wiki/server.py"
```

`-s user` 将 wiki 注册为全局 MCP，在任何目录启动 Claude Code 都能使用 wiki 工具。之后每次对话 Claude 会自动启动 server，对话结束自动关闭。不需要手动挂后台进程。

### 第 3 步：追加全局规则

运行以下命令，把 wiki 规则写入你的全局 CLAUDE.md：

```bash
cat >> ~/.claude/CLAUDE.md << 'WIKI_RULES'

## Mob-Wiki 团队知识库

团队知识库位于 ~/mob-wiki（仓库 cdotlock/mob-wiki），已通过 MCP 注册。

### 强制规则

1. **查询优先**：被问到项目架构、设计决策、产品逻辑、历史上下文时，
   先调 wiki_list 看目录，再 wiki_read 读相关页面，最后回答。wiki 是 source of truth。
2. **写入优先**：产出任何 PRD、设计文档、技术方案、重大决策后，
   必须 wiki_ingest 入库。没入库 = 没做过。
3. **引用来源**：引用 wiki 内容时标注页面路径，方便用户查证。
4. **保持新鲜**：工作中发现 wiki 内容过期或有误，立即 wiki_update_page 更新。
5. **写前同步**：写 wiki 前先在 ~/mob-wiki 执行 git pull，避免冲突。

### 不用 wiki 的场景

- 一次性调试问题，无复用价值
- 代码级实现细节（代码库本身就是文档）
- 个人笔记或对话临时上下文
WIKI_RULES
```

完成！现在你的 Claude Code 每次对话都会遵循这些规则。

## 日常使用

配置完成后**零操作**。正常和 Claude Code 对话即可：

- 问项目问题 → Claude 自动查 wiki 后回答
- 产出文档 → Claude 自动入库
- 说"lint wiki" → Claude 自动检查健康度

唯一需要偶尔做的：`cd ~/mob-wiki && git pull` 拉别人的更新。

## 浏览 Wiki（可选）

**方式 1：GitHub 网页** — 直接在 GitHub 上看 wiki/ 目录下的 Markdown 文件

**方式 2：本地 HTTP** — 临时启动查看器：

```bash
cd ~/mob-wiki && uv run --frozen python server.py --http
# 然后访问 http://localhost:8787
```

## 架构

```
mob-wiki/
├── raw/          # 不可变源文档（丢进来的原始文件）
├── wiki/         # LLM 编译的知识页（自动维护）
│   ├── index.md  # 分层目录索引（核心导航）
│   ├── log.md    # 操作日志
│   ├── concepts/ # 概念页
│   ├── entities/ # 实体页
│   └── syntheses/# 综合分析页
├── schema.md     # Wiki 结构规范（LLM 写页面时的规则）
├── SKILL.md      # 详细操作流程（ingest/query/lint 工作流）
├── server.py     # MCP Server（8 个工具）+ HTTP 查看器
└── indexer.py    # SQLite FTS5 搜索索引
```

## 团队重新启用

修复与后续优化见 [2026-09-14 审核记录](docs/audit-2026-09-14.md)。

需要 Python 3.11+ 和 uv。已有成员先在自己的副本执行 `git status`，保存自己的改动后执行 `git pull --ff-only`，再运行上面的 `uv sync`。不要使用系统自带的 Python 3.9。安装是每位成员自己的本地配置；仓库更新不会自动替成员注册 MCP。

MCP 默认只提供 stdio 工具，不启动网页端口。`--http` 提供独立浏览器进程；`WIKI_HTTP_PORT` 可覆盖 8787。确需同一进程同时提供两种入口时设 `WIKI_HTTP_ENABLED=1`。默认知识库根目录是 `server.py` 所在目录，从其他项目启动也会读取正确资料；自定义部署可通过 `WIKI_ROOT` 指向含 `wiki/` 和 `raw/` 的完整副本。查看器仅监听本机，不包含互联网服务的身份认证。

验证：

```sh
uv run --frozen --extra dev pytest -q
uv run --frozen python scripts/check_wiki.py
```

第二条会实际启动 MCP，验证列目录、读取、搜索和结构检查，结构错误时返回非零状态。资料新鲜度提醒需人工结合上下文判断，不阻止无关工作。CI 在提交和 PR 时执行同样的检查。

团队编辑时先拉取，调用 `wiki_read` 获得正文和 `revision`，更新时将该值传入 `wiki_update_page` 的 `expected_revision`。如返回冲突，重新读取并合并双方内容。旧客户端仍可省略此参数，但无法获得过期写入保护。Git 推送被拒绝时应取回远端变化并解决冲突，禁止强推覆盖他人的贡献。

搜索使用本地 SQLite FTS5 关键词匹配；中文词在 FTS 无结果时回退到子串匹配。没有向量语义搜索，也不需要模型 API key。每次搜索检测本地 Markdown 的新增、修改和删除，拉取更新后无需手工重建索引。

`updated` 是资料的历史更新时间，不能视为生产系统已重新核验的证明。空 `sources` 表示来源尚未补充。重新采用某条部署或产品决策前，应核对相关仓库和实际服务；尤其留意页面中的 `superseded`、`deferred` 和待上线记录。
