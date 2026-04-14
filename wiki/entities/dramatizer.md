---
title: Dramatizer
tags: [go, cli, pipeline, llm, screenplay, mcp, interactive-fiction]
sources: [raw/2026-04-14-dramatizer-skill.md, raw/2026-04-14-mobai-agent-memory.md, raw/2026-04-14-cli-gateway-server-layer-design.md]
created: 2026-04-14
updated: 2026-04-14
---

Go binary that converts long novels into interactive mini-drama screenplays through a 15-stage LLM pipeline. Exposes four integration interfaces: CLI (Cobra), HTTP REST API (Chi), MCP server (mcp-go), and interactive TUI (Bubble Tea). Produces branching story trees with multiple endings, growth paths, and minigame integration points for the [[entities/moonshort-backend]] game engine.

## Tech Stack

- **Language:** Go 1.25.0, compiles to a single binary (~24MB)
- **Module:** `github.com/AugustZAD/Dramatizer`
- **CLI Framework:** Cobra v1.8.1 (33 commands)
- **HTTP Router:** Chi v5.2.5 (REST API + SSE progress streaming)
- **MCP Server:** mark3labs/mcp-go v0.46.0 (stdio + HTTP StreamableHTTP transport)
- **TUI:** Bubble Tea v1.3.10 + Bubbles (interactive terminal UI)
- **Database Driver (PostgreSQL):** lib/pq
- **Database Driver (SQLite):** go-sqlite3
- **Configuration:** Viper (YAML/JSON config file support)
- **Binary location:** `/Users/Clock/dramatizer/dram`

## All 33 CLI Commands

Commands are organized by functional category.

### Data Management Commands

| Command | Description |
|---------|-------------|
| `dram upload <file>` | Upload a novel file (txt/epub) to the database. Accepts `--title` flag for custom title. |
| `dram novel list` | List all uploaded novels with ID, title, status, and word count. Supports `--status` filter and `--json` output. |
| `dram novel get <id>` | Show detailed information about a specific novel including chapter count and processing history. |
| `dram novel delete <id>` | Remove a novel and all associated jobs/artifacts from the database. |
| `dram job list` | List processing jobs. Filterable by `--novel-id` and `--status` (pending, running, completed, failed). |
| `dram job get <id>` | Show job details including current stage, progress percentage, and timing. |
| `dram job create <novel-id>` | Create a new processing job for a novel. Returns the job ID. |
| `dram job stop <id>` | Cancel a running job. Sends termination signal to the pipeline runner. |
| `dram artifact list <job-id>` | List all artifacts (stage outputs) for a job. Shows stage name, size, and creation time. |
| `dram artifact get <job-id> <stage>` | Retrieve the content of a specific stage artifact as JSON. |
| `dram artifact set <job-id> <stage>` | Inject a controller artifact (e.g., prompt-preamble, target-episodes) before running. Reads content from stdin or `--content` flag. |
| `dram artifact edit <job-id> <stage>` | Apply diff-based editing to an existing artifact. Accepts `--diff` flag with the patch content. |
| `dram snapshot list <job-id>` | List LLM call snapshots (input/output records) for auditability. |
| `dram snapshot get <snapshot-id>` | Retrieve full LLM snapshot including the prompt, response, tokens used, and latency. |

### Pipeline Execution Commands

| Command | Description |
|---------|-------------|
| `dram run <job-id>` | Run the full 15-stage pipeline for a job. Supports `--stage <name>` to start from a specific stage and `--restart` to re-run a completed stage. |
| `dram pipeline status <job-id>` | Show pipeline progress with per-stage completion status. Supports `--json` for structured output. |
| `dram pipeline list-stages` | List all 15 pipeline stages with descriptions and phase groupings. |
| `dram export <job-id>` | Export the final story tree artifact as a standalone JSON file suitable for import into [[entities/moonshort-backend]]. |

### Integration Commands

| Command | Description |
|---------|-------------|
| `dram mcp` | Start MCP server in stdio mode. Connects to [[entities/mobai-agent]] as a local tool provider. |
| `dram mcp --http --port 9002` | Start MCP server in HTTP StreamableHTTP mode. Enables remote agent connections. |
| `dram serve --port 3000` | Start the HTTP REST API server with SSE progress streaming. For web clients and direct API access. |
| `dram gateway --port 9001` | Start the [[entities/cli-gateway]] microservice. Enables remote CLI execution via the gateway protocol. Accepts `--api-key` flag or reads `CLI_GATEWAY_KEY` env var. |

### Authentication and Billing Commands

| Command | Description |
|---------|-------------|
| `dram auth login` | Authenticate with the billing service. Stores credentials locally. |
| `dram auth logout` | Clear stored authentication credentials. |
| `dram auth status` | Show current authentication status and account information. |
| `dram billing status` | Show current billing usage, quotas, and remaining credits. |
| `dram billing history` | Show billing transaction history. |

