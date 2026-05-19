---
title: 中转站满血验机方法 + ECC 全局配置瘦身 playbook
updated: 2026-05-20
tags: [api-relay, model-verification, claude-code, ecc, cost-optimization]
---

# 中转站满血验机 + ECC 全局配置瘦身

两件事的实操沉淀(2026-05,august 机器)。

## 背景

- 中转站常谎称"满血 Opus"实则换 Sonnet/量化/套壳。需要可落地的验机手段。
- 顺带发现本机 ECC 全局 `~/.claude/rules/` 每会话注入 ~59k token,严重浪费。

---

## Part A — 中转站验机方法

### 分层策略(投产比从高到低)

1. **Tier 0 canary + 延迟节奏(首选,零成本,95% 场景够用)**
   - 7 道高区分度硬推理题(数字计数 / 9.11vs9.9 / 字母计数 / 亲属逻辑 /
     bat&ball / 机器问题 / 严格 JSON),有唯一答案,弱模型/量化版会翻车。
   - 同 prompt 流式跑 N 次,统计 TTFT / token 间隔 CV。
   - 脚本:`~/Desktop/opus_canary_check.py`(零依赖,支持 openai/anthropic
     两种 API 形态)。真满血 Opus 4.x 应 ≥6/7 且节奏稳。
2. **Tier 1 LLMmap**(`pasquini-dario/LLMmap`):无参照时判模型家族,
     但区分不了"满血 vs 量化同款 Opus",对中转站场景不对口。
3. **Tier 2 Model Equality Testing**(`i-gao/model-equality-testing`):
     双样本统计检验,抓最隐蔽的"真 Opus 但被量化/finetune"。
     脚手架:`~/Desktop/met-check/`(采集/检验解耦、可中断续采、HOWTO.txt)。
     **硬前提:必须有官方直连 Anthropic key 当参照**(公开数据集无 Claude)。

### 实测结论(2026-05-19)

| 端点 | canary | 模型回显 | 判定 |
|---|---|---|---|
| mob-ai `claude-opus-4-6:free` | 7/7 | claude-opus-4-6:free | 满血,free 无降级 |
| mob-ai `claude-opus-4-6` | 7/7 | claude-opus-4-6 | 满血 |
| ccdan.live | 复测干净 | **claude-opus-4-7** | 真 4.7,行为干净 |

三家粗粒度均无作假。

### 关键坑(务必记住)

- **ccdan.live 是 Claude Code 订阅型 key**:只认真·`claude` 客户端
  (白名单 + 疑似 JA3),手搓 HTTP 一律 `Client not allowed`。
  只能用 `claude -p` 打。
- **在 Claude Code 里套跑 `claude` 会继承父进程 `ANTHROPIC_*` 导致 401**
  → 必须 `env -i HOME=.. PATH=.. ANTHROPIC_BASE_URL=.. ANTHROPIC_AUTH_TOKEN=..`
  干净环境隔离。
- **ccdan 永不要用 MET**:claude_cli 每次拖 Claude Code 系统提示 ~81.5k
  cache 写入(实测 costUSD ~$0.52/次),750 次≈$394 + 烧订阅额度触发限流
  + 系统提示污染分布使检验无效。canary 已够。
- MET 成本(实测 token 锚定):裸 API 端默认量 30×25=750 次,官方参照侧
  仅 $1~3(假设 $5/$25~$15/$75 每 MTok)。先 `--samples 8` 冒烟 ~$0.1。

---

## Part B — ECC 全局配置瘦身

### 发现

- `~/.claude/CLAUDE.md` 本体仅 ~1k token(正常)。
- `~/.claude/rules/` 103 文件 ~59k token,**common 内容三重复**:
  `common/` + `zh/`(中文翻译副本)+ 扁平 `common-*.md`(README 警告的
  flatten 反模式);另有 12 语言目录 + web 全局无差别加载。
- 注入机制:Claude Code 原生把 `~/.claude/rules/**/*.md` 当全局 memory 扫
  (CLAUDE.md 无 @import、session-start.js 不注入 rules)。
  → **机制无关的安全做法:文件移出 `~/.claude/rules/` 即停止加载。**

### 已执行(2026-05-20,可回滚)

- 保留 DAILY:`rules/common/`(权威唯一,CLAUDE.md L58 引用)+ `README.md`
- 移到 `~/.claude/rules-library/`:`zh/`、扁平 `common-*.md`/`python-*.md`、
  12 语言目录 + `web/`
- 效果:每会话 rules 注入 **177,503 B → 21,713 B,省 ~52k token**
- 回滚:`bash ~/.claude/rules-library/ROLLBACK.sh`(全量还原)

### 正确姿势:语言规则跟项目走,不全局常驻

- 原理:Claude Code 原生 `@import`——项目根 `CLAUDE.md` 写 `@文件路径`,
  该规则只对这个项目生效。
- 一键脚本 `~/.claude/rules-library/use-rules.sh`:
  - `cd 项目 && bash ~/.claude/rules-library/use-rules.sh` — 自动识别栈
    (package.json/pyproject.toml/Cargo.toml/go.mod/pubspec.yaml…)并把对应
    语言规则 @import 写进该项目 `./CLAUDE.md`(ECC-RULES 管理区块,幂等)。
  - `--list` 只看识别;`use-rules.sh python typescript` 手动指定。
  - common/ 已全局常驻,不重复挂。
- **团队共享仓库**:脚本写绝对路径不可移植,改用
  `mkdir -p .claude/rules && cp -r ~/.claude/rules-library/<lang> .claude/rules/`
  并提交进 git,同事 clone 即得。

### 未处理(优先级低)

- skills(59)/agents(48) 仅注入 name+desc 元数据,体量次于 rules 三重复。
  要清是另一轮 `skill-stocktake` 的活。

---

## 关键文件清单

- `~/Desktop/opus_canary_check.py` — Tier0 验机(直连裸 API 端点)
- `~/Desktop/met-check/` — MET 脚手架(config.py / collect.py / run_test.py / HOWTO.txt)
- `~/.claude/rules/` — 瘦身后只剩 common + README
- `~/.claude/rules-library/` — 收纳的离栈/重复规则 + ROLLBACK.sh + use-rules.sh
