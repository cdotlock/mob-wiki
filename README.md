# Mob-Wiki

Team knowledge base powered by LLM agents. Based on Karpathy's LLM-Wiki pattern.

Repo: https://github.com/cdotlock/mob-wiki

## Setup

    # 1. Clone
    git clone https://github.com/cdotlock/mob-wiki.git ~/mob-wiki
    cd ~/mob-wiki

    # 2. Install
    pip install -e .

    # 3. Configure
    cp .env.example .env
    # Edit .env and set OPENAI_API_KEY

    # 4. Run MCP server
    python server.py
    # MCP: stdio transport
    # HTTP: http://localhost:3141

## Claude Code Integration

Add to your Claude Code MCP settings:

    {
      "mcpServers": {
        "mob-wiki": {
          "command": "python",
          "args": ["/Users/YOU/mob-wiki/server.py"]
        }
      }
    }

Then append the rules block from SKILL.md to your ~/.claude/CLAUDE.md.

## Architecture

- `raw/` — Immutable source documents
- `wiki/` — LLM-compiled knowledge pages
- `schema.md` — Wiki structure rules
- `server.py` — FastMCP server (8 tools) + HTTP viewer
- `indexer.py` — SQLite FTS5 + embedding search index
