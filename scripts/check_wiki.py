"""Exercise the actual stdio MCP server; exit nonzero on structural issues."""

import asyncio
import json
from pathlib import Path
from fastmcp import Client


async def main():
    async with Client(Path(__file__).resolve().parents[1] / "server.py") as client:

        async def call(name, arguments):
            result = await client.call_tool(name, arguments)
            data = result.structured_content or json.loads(result.content[0].text)
            if result.is_error or "error" in data:
                raise RuntimeError(data)
            return data

        index = await call("wiki_list", {})
        if "Mob-Wiki" not in index["index"]:
            raise RuntimeError("Wiki index missing")
        await call("wiki_read", {"path": "wiki/index.md"})
        search = await call("wiki_search", {"query": "Lunaverse"})
        if not search["results"]:
            raise RuntimeError("Search returned no results for a known project")
        lint = await call("wiki_lint", {})
        print(json.dumps(lint, ensure_ascii=False, indent=2))
        if lint["issues"]:
            raise SystemExit(1)


asyncio.run(main())
