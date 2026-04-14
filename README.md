# Mob-Wiki

团队 LLM 知识库。基于 Karpathy LLM-Wiki 模式。

仓库: https://github.com/cdotlock/mob-wiki

## Setup（每人执行一次）

### 第 1 步：Clone + 安装

```bash
git clone https://github.com/cdotlock/mob-wiki.git ~/mob-wiki
cd ~/mob-wiki
pip install -e .
```

### 第 2 步：注册 MCP Server

```bash
claude mcp add -s user mob-wiki -- python ~/mob-wiki/server.py
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
cd ~/mob-wiki && python server.py
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
