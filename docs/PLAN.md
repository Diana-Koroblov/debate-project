# Architectural Design Document (PLAN) - AI Agent Debate

## 1. Architectural Overview & System Topography

### 1.1 Layered Architecture Model
The system is designed using a strict three-tier layered architecture to ensure modularity, testability, and separation of concerns.

1.  **Presentation Layer (CLI):** Thin wrappers that handle user input and terminal output. This layer is strictly prohibited from containing business logic. It consumes the SDK's public interfaces to initiate and monitor debates.
2.  **Core SDK Layer (Business Logic):** Located in `src/<package>/sdk/`, this is the heart of the system. It manages agent orchestration, state transitions, message routing, and the debate lifecycle.
3.  **Infrastructure Layer:** Handles external integrations, including LLM API clients, Web Search providers, and the File I/O system (logs and state persistence).

### 1.2 The SDK Priority Rule
All intelligence regarding *how* the debate flows resides within the SDK. The CLI or any future UI (web/mobile) acts only as a "dumb" consumer. This ensures that the core logic is fully testable in isolation and portable across different interfaces.

### 1.3 Multi-Process & IPC Model
To ensure true autonomy and fault tolerance, every agent (Pro, Con, and Parent) operates as a completely isolated, concurrent Operating System process.
*   **Isolation:** Memory spaces are independent; a memory leak or crash in one agent cannot corrupt another.
*   **Inter-Process Communication (IPC):** Communication is handled via OS-level pipes or queues (e.g., Python's `multiprocessing.Queue` or `Pipe`). 
*   **Asynchrony:** The system uses non-blocking I/O and event-driven patterns to manage message exchanges between the Parent and Child processes.

### 1.4 Project Directory Structure
The project strictly implements a modular and layered directory structure, ensuring a fixed footprint and proper package organization:


debate_project/
│
├── config/                         # Configuration environment files
│   ├── setup.json                  # Main application configurations
│   ├── rate_limits.json            # API rate limiting thresholds
│   └── logging_config.json         # Circular logging configuration
│
├── data/                           # Input/Static data files
│
├── docs/                           # Mandatory system documentation
│   ├── PRD.md                      # Product Requirements Document
│   ├── PLAN.md                     # Architectural Design Document (This file)
│   └── TODO.md                     # Micro-task tracking artifact
│
├── results/                        # Outputs and analytical tracking
│   └── logs/            
│       ├── agent_logs_01.log
│       ├── agent_logs_02.log
│       ...
│       └── agent_logs_20.log
│
├── src/                            # Bounded source code root directory
│   └── debate_sdk/                 # Core modular package
│       ├── __init__.py             # Package interface declaration
│       ├── main.py                 # Thin CLI controller (Presentation layer)
│       │
│       ├── sdk/                    # Core Business Logic Layer
│       │   ├── __init__.py
│       │   └── orchestrator.py     # Main debate loop engine
│       │
│       ├── services/               # Internal agent services
│       │   ├── __init__.py
│       │   ├── base_agent.py       # OOP abstract base agent class
│       │   ├── pro_agent.py        # Astrophysical stance process logic
│       │   ├── con_agent.py        # Skeptical stance process logic
│       │   └── judge_agent.py      # Final decision-making process logic
│       │
│       └── shared/                 # Infrastructure and shared utilities
│           ├── __init__.py
│           ├── gatekeeper.py       # Centered API rate limiter & queue
│           ├── watchdog.py         # PID daemon for process resilience
│           ├── config.py           # Bounded dynamic configuration manager
│           ├── constants.py        # Immutable variables layer
│           └── version.py          # Global version tracking module
│
├── tests/                          # Automated offline test suite
│   ├── conftest.py                 # Shared fixtures for mock engines
│   ├── unit/                       # Focused component test logic
│   └── integration/                # Full operational round flow verification
│
├── .env                            # Uncommitted API keys and credentials
├── .env-example                    # Committed placeholder keys blueprint
├── .gitignore                      # Security runtime ignores
├── pyproject.toml                  # Lock-step build and Ruff lint rules
└── uv.lock                         # Strictly deterministic package lockfile

---

## 2. Component Architecture (C4 Model & Structural Blueprints)

### 2.1 System Context & Container Level
The interaction flow follows a deterministic path:
`User -> CLI -> SDK (Orchestrator) -> Parent Agent -> Gatekeeper -> [LLM / Search API]`

### 2.2 Object-Oriented Design (OOP) & Inheritance Map
The agent system utilizes a hierarchy to maximize code reuse and enforce structural consistency.

*   **`BaseAgent` (Abstract Base Class):**
    *   `__init__(agent_id, config)`: Initializes process identity and IPC channels.
    *   `run()`: The main loop for the process.
    *   `handle_message(json_payload)`: Validates and routes incoming IPC packets.
    *   `log_token_usage(metadata)`: Standardized hook for the Token Economy component.
    *   `terminate()`: Graceful shutdown logic.

*   **Concrete Implementations:**
    *   **`ChildDebaterAgent` (Abstract):** Adds `search_tool` capabilities and argument generation logic.
        *   **`ProDebaterAgent`:** Implements astrophysical specific personas and logic.
        *   **`ConDebaterAgent`:** Implements skeptical/Fermi Paradox personas and logic.
    *   **`ParentJudgeAgent`:** Implements orchestration logic, turn management, history aggregation, and final decision-making.

---

## 3. Core Subsystems & Structural Interfaces

### 3.1 Centralized API Gatekeeper (`ApiGatekeeper`)
The `ApiGatekeeper` is a singleton-like controller that mediates all external network traffic.
*   **Rate Limiting:** Reads `config/rate_limits.json` to enforce RPS (Requests Per Second) and TPM (Tokens Per Minute) caps.
*   **Overflow Queue:** Implements a FIFO (First-In-First-Out) buffer. If a request hits a rate limit, it is queued and retried automatically once the window resets, preventing 429 errors from reaching the agents.
*   **Resilience:** Built-in exponential backoff for transient 5xx errors and hard timeouts (60s) for all requests.

### 3.2 Watchdog & Resilience Daemon
A dedicated background process monitors the health of the agent swarm.
*   **Monitoring:** Tracks the PID and "heartbeat" (last activity timestamp) of each agent process.
*   **Graceful Recovery:** If an agent becomes unresponsive:
    1.  The Watchdog kills the faulty process.
    2.  It retrieves the last valid state from the session logs.
    3.  It reinstantiates the agent, restores its context, and re-inserts it into the debate loop.

### 3.3 Structured Logging & Token Economy
*   **FIFO Rotation Policy:** The logger uses a circular rotation defined in `logging_config.json`.
    *   Max files: 20.
    *   Max lines per file: 500.
    *   Old logs are automatically purged to maintain a fixed disk footprint.
*   **Token Tracking Schema:** Every API transaction generates a record:
    ```json
    {
      "request_id": "uuid",
      "agent_id": "pro_agent",
      "model": "gpt-4o",
      "usage": { "input": 450, "output": 1200 },
      "latency_ms": 1450,
      "timestamp": "ISO8601"
    }
    ```

---

## 4. Communication Protocols & Data Schemas (JSON Contracts)

### 4.1 `ChildToParentMessage`
```json
{
  "type": "argument",
  "agent_id": "string",
  "round_number": "int",
  "payload": {
    "text": "string",
    "search_queries": ["query1", "query2"],
    "citations": [{"title": "str", "url": "str"}]
  }
}
```

### 4.2 `ParentToChildRouter`
```json
{
  "type": "turn_prompt",
  "recipient_id": "string",
  "history": ["msg1", "msg2"],
  "game_status": "ACTIVE|ENDING"
}
```

### 4.3 `FinalJudgmentSchema`
```json
{
  "winner_id": "string",
  "differential_score": "float", 
  "justification": [
    {"point": "Logical Consistency", "evidence": "text"},
    {"point": "Rhetorical Strength", "evidence": "text"}
  ]
}
```

---

## 5. Implementation Constraints & ADRs

### 5.1 Modularization Strategy (150 LOC Limit)
To enforce the 150-line file limit, the system will use:
*   **Mixins:** Splitting complex logic (like search tools) into separate classes.
*   **Strategy Pattern:** Encapsulating different LLM provider logics into small, focused adapter files.
*   **Utility Separation:** Aggressive use of helper functions in a dedicated `utils/` directory.

### 5.2 Testability Strategy (TDD)
*   **Mock Engines:** All external calls (OpenAI, Tavily) will be intercepted by a `MockEngine` during testing.
*   **Coverage Target:** 85% statement and branch coverage is mandatory. Tests will be located in `tests/` and run via `pytest`.
*   **CI/CD:** Linter checks (`Ruff`) must pass with 0 errors before any merge.

### 5.3 Environment & Dependency Management
*   **Secrets:** Managed via `.env` (git-ignored) with a mandatory `.env-example`.
*   **Tooling:** `uv` is the exclusive tool for environment setup (`uv venv`), dependency installation (`uv pip sync`), and script execution (`uv run`).
