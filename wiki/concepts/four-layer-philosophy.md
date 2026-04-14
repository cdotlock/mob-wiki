---
title: "SKILL / CLI / MCP / API Four-Layer Philosophy"
tags: [architecture, agent, design-pattern, framework]
sources: [raw/2026-04-14-cli-gateway-server-layer-design.md]
created: 2026-04-14
updated: 2026-04-14
---

# SKILL / CLI / MCP / API Four-Layer Philosophy

## Origin and Purpose

The Four-Layer Philosophy is a design framework derived from cross-project analysis of two production agent-platform integrations: lark-cli (a CLI for the Feishu/Lark platform) and dws (a CLI for the DingTalk Workspace platform). These two projects, built independently to solve the same fundamental problem -- letting AI agents operate complex enterprise platforms -- converged on strikingly similar architectural patterns despite differing in language, platform, and implementation strategy.

The framework addresses a specific challenge: when an AI agent must operate a complex platform (one with dozens or hundreds of API endpoints, multiple authentication schemes, domain-specific workflows, and context-dependent behaviors), how should the interface between the agent and the platform be structured? A naive approach -- expose all APIs directly to the agent -- fails catastrophically. The agent drowns in options, re-derives authentication logic on every call, cannot discover capabilities progressively, and has no fallback when its primary interface breaks.

The Four-Layer Philosophy solves this by recognizing that an agent can be in one of four distinct cognitive states at any given moment, and each state requires a different kind of interface. The four layers are not four alternatives to choose between. They are four complementary interfaces, each optimized for a different cognitive state. A well-designed system provides all four simultaneously, ensuring the agent always has an appropriate entry point regardless of how much or how little it knows about the task at hand.

## The Four Layers

### SKILL (Knowledge Layer) -- "How to think about the problem"

The SKILL layer consists of structured knowledge documents -- typically Markdown files -- that are injected directly into the LLM's context window as part of the system prompt. SKILL documents provide direction, constraints, decision frameworks, and domain rules. They tell the agent how to reason about a problem domain, what trade-offs exist, what invariants must be maintained, and what the correct sequence of operations is for complex workflows.

The defining characteristic of the SKILL layer is that it gives direction without giving specific execution means. A SKILL document might say "when running the dramatizer pipeline, always check the artifact from the previous stage before advancing to the next stage" -- but it does not specify the exact CLI command or MCP tool call to use for that check. This decoupling from implementation is deliberate and essential: CLI commands can be renamed, MCP tools can be reorganized, API endpoints can change -- but the domain knowledge captured in SKILL documents remains valid across all of these changes.

There is an inverse relationship between the predictability of the tool surface and the criticality of the SKILL layer. When the CLI and MCP surfaces are stable and well-documented (as in the Dramatizer, where hand-written CLI commands have stable names and flags), the SKILL layer provides helpful context but is not strictly essential for basic operation. When the tool surface is dynamic and unpredictable (as in Agent-Forge, where CLI commands are dynamically generated from the MCP tool catalog and can change between deployments), the SKILL layer becomes the only reliable source of intent-to-tool mapping. Without it, the agent cannot reason about which tool to call because the tool names themselves are unstable.

In the Moonshort platform, the SKILL layer is implemented through six skill files organized in the `skills/` directory of mobai-agent:

- **`skills/dramatizer/pipeline.md`** -- Encodes knowledge of the Dramatizer's 15-stage pipeline. Contains the stage ordering, the expected artifact format at each stage, the rules for stage advancement (when to auto-advance versus when to wait for human review), and the error recovery procedures for each stage. This skill is what allows the agent to orchestrate a multi-hour dramatization job without losing track of where it is in the pipeline.

- **`skills/agent-forge/video-production.md`** -- Contains the MCP tool catalog for Agent-Forge, mapping high-level intents (create a video, list available skills, check rendering status) to specific MCP tool names and their parameter schemas. Because Agent-Forge's MCP surface is large (60+ tools across multiple capability domains), this skill provides the navigational map that prevents the agent from getting lost in the tool space.

- **`skills/general/orchestrator.md`** -- Defines cross-platform coordination rules: how to sequence operations that span multiple Moonshort services, how to handle partial failures (when one service succeeds but another fails), and how to maintain consistency across the platform. This skill is activated when the agent is working on tasks that touch more than one service.

- **`skills/moonshort/game-client.md`** -- Covers the game client testing workflow, including headless browser automation patterns, visual regression testing procedures, and the relationship between test results and deployment gates.

