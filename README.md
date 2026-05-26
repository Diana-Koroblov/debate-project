# Debate Project

Debate Project is a multi-process CLI application that stages a structured AI debate on the question of extraterrestrial life. A parent judge process orchestrates two child debaters, enforces turn order through IPC queues, persists session state, rotates logs, tracks API budget usage, and emits a final judgment plus cost summary.

The current shipped runtime is configured for Gemini with `gemini-2.5-flash`, and the live debate path was validated in this repository on 2026-05-24 after fixing two runtime blockers: `.env` loading for Gemini API keys and Windows session-worker daemonization.

## Architecture

### Layered SDK Layout

```text
debate_project/
|
+-- src/debate_project/           Presentation layer
|   +-- cli.py                    Interactive menu and terminal orchestration
|   +-- menu.py                   Keyboard navigation
|   +-- render.py                 Live event/log rendering
|
+-- src/debate_sdk/sdk/           Core SDK layer
|   +-- session.py                Session bootstrap and streaming loop
|   +-- logstream.py              Log follower for CLI rendering
|   +-- pricing.py                Token and cost summaries
|
+-- src/debate_sdk/services/      Agent service layer
|   +-- base_agent.py             Shared process event loop
|   +-- child_agent.py            Debater behavior wrapper
|   +-- pro_agent.py              Pro-debate persona + Gemini
|   +-- con_agent.py              Con-debate persona + Gemini
|   +-- judge_agent.py            Parent judge orchestration
|   +-- judge_*_mixin.py          Decomposed judging, routing, and process logic
|   +-- gemini_mixin.py           Shared LLM interface
|   +-- web_search_mixin.py       Tavily search capabilities
|
+-- src/debate_sdk/shared/        Infrastructure layer
|   +-- gatekeeper.py             API orchestration singleton
|   +-- gatekeeper_*.py           Sub-systems for budget, traffic, and runtime
|   +-- watchdog.py               Health monitoring and process recovery hooks
|   +-- config.py                 Configuration loader
|   +-- config_utils.py           Strict JSON normalization/validation
|   +-- state_manager.py          Debate checkpoint persistence
|   +-- search_client.py          Tavily integration
|   +-- logger.py                 Structured logging setup
|   +-- process_utils.py          Process tree termination helpers
|
+-- config/                       Runtime configuration
+-- results/                      Logs, state, and cost artifacts
+-- docs/                         PRD, plan, TODO, prompt book, transcript
```

### Multi-Process IPC Boundaries

```text
			+-----------------------+
			|   CLI / SDK Session   |
			|  run_debate_session   |
			+-----------+-----------+
				    |
				    v
			+-----------------------+
			| ParentJudgeAgent      |
			| inbound/outbound q    |
			+----+-------------+----+
			     |             |
	     pro_inbound q   |             |   con_inbound q
			     v             v
		    +---------------+   +---------------+
		    | ProDebater    |   | ConDebater    |
		    | process       |   | process       |
		    +-------+-------+   +-------+-------+
			    |                   |
			    +--------+----------+
				     |
				     v
			   Parent inbound queue

Cross-cutting services:
- ApiGatekeeper wraps Gemini calls and token budget accounting.
- Watchdog monitors child PIDs and heartbeats.
- StateManager flushes ledger checkpoints to results/state/.
- Logging rotates structured logs in results/logs/.
```

## Setup

### Prerequisites

- Windows or another OS with Python 3.10 available
- `uv`
- A valid Gemini API key
- Optional Tavily API key for search augmentation

### Install

```powershell
uv python pin 3.10
uv venv --python 3.10
uv sync --dev
```

If you prefer the existing local virtual environment on Windows:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

### Configure Secrets

Create a local `.env` file from `.env-example` and fill in the keys:

```text
GOOGLE_API_KEY="your_gemini_api_key"
TAVILY_API_KEY="your_tavily_api_key"
```

Notes:

- `GOOGLE_API_KEY` is required for live debates.
- If the key is missing, the Gemini layer now logs an explicit exception message during initialization.
- `TAVILY_API_KEY` is optional for the current runtime because the debate loop does not hard-fail when search is unavailable.

## Running The Debate

### CLI Entry Points

```powershell
uv run debate-cli
```

or:

```powershell
uv run python -m debate_project
```

### CLI Workflow

