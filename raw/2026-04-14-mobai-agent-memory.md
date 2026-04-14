# Memory

## Platform Locations

- **Dramatizer**: `/Users/Clock/dramatizer/` — Go binary at `./dram`, MCP via `dram mcp`, 小说→互动剧本 15 阶段管线
- **Agent-Forge**: `/Users/Clock/video-loop/Agent-Forge/` — Next.js port 8001, MCP at `/mcp`, 剧本→视频
- **Backend**: `/Users/Clock/moonshort backend/backend/` — Next.js port 3000, CLI at `cli/bin/noval.ts`, 游戏引擎+管理后台
- **Moonshort Client**: `/Users/Clock/moonshort backend/moonshort/` — Cocos Creator 3.8.8, headless 测试 at `test/`
- **mobai-agent**: `/Users/Clock/moonshort backend/mobai-agent/` — 本 Agent

## MCP Connections

- agent-forge: 48 tools (HTTP StreamableHTTP)
- dramatizer: 12 tools (stdio)

## CLI Tools

- `dram` — Dramatizer CLI (`/Users/Clock/dramatizer/dram`)
- `noval` — Backend game CLI (`cd backend && npx tsx cli/bin/noval.ts`)
- Moonshort AutoPlayer — `cd moonshort/test && npx tsx --tsconfig tsconfig.test.json play.ts`
- Moonshort Tests — `cd moonshort/test && npx tsx --tsconfig tsconfig.test.json run-tests.ts` (49/49)

## Key Facts

- LLM: Claude Sonnet 4.6 via Anthropic API
- Backend DB: PostgreSQL at localhost:5432 (Docker: noval-db-dev), seeded with novels #25, #26, #28
- Dramatizer DB: SQLite (已 migrate)
- Agent-Forge DB: PostgreSQL (Docker 同实例, database: agent_forge)

## Agent-Forge Dynamic MCP — Sandbox 规范


## Agent-Forge Dynamic MCP — Sandbox 规范

### 关键发现（E2E 测试 2026-04-13）

**Sandbox 使用 QuickJS (quickjs-emscripten)，代码必须用 CommonJS `module.exports` 格式：**

```js
// ✅ 正确写法
module.exports.tools = [
  {
    name: "my_tool",
    description: "...",
    inputSchema: { type: "object", properties: { ... } }
  }
];

module.exports.callTool = async function(name, args) {
  if (name === "my_tool") {
    return { content: [{ type: "text", text: "result" }] };
  }
  throw new Error("Unknown tool: " + name);
};
```

**❌ 错误写法（会导致 callTool failed in sandbox）：**
- 直接 `function listTools() {}` + `async function callTool() {}` — sandbox 找不到导出
- `return "string"` — 虽然 sandbox 会 wrap 成 content，但实测仍报错
- `return { key: value }` 对象字面量 — 在错误的导出格式下无效

**Sandbox 内置全局变量：**
- `console.log/warn/error` — 输出到宿主 `[sandbox:name]` 前缀日志
- `fetch` / `fetchSync(url, options)` — 同步 HTTP，返回 `{ status, body, ok, json(), text() }`
- `getSkill(name)` — 读取 Agent-Forge skill 内容
- `callToolSync(name, args)` — 调用其他已注册 MCP 工具
- **没有** `JSON` 全局对象（QuickJS 沙箱限制）→ 用字符串拼接或 `fetchSync` 返回的 `.json()` 方法

**callTool 返回格式必须是 MCP CallToolResult：**
```js
{ content: [{ type: "text", text: "..." }] }
```

**MCP 工具调用方式（从 mobai-agent 侧）：**
```
agent-forge_mcp_manager__use { provider: "my-mcp", tool: "tool_name", args: {...} }
```
注意：tool 名称不带 provider 前缀（不是 `my-mcp__tool_name`，就是 `tool_name`）。

**video_mgr 工具调用同理：**
```
agent-forge_mcp_manager__use { provider: "video_mgr", tool: "generate_image", args: {...} }
```
不是 `video_mgr__generate_image`。