### Meta Commands

| Command | Description |
|---------|-------------|
| `dram version` | Print version, build date, and Go version. |
| `dram help` | Show top-level help with all command groups. |
| `dram config show` | Display the current configuration (merged from file + env). |
| `dram config init` | Generate a default configuration file. |

### Generated Entity Commands (17)

The code generation system (`codegen/`) produces 17 additional CRUD commands for database entities. These are auto-generated from YAML schema definitions and should never be manually edited in the `gen/` directory.

## 15-Stage Pipeline

The pipeline processes novels through three phases, each containing multiple stages that can be run independently, restarted, or resumed.

### Phase 1: Content Extraction (Stages 1-6)

**Stage 1: `skeleton`** -- Extracts the protagonist and core characters from the first 10,000 characters of the novel. Produces a character skeleton with names, relationships, and key attributes. This stage runs on a small context to quickly identify the main cast.

**Stage 2: `extract`** -- Parallel scene extraction across all chapters. Each chapter is processed independently, extracting scenes with dialogue, action, and emotional beats. This stage is resumable: if interrupted, it picks up from the last completed chapter.

**Stage 3: `resolve`** -- Unifies character names across chapters. Novels often refer to characters by different names, nicknames, or titles in different chapters. This stage builds a canonical name mapping and normalizes all references.

**Stage 4: `bible`** -- Generates the narrative authority document. This is a comprehensive reference containing world rules, character arcs, thematic elements, and narrative constraints. Processed in 3 sub-stages for thoroughness. The bible serves as the ground truth for all subsequent stages.

**Stage 5: `judge`** -- Quality review with conditional routing. An LLM evaluates the extracted content against the bible for consistency, completeness, and narrative coherence. If quality thresholds are not met, the pipeline can route back to earlier stages for re-processing.

**Stage 6: `final`** -- Merges all extracted data into canonical form. Combines the skeleton, extracted scenes, resolved names, and bible into a unified data structure that serves as input for Phase 2.

### Phase 2: Screenplay Architecture (Stages 7-8)

**Stage 7: `refine-map`** -- Episode planning. Divides the novel's content into episodes with defined boundaries, pacing targets, and narrative arcs. This stage is restartable: it can be re-run with different parameters (e.g., different `target-episodes` count) without affecting Phase 1 artifacts.

**Stage 8: `refine-write`** -- Writes the actual episode screenplays. Each episode is written with dialogue, stage directions, and transition markers. This stage is resumable: episodes are written sequentially and the pipeline can pick up from the last completed episode.

### Phase 3: Interactive Branches (Stages 9-15)

**Stage 9: `ludify-analyze`** -- Story structure analysis. Examines the linear screenplay from Phase 2 and identifies natural branching points, decision moments, and player agency opportunities.

**Stage 10: `ludify-tree`** -- Story tree design. Creates the master branching structure using an Agent Loop pattern: think (analyze branching options) -> draft (create the tree) -> critique (evaluate the tree for balance and player experience) -> revise (refine based on critique). This iterative approach produces higher-quality story trees than single-pass generation.

**Stage 11: `ludify-growth`** -- Growth choice points. Adds character development branches where player decisions affect stats, skills, or relationships. These are parallel branches that reconnect to the main storyline.

**Stage 12: `ludify-minor`** -- Minor branches. Creates short side branches (1-3 episodes) that explore alternative scenarios or "what if" moments. These branches always return to the main storyline.

**Stage 13: `ludify-badend`** -- Bad endings. Designs narrative-purpose bad endings that serve the story rather than simply punishing the player. Each bad ending has a thematic connection to the player's choices.

**Stage 14: `ludify-route`** -- Independent subplots. Creates parallel storylines (maximum 2) that run alongside the main story. These are longer branches with their own narrative arcs.

**Stage 15: `ludify-fusion`** -- Final merge. Combines all branches (main storyline, growth points, minor branches, bad endings, and routes) into the final v2.0 story tree. Produces the complete interactive screenplay JSON that can be exported for [[entities/moonshort-backend]].

## All 14 MCP Tools

### Read Operations

**`list_novels`** -- List all uploaded novels. Parameters: `status` (string, optional, filter by processing status), `limit` (number, optional, max results). Returns array of novel objects with id, title, status, word_count, and created_at.

**`get_novel`** -- Get detailed novel information. Parameters: `novel_id` (number, required). Returns novel object with full metadata including chapter list.

**`list_jobs`** -- List processing jobs. Parameters: `novel_id` (number, optional, filter by novel), `status` (string, optional, filter by status: pending/running/completed/failed), `limit` (number, optional). Returns array of job objects.