- **`skills/general/coding.md`** -- General software engineering practices adapted for agent use, including code review checklists, refactoring patterns, and test-writing guidelines.

- **`skills/general/debugging.md`** -- Systematic debugging methodology: how to isolate failures, how to read stack traces, how to use binary search on commit history, and when to escalate to human review.

SKILL documents are loaded into the agent's context through a trigger-matching system. Each skill defines trigger patterns (keywords, tool names, or domain indicators) that determine when it should be activated. When the agent's current conversation matches a skill's triggers, that skill is injected into the system prompt for the duration of the relevant interaction. This mechanism ensures the agent has the right domain knowledge at the right time without permanently consuming context window capacity.

### CLI (Discovery and Orchestration Layer) -- "What to call, in what order"

The CLI layer provides packaged command-line tools with progressive discovery capabilities. A CLI tool supports `schema` (to enumerate available commands), `help` (to explain what a command does and what arguments it accepts), and `--dry-run` (to preview what a command would do without executing it). This trio of capabilities enables an agent to go from complete ignorance of a tool's capabilities to confident, correct usage through a predictable discovery sequence.

From the perspective of an external agent, a CLI tool is a black box. The agent does not need to know -- and should not care -- whether a CLI command internally calls three API endpoints, one MCP tool, or a combination of both. This opacity is a design goal, not a defect. It means that the internal implementation of a CLI command can be completely refactored (switching from direct API calls to MCP proxying, for example) without any change to how the agent invokes it. The agent's learned patterns for using the CLI remain valid across internal reorganizations.

The CLI layer's primary strength is pipeline encapsulation: the ability to integrate a complex, multi-step workflow into a single command invocation. Consider the Dramatizer's `dram run <job-id>` command. Internally, this command orchestrates a 15-stage pipeline: it initializes the job, fetches the source material, runs each transformation stage in sequence, validates the output of each stage, handles retries on transient failures, writes artifacts to the correct locations, updates the job status in the database, and reports completion. Without CLI encapsulation, the agent would need to manage all of these steps individually, keeping track of state across dozens of sequential tool calls with no atomicity guarantees. With CLI encapsulation, the agent issues one command and receives one result.

The CLI layer also internalizes cross-cutting concerns that would otherwise need to be re-solved by every agent on every call. These cross-cutting concerns include: authentication (the CLI handles API key management, token refresh, and credential storage), error classification (the CLI distinguishes between transient errors that should be retried and permanent errors that require human intervention), audit logging (the CLI records what was executed, when, and by whom), and input correction (the CLI can suggest corrections for common mistakes, such as misspelled subcommand names or missing required flags). These concerns are solved once in the CLI implementation and applied uniformly to all invocations, whether those invocations come from a human user, an AI agent, or an automated pipeline.

In the Moonshort platform, the CLI layer includes several tools:

- **`dram run <job-id>`** -- Encapsulates the full 15-stage dramatizer pipeline. The agent issues one command; the CLI handles stage sequencing, artifact validation, error recovery, and progress reporting internally.

- **`dram run <job-id> --stage <name>`** -- Runs a single specific stage of the pipeline, used when the agent needs fine-grained control over pipeline execution (for example, re-running a failed stage after fixing its input).

- **`noval play <novelId> --auto`** -- Encapsulates a complete automated game session in the Moonshort client. The CLI handles session initialization, page navigation, input simulation, screenshot capture, and result extraction. Without this CLI command, the agent would need to manage headless browser state across dozens of tool calls.

- **`play <testSuite>`** -- Runs a test suite against the game client, handling test fixture setup, browser launch, test execution, result collection, and cleanup.

### MCP (Direct Access Layer) -- "Just do this specific thing, efficiently"

The MCP (Model Context Protocol) layer provides fine-grained tool invocation. Where the CLI layer bundles operations into high-level commands with discovery overhead (help text, flag parsing, output formatting), the MCP layer exposes individual capabilities as directly callable tools with structured input and output schemas. When the agent already knows exactly which capability it needs to invoke, MCP provides the fastest path to execution by skipping the CLI ceremony entirely.

The relationship between CLI and MCP is complementary, not competitive. CLI is for exploration ("I'm still figuring out what to do"). MCP is for execution ("I know what to do, and I want to do it fast"). An agent working on a new, unfamiliar task will typically start with the CLI layer, using `--help` and `schema` to understand available capabilities, then transition to MCP for repeated operations once it has learned the correct tool and parameter patterns. This transition from CLI to MCP is a natural part of the agent's learning process within a session.

