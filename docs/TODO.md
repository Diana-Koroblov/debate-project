# Project TODO & Task Tracker - AI Agent Debate

This document serves as the granular Agile project tracker for the "Autonomous AI Agent Debate" system. It breaks down architectural components from `PRD.md` and `PLAN.md` into atomic, actionable micro-tasks.

---

## Phase 1: Environment & Repository Setup

**Priority:** High | **Status:** Pending
**Definition of Done (DoD):** Repository initialized, `uv` configured, directory structure in place, Ruff and pytest configured successfully.

* [ ] 1.1 Initialize project directory and git repository.
* [ ] 1.2 Initialize `uv` as the exclusive package manager (`uv init`).
* [ ] 1.3 Create the mandatory folder structure aligned with PLAN.md:
* [ ] `src/debate_sdk/sdk/`
* [ ] `src/debate_sdk/services/`
* [ ] `src/debate_sdk/shared/`
* [ ] `tests/unit/` and `tests/integration/`
* [ ] `docs/`
* [ ] `config/`
* [ ] 1.4 Create `.env-example` with placeholder keys (`GOOGLE_API_KEY`, `TAVILY_API_KEY`).
* [ ] 1.5 Configure `pyproject.toml`:
* [ ] Add Ruff linter settings (strict rule enforcement, 0 errors allowed).
* [ ] Add pytest and pytest-cov settings (target: 85% `fail_under`).
* [ ] 1.6 Create a global `version.py` file to manage semantic versioning starting at 1.00.

---

## Phase 2: Configuration & Gatekeeper (The API Guard)

**Priority:** High | **Status:** Pending
**Definition of Done (DoD):** Gatekeeper successfully routes requests, throttles traffic based on configuration, validates configuration versions, and achieves >85% test coverage. No file exceeds 150 LOC.

* [ ] 2.1 Create the configuration file `config/rate_limits.json`.
* [ ] 2.2 Implement the JSON configuration parser utility.
* [ ] 2.3 Write the `ApiGatekeeper` singleton/controller class structure.
* [ ] 2.4 Implement rate limit logic (Requests Per Second and Tokens Per Minute).
* [ ] 2.5 Implement the FIFO overflow queue for handling rate-limited requests without dropping them.
* [ ] 2.6 Implement exponential backoff logic for transient API failures.
* [ ] 2.7 Implement token tracking data capture (Model ID, Input/Output Tokens, Latency).
* [ ] 2.8 Implement startup compatibility validation between configuration `version` keys and `version.py`.
* [ ] 2.9 Write isolated unit tests for `ApiGatekeeper` mocking API limits and verifying queue behavior.

---

## Phase 3: Logging & Watchdog Daemon

**Priority:** High | **Status:** Pending
**Definition of Done (DoD):** Logs rotate correctly. Watchdog successfully detects stuck processes, kills them, and restarts them.

* [ ] 3.1 Create `config/logging_config.json`.
* [ ] 3.2 Implement a custom logger utilizing a FIFO circular rotation policy (Max 20 files, Max 500 lines per file).
* [ ] 3.3 Implement the `Watchdog` background daemon class.
* [ ] 3.4 Add logic to monitor child process PIDs and track "heartbeat" timestamps.
* [ ] 3.5 Implement graceful termination (kill) for unresponsive processes.
* [ ] 3.6 Implement state recovery logic to reinstantiate a process from session logs.
* [ ] 3.7 Write integration tests simulating a hanging process to verify the Watchdog's kill-and-restart sequence.

---

## Phase 4: OOP Base Agent & IPC Protocol

**Priority:** High | **Status:** Pending
**Definition of Done (DoD):** `BaseAgent` class supports cross-process communication via OS pipes/queues, and parses JSON schemas perfectly.

* [ ] 4.1 Define the `BaseAgent` abstract base class.
* [ ] 4.2 Implement OS-level Inter-Process Communication (IPC) primitives (e.g., queues/pipes) in the base constructor.
* [ ] 4.3 Implement the main `run()` event loop to listen for incoming IPC messages.
* [ ] 4.4 Define the abstract `handle_message` method.
* [ ] 4.5 Implement standard JSON payload validation for incoming messages.
* [ ] 4.6 Implement a standardized `log_token_usage` hook to interface with the `ApiGatekeeper`.
* [ ] 4.7 Write unit tests validating IPC message serialization and deserialization across a mocked process boundary.

---

## Phase 5: Child Agents (Pro & Con) & Tools

**Priority:** Medium | **Status:** Pending
**Definition of Done (DoD):** Both agents generate distinct arguments, utilize the search tool, and format outputs in the required JSON schemas.

* [ ] 5.1 Implement the Web Search Tool wrapper interacting with the Search API.
* [ ] 5.2 Define the `ChildDebaterAgent` abstract class inheriting from `BaseAgent`.
* [ ] 5.3 Inject search tool capabilities into `ChildDebaterAgent` using Mixins or direct composition.
* [ ] 5.4 Implement the `ProDebaterAgent` subclass with its specific system prompt (Astrophysical, statistical certainty).
* [ ] 5.5 Implement the `ConDebaterAgent` subclass with its specific system prompt (Fermi Paradox, skepticism).
* [ ] 5.6 Implement prompt logic enforcing "Direct Rebuttal" and "Anti-Concession" behavioral rules.
* [ ] 5.7 Write unit tests validating that tool executions trigger correctly and JSON output schemas are strictly followed.

---

## Phase 6: Parent Judge & Orchestration

**Priority:** High | **Status:** Pending
**Definition of Done (DoD):** Parent agent correctly orchestrates exactly 10 rounds and issues a structured, tie-free judgment.

* [ ] 6.1 Implement the `ParentJudgeAgent` class inheriting from `BaseAgent`.
* [ ] 6.2 Implement state management to aggregate the full conversation history.
* [ ] 6.3 Implement the strict turn counter (enforcing exactly 10 rounds).
* [ ] 6.4 Implement message routing logic (`Child -> Parent -> Child`).
* [ ] 6.5 Formulate the `FinalJudgmentSchema` to parse the judge's final decision.
* [ ] 6.6 Implement the final judging prompt enforcing the "No-Tie" rule and requiring a differential score.
* [ ] 6.7 Write integration tests simulating a full round, verifying correct routing and state aggregation.

---

## Phase 7: CLI Interface & Final Delivery

**Priority:** Medium | **Status:** Pending
**Definition of Done (DoD):** CLI menu successfully starts the debate using keyboard inputs, reads output from the SDK, and visualizes the process. All quality KPIs are met.

* [ ] 7.1 Build the interactive, menu-driven CLI using keyboard selection navigation for user input.
* [ ] 7.2 Implement hooks in the CLI menu to spawn the `ParentJudgeAgent` process via the SDK.
* [ ] 7.3 Implement terminal visualization of the live debate (reading from the Parent's state/logs).
* [ ] 7.4 Create an end-of-debate summary view extracting token usage data and calculating estimated API costs.
* [ ] 7.5 Execute a full end-to-end system test.
* [ ] 7.6 Write the comprehensive `README.md` user manual, including installation guides, architecture diagrams, and cost metrics.
* [ ] 7.7 Perform a final code audit: Verify no `.py` file exceeds the 150 LOC limit.
* [ ] 7.8 Run the final test suite and linter via `uv run` to ensure 85% coverage and 0 Ruff errors.