1. Choose `Start debate`.
2. Select a number of rounds from the keyboard menu.
3. Watch live argument events and watchdog log messages stream in the terminal.
4. Review the final judgment and token cost table.
5. Inspect the generated JSON cost artifact in `results/`.

### Runtime Outputs

- `results/logs/agent_logs_*.log`: rotating structured runtime logs
- `results/state/session_<session_id>.state`: checkpointed ledger state
- `results/cost_summary_<session_id>.json`: cost breakdown artifact
- `docs/PROMPT_BOOK.md`: runtime prompt appendix
- `docs/DEBATE_TRANSCRIPT.md`: full generated 10-round transcript

## Configuration Reference

### `config/setup.json`

- `watchdog.timeout_seconds`: heartbeat timeout before forced recovery
- `watchdog.check_interval_seconds`: watchdog polling interval
- `debate.rounds`: upper bound exposed by the CLI, capped at 10 by the session layer
- `debate.model`: Gemini model used by pro, con, and judge agents
- `debate.pro_persona`: system prompt seed for the pro debater
- `debate.con_persona`: system prompt seed for the con debater
- `debate.adversarial_rules`: shared anti-concession and rebuttal directives
- `debate.formatting_instructions`: JSON output contract enforced in prompts

### `config/rate_limits.json`

- `requests_per_minute`: global Gemini traffic cap
- `concurrent_max`: simultaneous outbound API calls
- `queue_max_size`: pending request buffer ceiling
- `max_retries`: retry attempts for transient failures
- `backoff_base_seconds`: exponential backoff base delay
- `max_budget_tokens`: hard stop for cumulative projected token usage

### `config/logging_config.json`

- `log_directory`: rotating log directory
- `max_files`: maximum retained log files
- `max_lines_per_file`: FIFO rotation threshold per file
- `log_level`: structured logger verbosity

## Testing And Validation

### Quality Gates

```powershell
uv run ruff check .
uv run pytest tests/ --cov=src
```

### Runtime Validation Performed In This Repository

- Focused unit tests for `GeminiMixin`, debater agents, judge agent, and session runner
- Live one-round SDK smoke test
- Live debate validation after switching the default model to `gemini-2.5-flash`
- Full 10-round live execution progressed to round 8 before hitting the current Gemini free-tier request quota in this environment
- Deterministic offline 10-round transcript generation for the documentation artifact in `docs/DEBATE_TRANSCRIPT.md`

### Known Operational Notes

- The `google.generativeai` SDK emits a deprecation warning; migrating to `google.genai` is the next technical cleanup.
- Python 3.10 still works here but now emits an upstream support warning; Python 3.11 is the safer target going forward.
- The session worker must not run as a daemon on Windows because the judge process owns a `multiprocessing.Manager` and child worker processes.
- `run_with_retries` now respects provider-supplied `Please retry in ...s` guidance, but a full live 10-round debate still depends on available Gemini quota.

## Prompt Artifacts

- Runtime prompt appendix: `docs/PROMPT_BOOK.md`
- Full generated debate transcript: `docs/DEBATE_TRANSCRIPT.md` (deterministic offline documentation run)

## ISO/IEC 25010 Mapping

| Quality Characteristic | Repository Trait | Why It Fits |
| --- | --- | --- |
| Functional suitability | Typed IPC contracts and session orchestration | The system focuses on one bounded job: run a rule-governed debate and return a final judgment. |
| Performance efficiency | Gatekeeper throttling, bounded queues, capped log rotation | API usage, concurrency, and disk growth are explicitly limited. |
| Compatibility | CLI isolated from SDK orchestration | The same SDK session layer can support other front ends without rewriting debate logic. |
| Usability | Keyboard CLI, live event rendering, end-of-run cost summary | Operators can start and monitor debates without directly handling multiprocessing internals. |
| Reliability | Watchdog monitoring, state checkpoints, graceful budget fallback | The design anticipates stalled agents, partial failure, and resumable state. |
| Security | `.env` secrets, no hard-coded credentials, explicit API-key failure logging | Sensitive configuration is externalized and misconfiguration is surfaced clearly. |
| Maintainability | Small modules, mixin-based behavior split, <150 LOC discipline | Responsibilities are deliberately decomposed across focused files. |
| Portability | `uv`-managed environment and package entry points | The repo can be reproduced with pinned Python/tooling rather than ad hoc manual setup. |

## Repository Status

The final delivery checklist for documentation is completed by the root README, the prompt appendix, and the generated transcript artifact in `docs/`.