**`get_job`** -- Get job details with pipeline progress. Parameters: `job_id` (number, required). Returns job object including current_stage, progress_percent, stage_statuses (per-stage completion), and timing information.

**`list_artifacts`** -- List stage outputs for a job. Parameters: `job_id` (number, required), `stage` (string, optional, filter by stage name). Returns array of artifact objects with stage, size_bytes, and created_at.

**`get_artifact`** -- Get the content of a specific stage artifact. Parameters: `job_id` (number, required), `stage` (string, required). Returns the full JSON content of the artifact.

**`list_snapshots`** -- List LLM call records for a job. Parameters: `job_id` (number, required), `stage` (string, optional, filter by stage). Returns array of snapshot metadata (id, stage, model, tokens, latency).

**`get_snapshot`** -- Get a full LLM call record. Parameters: `snapshot_id` (number, required). Returns the complete snapshot including the input prompt, LLM response, model name, token counts, and latency.

### Write Operations

**`create_job`** -- Create a new processing job. Parameters: `novel_id` (number, required). Returns the created job object with its assigned id.

**`set_artifact`** -- Inject a controller artifact before running the pipeline. Parameters: `job_id` (number, required), `stage` (string, required, e.g., "prompt-preamble" or "target-episodes"), `content` (string, required). Used to set quality constraints or configuration before pipeline execution.

**`edit_artifact`** -- Apply diff-based editing to an existing artifact. Parameters: `job_id` (number, required), `stage` (string, required), `diff` (string, required, the patch content). Returns the updated artifact. Useful for making targeted corrections to pipeline outputs without re-running entire stages.

**`stop_job`** -- Cancel a running job. Parameters: `job_id` (number, required). Sends a termination signal to the pipeline runner and marks the job as cancelled.

### Additional Tools (via MCP-go extensions)

**`run_pipeline`** -- Trigger pipeline execution for a job. Parameters: `job_id` (number, required), `stage` (string, optional, start from stage), `restart` (boolean, optional, force restart of completed stage).

**`get_pipeline_status`** -- Get real-time pipeline progress. Parameters: `job_id` (number, required). Returns per-stage status with progress indicators.

## HTTP REST API

The REST API is served by `dram serve` using the Chi router.

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Health check. Returns `{ status: "ok", version: "...", uptime: ... }` |
| `GET` | `/api/novels` | List novels. Query params: `status`, `limit`, `offset` |
| `GET` | `/api/novels/:id` | Get novel details |
| `POST` | `/api/novels` | Upload a novel (multipart form or JSON body) |
| `DELETE` | `/api/novels/:id` | Delete a novel |
| `GET` | `/api/jobs` | List jobs. Query params: `novel_id`, `status`, `limit` |
| `GET` | `/api/jobs/:id` | Get job details |
| `POST` | `/api/jobs` | Create a job. Body: `{ novel_id: number }` |
| `POST` | `/api/jobs/:id/run` | Start pipeline execution. Body: `{ stage?: string, restart?: boolean }` |
| `POST` | `/api/jobs/:id/stop` | Stop a running job |
| `GET` | `/api/jobs/:id/artifacts` | List artifacts for a job |
| `GET` | `/api/jobs/:id/artifacts/:stage` | Get specific artifact content |
| `PUT` | `/api/jobs/:id/artifacts/:stage` | Set/update an artifact |
| `PATCH` | `/api/jobs/:id/artifacts/:stage` | Edit artifact with diff |
| `GET` | `/api/jobs/:id/progress` | SSE endpoint for real-time pipeline progress streaming |
| `GET` | `/api/jobs/:id/snapshots` | List LLM snapshots for a job |
| `GET` | `/api/snapshots/:id` | Get a specific LLM snapshot |
| `POST` | `/api/auth/login` | Authenticate. Body: `{ username, password }` |
| `POST` | `/api/auth/logout` | Clear session |
| `GET` | `/api/auth/me` | Get current user info |
| `GET` | `/api/admin/stats` | Admin statistics (requires admin role) |

### SSE Progress Streaming

The `/api/jobs/:id/progress` endpoint streams real-time pipeline progress via Server-Sent Events. Event types:

```
event: stage_start
data: {"stage": "skeleton", "timestamp": "..."}

event: stage_progress
data: {"stage": "extract", "chapter": 5, "total": 20, "percent": 25}

event: stage_complete
data: {"stage": "skeleton", "duration_ms": 4521}

event: pipeline_complete
data: {"job_id": 123, "total_duration_ms": 180000}

event: error
data: {"stage": "bible", "message": "LLM call failed: rate limit exceeded"}
```

## 4 Integration Modes