The MCP layer is particularly valuable for operations that the agent performs frequently within a session. Consider an agent monitoring a dramatizer pipeline job. It might need to check the status of the current stage dozens of times over the course of a multi-hour run. Using the CLI for each check would involve parsing a full command invocation and help-text-formatted output each time. Using the MCP tool `dramatizer_get_artifact { job_id, stage }` provides the same information in a single structured call with a JSON response that can be parsed programmatically.

In the Moonshort platform, the MCP layer includes tools from two primary servers:

- **Agent-Forge MCP** (HTTP transport, 60+ tools): `agent_forge_skills__list {}` for querying available skills, `agent_forge_render__start { template, params }` for initiating video renders, `agent_forge_assets__upload { path }` for uploading media assets, and many others organized across capability domains (skills, rendering, assets, projects, settings).

- **Dramatizer MCP** (stdio transport in local mode, HTTP transport in cloud mode, 14 tools): `dramatizer_get_artifact { job_id, stage }` for retrieving stage outputs, `dramatizer_run_stage { job_id, stage }` for executing individual pipeline stages, `dramatizer_list_jobs {}` for enumerating pipeline jobs, and others covering job lifecycle management.

### API (Raw Capability Layer) -- "What the system can do"

The API layer is the invisible foundation that powers everything above it. Every CLI command and every MCP tool ultimately resolves to one or more API calls against the underlying service. However, the API layer is deliberately invisible to the agent under normal operating conditions. The agent should never call raw APIs directly, because doing so means re-solving authentication (constructing the correct header, refreshing expired tokens), pagination (handling paginated responses across multiple requests), error recovery (distinguishing transient network failures from permanent authorization failures), and audit logging (recording what was done for compliance and debugging) -- all problems that the CLI and MCP layers have already solved.

The API layer exists as a fallback of last resort, exposed through the CLI's raw API passthrough mechanism. In the Moonshort platform, this takes the form of the bash tool, which can execute arbitrary HTTP requests when all higher-level interfaces fail. For example, if the Dramatizer's MCP server is down and the CLI gateway is unreachable, the agent can fall back to `bash: curl -s http://localhost:8001/api/health` to check whether the service is running at all. This ensures the agent is never completely stuck, even when the primary interfaces are unavailable.

The design principle is clear: the API layer should be invisible by default, and its direct use by the agent is a signal that something in the higher layers has failed. If the agent finds itself frequently falling back to raw API calls, that is an indicator that the CLI and MCP layers need to be improved to cover the missing use cases.

## Cognitive State Decision Tree

The four layers map to a decision tree based on the agent's current cognitive state. At any moment, the agent is in one of four states, and each state has a natural corresponding layer:

```
Agent faces a task:
  |
  +-- Doesn't know how to think about it
  |   --> Read SKILL for direction and constraints
  |   Example: Agent receives "run the dramatizer pipeline for this novel"
  |            but has never done this before. It reads the pipeline skill
  |            to learn the 15-stage sequence, validation rules, and
  |            error recovery procedures.
  |
  +-- Knows direction, not specific command
  |   --> Use CLI progressive discovery (schema -> help -> dry-run -> run)
  |   Example: Agent knows it needs to check pipeline job status but
  |            doesn't remember the exact command. It runs "dram --help"
  |            to see available subcommands, then "dram status --help"
  |            to learn the flags.
  |
  +-- Knows exactly what to call, wants speed
  |   --> Use MCP direct invocation
  |   Example: Agent has been monitoring a pipeline job for 30 minutes
  |            and knows the exact MCP call. It invokes
  |            dramatizer_get_artifact { job_id: "j-42", stage: "ludify" }
  |            directly without any CLI overhead.
  |
  +-- Nothing else works
      --> Use CLI raw API fallback (bash tool with curl)
      Example: MCP server is down, CLI gateway returns 503. Agent falls
               back to "curl -s http://localhost:9001/api/jobs/j-42/status"
               to check if the service is alive at all.
```

This decision tree is not a rigid flowchart. The agent may jump between layers within a single task. It might start with SKILL to understand the problem, use CLI to discover the right tool, switch to MCP for repeated execution, and fall back to API when it encounters an error. The key insight is that all four layers are always available, and the agent selects the appropriate one based on its current knowledge state.

## Core Design Principles

### Principle 1: SKILL gives direction, not means

SKILL documents encode domain wisdom: the knowledge that outlives any specific command name, tool version, or API endpoint. A SKILL document says "always validate the output of each pipeline stage before advancing" -- it does not say "call `dram status <job-id>` and check for `status: complete`." This separation ensures that SKILL documents remain valid even when the CLI is completely rewritten, the MCP tools are reorganized, or the underlying APIs change version. Domain wisdom is the most durable layer of knowledge in the system, and SKILL documents are designed to capture and preserve it.

