# Architectural Design Document (PLAN) - Debate Project

## 1. Architectural Overview

### 1.1 Current Layered Model

The repository is organized as a layered CLI application with a multi-process debate runtime.

1. **Presentation layer:** `src/debate_project/` contains the CLI entrypoints, keyboard menu selection, and terminal rendering.
2. **Session layer:** `src/debate_sdk/sdk/` owns session bootstrap, log following, transcript generation, and cost artifact output.
3. **Agent service layer:** `src/debate_sdk/services/` contains the parent judge, child debaters, provider mixins, and routing/judging process splits.
4. **Infrastructure layer:** `src/debate_sdk/shared/` contains contracts, config loading, gatekeeper subsystems, watchdog monitoring, logging, search, state persistence, and recovery primitives.

This is the architecture implemented in the current codebase. The CLI is intentionally thin and delegates all debate execution to the session and service layers.

### 1.2 Runtime Flow

The live execution path is:

`User -> debate_project.cli.main -> run_debate_session -> ParentJudgeAgent process -> child debater processes -> artifacts in results/`

The session layer starts one judge process. The judge process then spawns the pro and con child processes, manages turn routing through multiprocessing queues, emits streamed events back to the CLI, and writes final outputs once the debate concludes.

### 1.3 Topic Ownership

The parent judge owns topic selection. At the start of a session it uses the configured debate model to generate one fresh, neutrally phrased, actively contested scientific question. That topic is then injected into both debater personas for the run, and the transcript artifact includes the topic header before the turn log.

## 2. Current Repository Structure

```text
debate-project/
|
+-- commands/
|   +-- implement_task.md
|
+-- config/
|   +-- setup.json
|   +-- rate_limits.json
|   +-- logging_config.json
|
+-- docs/
|   +-- PRD.md
|   +-- PLAN.md
|   +-- TODO.md
|   +-- PROMPT_BOOK.md
|   +-- DEBATE_TRANSCRIPT.md
|   +-- cli-example.svg
|
+-- results/
|   +-- logs/
|   +-- state/
|   +-- cost_summary_<session_id>.json
|   +-- transcript_<session_id>.md
|
+-- src/debate_project/
|   +-- __main__.py
|   +-- cli.py
|   +-- menu.py
|   +-- render.py
|
+-- src/debate_sdk/sdk/
|   +-- session.py
|   +-- transcript.py
|   +-- pricing.py
|   +-- logstream.py
|
+-- src/debate_sdk/services/
|   +-- base_agent.py
|   +-- child_agent.py
|   +-- pro_agent.py
|   +-- con_agent.py
|   +-- judge_agent.py
|   +-- judge_decision_mixin.py
|   +-- judge_process_mixin.py
|   +-- judge_routing_mixin.py
|   +-- groq_mixin.py
|   +-- gemini_mixin.py
|   +-- web_search_mixin.py
|
+-- src/debate_sdk/shared/
|   +-- config.py
|   +-- config_utils.py
|   +-- contracts.py
|   +-- exceptions.py
|   +-- gatekeeper.py
|   +-- gatekeeper_budget.py
|   +-- gatekeeper_runtime.py
|   +-- gatekeeper_traffic.py
|   +-- history.py
|   +-- logger.py
|   +-- logging_handler.py
|   +-- process_utils.py
|   +-- recovery.py
|   +-- search_client.py
|   +-- state_manager.py
|   +-- version.py
|   +-- watchdog.py
|
+-- tests/
|   +-- unit/
|   +-- integration/
|
+-- pyproject.toml
+-- README.md
```

## 3. Component Responsibilities

### 3.1 Presentation Layer

`src/debate_project/cli.py` is the interactive entrypoint used by both `uv run debate-cli` and `uv run python -m debate_project` through `src/debate_project/__main__.py`.

Its responsibilities are limited to:

- configuring multiprocessing spawn mode
- collecting the requested round count from the menu layer
- starting the background log follower thread
- invoking `run_debate_session`
- rendering streamed events and final cost output to the terminal

Business logic for debate execution does not live in the presentation layer.

### 3.2 Session Layer

The session layer is implemented in `src/debate_sdk/sdk/`.