| Mode | Command | Port | Use Case |
|------|---------|------|----------|
| MCP stdio | `dram mcp` | N/A (local) | Local connection to [[entities/mobai-agent]] as a tool provider. Agent launches Dramatizer as a child process and communicates via stdin/stdout. |
| MCP HTTP | `dram mcp --http --port 9002` | 9002 | Remote agent connection. Uses mcp-go's `server.NewStreamableHTTPServer()` for HTTP StreamableHTTP transport. All 14 MCP tools work identically to stdio mode -- only the transport changes. |
| CLI Gateway | `dram gateway --port 9001` | 9001 | Remote CLI execution via the [[entities/cli-gateway]] protocol. Enables [[entities/mobai-agent]] to run `dram` commands on a remote server transparently. Implemented as a Go subcommand using Chi router with bearer auth middleware. |
| REST API | `dram serve --port 3000` | 3000 | Full HTTP REST API with SSE progress streaming. For web clients, dashboards, or direct API integration. |

## Database

### Abstract Store Interface

Dramatizer uses an abstract `Store` interface that supports two backends:

**SQLite (development):** Default for local development. Database file stored at a configurable path. Already migrated and ready to use. Suitable for single-user operation and testing.

**PostgreSQL (production):** Used in production deployments. Supports concurrent access and scales to larger datasets. Connection configured via environment variables or config file.

The Store interface provides CRUD operations for novels, jobs, artifacts, snapshots, and authentication data. All pipeline stages read from and write to the store.

## Configuration

### Viper Configuration

Dramatizer uses Viper for configuration management, supporting YAML and JSON file formats, environment variable overrides, and command-line flags.

**`config/pipeline.yaml`** -- Defines the 15 pipeline stages with their names, descriptions, phase groupings, dependencies, and execution parameters (parallelism, retry counts, timeout).

**`config/stage-llm.yaml`** -- Model routing configuration. Maps each pipeline stage to a specific LLM model, allowing different stages to use different models based on their requirements. For example, simple extraction stages might use a fast, cheap model while complex analysis stages use a more capable model. Default model: Grok 4.1 Fast via ZenMux.

### Configuration Hierarchy

1. Default values (hardcoded)
2. Configuration file (`config.yaml` or specified via `--config` flag)
3. Environment variables (prefixed with `DRAM_`)
4. Command-line flags (highest priority)

## Code Generation

The `codegen/` directory contains YAML schema definitions for database entities. A code generator reads these schemas and produces Go code in the `gen/` directory, including:

- Database model structs
- CRUD repository functions
- CLI subcommands for entity management (the 17 generated commands)
- API route handlers for entity endpoints

The `gen/` directory is marked as auto-generated and should never be manually edited. Changes to entity schemas should be made in `codegen/` YAML files and regenerated via `make generate`.

## Build System

The project uses a Makefile with the following targets:

| Target | Description |
|--------|-------------|
| `make generate` | Run code generation from YAML schemas to Go code |
| `make build` | Compile the binary to `./dram` |
| `make dev` | Build and run in development mode |
| `make test` | Run all tests |
| `make release` | Build release binaries for multiple platforms |
| `make docker-build` | Build the Docker image |
| `make lint` | Run golangci-lint |
| `make migrate` | Run database migrations |

## Authentication

Bearer token JWT authentication. The auth service handles user registration, login, and token validation. Tokens are included in the `Authorization: Bearer <token>` header for API requests. The `dram auth` command group manages local credential storage.

## Billing

Integrated billing service that tracks LLM token usage per pipeline stage. The `dram billing` command group shows usage statistics and remaining credits. Billing data is associated with the authenticated user account.

## Key Operational Notes

- LLM calls are snapshotted to the database for full auditability. Every prompt and response is recorded with timing and token counts.
- Artifact existence equals stage completion. The pipeline uses this as its recovery mechanism: if a stage's artifact exists, that stage is considered done.
- The pipeline is resumable at any stage. Interrupted runs can be restarted from the point of failure.
- Controller artifacts (`prompt-preamble`, `target-episodes`) can be injected before running to customize pipeline behavior without modifying code.

## Related

- [[entities/mobai-agent]] -- Orchestrator agent that connects to Dramatizer via MCP
- [[entities/moonshort-backend]] -- Game engine that imports Dramatizer's story tree output
- [[entities/cli-gateway]] -- Protocol used by the `dram gateway` command
- [[concepts/cli-gateway-protocol]] -- HTTP API specification
- [[concepts/four-layer-philosophy]] -- Design framework positioning Dramatizer's CLI/MCP/API layers

## Sources

- [Dramatizer skill](../raw/2026-04-14-dramatizer-skill.md)
- [Agent memory](../raw/2026-04-14-mobai-agent-memory.md)
- [CLI Gateway design spec](../raw/2026-04-14-cli-gateway-server-layer-design.md)