### Principle 2: CLI is the sole execution entry for external agents

All execution by external agents routes through the CLI layer. A single binary, a single authentication flow, a single audit trail. This is not an arbitrary constraint -- it is a security and observability requirement. When all agent actions pass through the CLI, there is one place to enforce access controls, one log to audit, one interface to monitor for anomalous behavior, and one surface to harden against misuse. The CLI is the checkpoint through which all agent intent passes into system action.

### Principle 3: CLI and MCP complement, never compete

CLI and MCP serve different cognitive states. Treating them as competitors -- asking "should I expose this capability as a CLI command or an MCP tool?" -- is a category error. The answer is often "both," because the agent may need to discover the capability (CLI) in one session and execute it efficiently (MCP) in the next. The CLI provides the navigation map; MCP provides the highway. You need both to get where you are going.

### Principle 4: API is invisible by design

The agent should never directly compose raw HTTP requests against service APIs under normal operating conditions. Direct API usage means the agent is re-solving problems (authentication, pagination, error recovery, audit) that the higher layers have already solved. This is the single largest source of engineering waste in agent-platform integrations: multiple agents, each independently re-deriving the same credential-management and error-handling logic that could have been solved once in a shared CLI layer.

### Principle 5: Layer weights are elastic

Not all systems implement the four layers with equal emphasis. A system with a rich, hand-crafted CLI (like the Dramatizer) can put less weight on the SKILL layer because the CLI itself embodies much of the domain logic through its subcommand structure and help text. A system with a dynamically-generated, unpredictable CLI (like Agent-Forge, where CLI commands are generated from the MCP tool catalog) must put more weight on the SKILL layer because the CLI surface alone is not a reliable guide to correct usage. The philosophy is a framework, not a recipe. The relative weight of each layer should be calibrated to the specific system's characteristics.

### Principle 6: Design for every cognitive state

If an agent in any cognitive state has no appropriate entry point, the system has failed. This is the completeness criterion. A system that has CLI and MCP but no SKILL leaves the agent with no way to learn how to think about a new problem domain. A system that has SKILL and API but no CLI leaves the agent with no way to progressively discover capabilities. A system that has SKILL, CLI, and MCP but no API fallback leaves the agent stuck when the primary interfaces break. The four layers must all be present for the system to handle every possible agent state.

## Architecture Variants

The Four-Layer Philosophy can be implemented through two primary architecture patterns, both of which are present in the Moonshort platform.

### Variant 1: CLI wraps API directly (Dramatizer / lark-cli)

In this variant, the CLI is a hand-written binary that directly calls the underlying service APIs. The CLI contains rich, purpose-built subcommands with carefully designed flags, help text, and output formatting. Each CLI command embeds domain knowledge in its implementation: it knows the correct API call sequence, the expected response format, and the appropriate error handling for its specific use case.

MCP supplements the CLI by providing server-side intelligence: the ability for the agent to call individual tool functions without the overhead of command-line invocation and output parsing. The MCP tools may expose the same underlying capabilities as the CLI commands, but through a structured JSON interface optimized for programmatic access.

In this variant, the SKILL layer is important but not critical, because the CLI itself encodes significant domain logic. The CLI's help text, subcommand hierarchy, and `--dry-run` output collectively provide a rich source of domain knowledge that the agent can discover interactively.

The Dramatizer is the canonical example: `dram` is a Go binary with hand-crafted subcommands (`dram run`, `dram status`, `dram mcp`, `dram gateway`), each with carefully designed flags and comprehensive help text. The 14 MCP tools supplement these commands for direct access.

### Variant 2: CLI wraps MCP as core transport (Agent-Forge / dws)

In this variant, the CLI is dynamically generated from the MCP tool catalog. Instead of hand-writing each CLI command, the CLI discovers available MCP tools at startup and generates corresponding command-line interfaces automatically. This approach scales well when the MCP surface is large and changes frequently, but it produces a CLI surface that is unpredictable: command names, flags, and behaviors can change between deployments as the underlying MCP tools evolve.

In this variant, the SKILL layer becomes essential. Because the CLI surface is dynamically generated, the agent cannot rely on stable command names or predictable flag patterns. The SKILL layer is the only reliable source of intent-to-tool mapping: it tells the agent "when you need to start a video render, look for a tool whose name contains 'render' and 'start'" -- a pattern-based approach that survives tool catalog changes.