- `session.py` loads setup config, bounds the round count, starts the judge worker process, collects outbound events, and writes transcript and pricing artifacts.
- `transcript.py` renders a Markdown transcript that starts with the selected topic and ends with the judge decision.
- `pricing.py` resolves model pricing metadata and writes `cost_summary_<session_id>.json`.
- `logstream.py` streams rotating runtime logs into the CLI renderer while a session is active.

### 3.3 Agent Service Layer

The debate engine lives in `src/debate_sdk/services/`.

- `BaseAgent` provides the common process event loop and queue behavior.
- `ChildDebaterAgent` handles turn prompts, prompt shaping, JSON parsing, and normalized argument emission.
- `ProDebaterAgent` and `ConDebaterAgent` combine child-agent behavior with Groq-backed generation and role-specific system prompts.
- `ParentJudgeAgent` is the central orchestrator. It selects the topic, applies topic-aware personas, tracks debate history, routes turns, handles telemetry, and emits the final judgment.

The parent judge is decomposed into focused mixins:

- `judge_process_mixin.py`: child process startup and shutdown
- `judge_routing_mixin.py`: deterministic turn routing, topic announcement, and heartbeat updates
- `judge_decision_mixin.py`: final evaluation, malformed-output normalization, and neutral fallback winner selection

Provider-specific behavior is separated into mixins:

- `groq_mixin.py`: current live chat-completions transport used by the debate runtime
- `gemini_mixin.py`: alternate provider helper retained in the codebase
- `web_search_mixin.py`: search hook used by child agents

### 3.4 Infrastructure Layer

The shared layer contains the runtime support services used by the session and agents.

- `config.py` and `config_utils.py` load and validate the JSON config files.
- `contracts.py` defines the typed IPC and judgment schemas.
- `gatekeeper.py` is the central facade for outbound API execution.
- `gatekeeper_budget.py`, `gatekeeper_traffic.py`, and `gatekeeper_runtime.py` split budget enforcement, traffic control, retries, and telemetry concerns.
- `history.py` stores debate turns for prompt construction and final judgment.
- `state_manager.py` writes durable session checkpoints under `results/state/`.
- `logger.py` and `logging_handler.py` implement structured FIFO log rotation.
- `watchdog.py` monitors child process heartbeats and can invoke a timeout callback.
- `recovery.py` provides a recovery-manager abstraction for respawn workflows.
- `search_client.py` wraps Tavily search access.
- `process_utils.py` contains process-tree termination helpers.

## 4. Multi-Process And IPC Design

### 4.1 Process Topology

The active runtime uses three agent processes per debate session:

1. one `ParentJudgeAgent` worker process created by the session layer
2. one `pro_agent` child process created by the judge
3. one `con_agent` child process created by the judge

The CLI process remains outside this swarm and only consumes streamed outbound events.

### 4.2 Queue Boundaries

The main queue relationships are:

- the session process creates one inbound queue for the judge and one outbound queue back to the CLI session loop
- the judge creates one inbound queue per child debater
- child debaters publish arguments to the judge inbound queue
- the judge publishes `topic_selected`, `argument`, `telemetry`, and `final_judgment` events to the session outbound queue

This design enforces indirect communication. Child agents never talk directly to one another.

### 4.3 Turn Discipline

Turn ordering is deterministic.

- the judge starts round 1 by prompting the pro agent
- every valid pro turn is followed by a con turn
- when the configured round count is reached, the judge stops child execution and evaluates the accumulated history

The judge also rejects out-of-turn child messages to preserve routing integrity.

## 5. Topic Generation, Debate Flow, And Judging

### 5.1 Topic Selection

The parent judge does not take the debate topic from a hardcoded list. Instead it prompts the configured model to return a JSON payload containing a fresh topic and a short balance rationale. The generated topic must:

- be phrased as a neutral question
- stay short and single-sentence
- represent a genuinely contested scientific question
- survive a second validation prompt that checks whether credible arguments exist on both sides

If topic generation or validation fails repeatedly, the judge raises a runtime error rather than silently substituting a hardcoded fallback topic.

### 5.2 Debater Prompting

Child agents receive a concise prompt constructed from debate history. They are required to:

- return JSON only
- keep each turn to 2-3 concise sentences
- directly rebut the latest opponent claim before adding one supporting point
- stay inside the anti-concession and formatting rules loaded from `setup.json`

The judge binds the generated topic into both debater personas for the current run.

### 5.3 Final Decision

After the last con turn, the judge evaluates the full history through `judge_decision_mixin.py`. The decision pipeline:

- requests a single winner and non-zero differential score
- normalizes malformed winner fields and justification payloads
- rejects ties by forcing a minimum non-zero score
- falls back to a deterministic neutral winner selection only if the judging model remains invalid after retries

This keeps malformed judge output from automatically favoring one side.

## 6. External Integrations And Cost Controls

### 6.1 Groq Runtime

The current live debate path uses `groq_mixin.py`, which sends requests to Groq's OpenAI-compatible `/chat/completions` endpoint. The configured model comes from `config/setup.json`. The project metadata and pricing layer currently recognize multiple Groq-served models, with `llama-3.3-70b-versatile` as the active repository configuration.

### 6.2 Search Integration

`search_client.py` provides an optional Tavily-backed search client. Missing search credentials do not terminate the debate loop; the client logs the condition and returns an empty result set.

### 6.3 Gatekeeper Decomposition

All outbound model calls flow through `ApiGatekeeper`.

- budget reservation and usage tracking are isolated in `gatekeeper_budget.py`
- request throttling, queueing, and concurrency limits are isolated in `gatekeeper_traffic.py`
- retry logic, telemetry dispatch, and runtime helpers are isolated in `gatekeeper_runtime.py`

This is the implemented modularization in the current codebase.

## 7. Reliability, State, And Recovery Surfaces

### 7.1 State Persistence

The judge periodically serializes debate state through `StateManager`. The state file is written to `results/state/session_<session_id>.state` using a temporary file plus atomic replace pattern to reduce corruption risk.

### 7.2 Logging

Runtime logs are written through the structured logger stack and rotated by the FIFO handler configured in `config/logging_config.json`. The CLI can tail these logs live through `sdk/logstream.py` while a debate is running.

### 7.3 Watchdog Behavior

The watchdog currently provides heartbeat monitoring and forced termination for stalled child processes. The judge registers the pro and con child processes and starts the watchdog during child-process startup.

Automatic in-session recovery is only partially implemented at the repository level:

- `watchdog.py` supports an `on_timeout` callback
- `recovery.py` provides a `RecoveryManager`
- the current `ParentJudgeAgent` wiring does not attach a recovery callback when constructing the watchdog

Accordingly, the current codebase implements watchdog monitoring and recovery hooks, but not a fully wired end-to-end agent rehydration flow in the active judge runtime.

## 8. Configuration, Tooling, And Quality Gates

### 8.1 Configuration Sources

The runtime depends on three JSON configuration files:

- `config/setup.json` for watchdog and debate behavior
- `config/rate_limits.json` for request, queue, retry, and budget settings
- `config/logging_config.json` for log rotation behavior

These files are normalized through `config_utils.py` before use.

### 8.2 Environment And Entry Points

- project metadata is defined in `pyproject.toml`
- the CLI script entry point is `debate-cli = "debate_project.cli:main"`
- `python -m debate_project` resolves through `src/debate_project/__main__.py`
- provider credentials are expected through `.env`
- the repository currently targets Python `>=3.10,<3.11`

### 8.3 Quality Gates

The repository is set up to use:

- `uv` for environment and command execution
- `ruff` for linting
- `pytest` with coverage enforcement configured in `pyproject.toml`

The configured coverage threshold is 85%.

## 9. Architectural Summary

The current codebase is a layered, queue-driven, multi-process debate system centered on a parent judge process. The judge selects a topic dynamically, enforces strict turn routing, streams structured events back to the CLI, and writes transcript and pricing artifacts at the end of the run. The major modularization steps that exist in the repository today are the gatekeeper subsystem split, the judge mixin split, the session/artifact layer in `src/debate_sdk/sdk/`, and the separation between presentation, services, and shared infrastructure.

This PLAN intentionally reflects the current implementation, including active capabilities and partial surfaces such as the watchdog recovery hooks that are present in code but not fully wired into the live runtime path.