Agent-Forge is the canonical example: its CLI commands are generated from a catalog of 60+ MCP tools. The SKILL document `skills/agent-forge/video-production.md` provides the navigational map that makes this dynamic surface usable.

## Technology Selection Principle

When choosing the implementation language and framework for agent-facing CLI tools, the correct question is not "which language or framework is better?" The correct question is "which constraints are non-negotiable, and which technology has no disqualifying weakness against all of them simultaneously?"

For agent-facing CLI tools, the recurring constraint stack is: zero-dependency cross-platform binary (the CLI must work on any machine without a package manager or runtime installation), sub-50ms cold start under high-frequency invocation (the agent may call the CLI hundreds of times per session, and startup latency compounds), and native OS integration (keychain access for credential storage, file locks for concurrent execution safety, signal handling for graceful shutdown). When all three constraints co-occur, the viable option space narrows dramatically. Languages like Go and Rust satisfy all three. Languages that require a runtime (Python, Node.js, Ruby) fail the first constraint. Languages with garbage-collector pauses (Java, C#) risk failing the second under sustained high-frequency invocation.

This principle is not about language preference. It is about engineering honesty: start with the non-negotiable constraints, and let the technology choice fall out of the constraint analysis.

## Design Maxim

Build systems for agents the way you would onboard a capable but context-blind new hire: give them domain knowledge to think correctly (SKILL), a well-labeled toolbox to work with (CLI), shortcuts for repeated tasks (MCP), and raw materials when nothing else fits (API). Never make them re-derive what you have already solved.

This analogy captures the essential insight of the Four-Layer Philosophy. The new hire is intelligent and capable, but starts with zero knowledge of the specific domain. SKILL provides the onboarding documentation. CLI provides the standard operating procedures. MCP provides the keyboard shortcuts that experienced operators use. API provides the emergency manual for when the standard tools are broken. A good onboarding process provides all four; a system that skips any of them produces a new hire (or an agent) that is unnecessarily slow, error-prone, or stuck.

## How mobai-agent Implements This

The [[entities/mobai-agent]] system implements all four layers of the philosophy:

**SKILL**: Six skill files in the `skills/` directory, organized by domain (`dramatizer/`, `agent-forge/`, `moonshort/`, `general/`). Skills are loaded through trigger-matching: when the agent's current conversation matches a skill's trigger patterns (keywords, tool names, or domain indicators), the skill content is injected into the system prompt. This ensures domain knowledge is available when needed without permanently consuming context window capacity.

**CLI**: The three built-in tools `discover_cli`, `cli_help`, and `cli_run` implement progressive mastery with auto-recovery. The agent follows a natural progression: `discover_cli` scans for available CLI tools (both local and remote via gateways), `cli_help` retrieves help text for a specific tool or subcommand (with a 7-day cache and 8000-character truncation), and `cli_run` executes commands with smart error recovery (on failure, it automatically fetches and attaches relevant help text to the error response, enabling the agent to self-correct). This trio enables an agent to go from complete ignorance of available tools to confident, correct usage within a single conversation.

**MCP**: The `mcp-client.ts` module connects to MCP servers using both HTTP (StreamableHTTP with SSE fallback) and stdio transports. In the current Moonshort deployment, this provides access to 60+ tools from Agent-Forge (HTTP transport at `http://localhost:8001/mcp`) and 14 tools from the Dramatizer (stdio transport spawning the `dram mcp` subprocess). Each MCP tool is wrapped as a standard `ToolDefinition` with automatic JSON Schema to Zod conversion, making MCP tools indistinguishable from built-in tools in the agent's tool registry.

**API**: The bash tool serves as the fallback escape hatch. When MCP servers are unreachable and CLI gateways are down, the agent can still execute arbitrary shell commands, including `curl` requests against raw API endpoints. This ensures the agent is never completely stuck, consistent with the fourth layer's role as the interface of last resort.

## Related

- [[entities/mobai-agent]]
- [[concepts/cli-gateway-protocol]]
- [[concepts/server-layer]]
- [[syntheses/cloud-deployment-architecture]]
- [[entities/dramatizer]]
- [[entities/agent-forge]]

## Sources

- [CLI Gateway + Server Layer Design Spec](../raw/2026-04-14-cli-gateway-server-layer-design.md)
- [Orchestrator Skill](../raw/2026-04-14-orchestrator-skill.md)
- [Dramatizer Skill](../raw/2026-04-14-dramatizer-skill.md)
- [Agent-Forge Skill](../raw/2026-04-14-agent-forge-skill.md)
