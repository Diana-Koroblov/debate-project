# Project TODO & Task Tracker - AI Agent Debate

This document serves as the granular Agile project tracker for the "Debate Project" system. It breaks down architectural components from `PRD.md` and `PLAN.md` into atomic, actionable micro-tasks.

---

## Phase 1: Environment & Repository Setup
**Priority:** High | **Status:** Pending
**Definition of Done (DoD):** Git repository initialized with a secure framework. `uv` established as the exclusive package and environment manager, executing lockfile synchronization cleanly. Directory hierarchy completely constructed matching PLAN.md. Configuration files initialized with explicit semantic versions (starting at 1.00), and `pyproject.toml` injected with strict, non-bypassable compilation rules for Ruff (0 errors) and Pytest-cov (minimum 85% enforcement).

### 1.1 Local Workspace & Version Control Genesis
- [x] 1.1.1 Create a comprehensive `.gitignore` file at the root layer to prevent temporary or runtime assets from entering version control.
- [x] 1.1.2 Explicitly add operational ignore targets to `.gitignore`: `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.venv/`, `.env`, and dynamic operating system artifacts like `.DS_Store`.

### 1.2 Toolchain & Environment Optimization via `uv`
- [x] 1.2.1 Initialize the workspace infrastructure natively leveraging the mandatory `uv` package manager (`uv init --lib`).
- [x] 1.2.2 Create a fully isolated Python virtual environment bound specifically to the workspace using toolchain controllers (`uv venv --python 3.10`).
- [x] 1.2.3 Verify runtime accessibility to ensure all subsequent python or utility calls flow strictly through the managed environment launcher (`uv run`).
- [x] 1.2.4 Generate the structural initialization lockfile (`uv.lock`) to act as the absolute, deterministic source of truth for runtime dependencies.

### 1.3 Directory Topography Serialization (Layout Generation)
- [x] 1.3.1 Construct the mandatory system configuration container directory at `config/`.
- [x] 1.3.2 Construct the structured system metadata output tracking directory at `results/` along with its sub-folder `results/logs/`.
- [x] 1.3.3 Create the localized data ingestion layer directory at `data/`.
- [x] 1.3.4 Build the explicit layered package container framework within the source branch directory:
  - [x] Create `src/debate_sdk/sdk/` to house the core orchestration business logic layers.
  - [x] Create `src/debate_sdk/services/` to capture concrete multi-process agent worker declarations.
  - [x] Create `src/debate_sdk/shared/` to establish unified utilities, API gatekeepers, and watchdog structures.
- [x] 1.3.5 Set up the decoupled testing matrix layer directory by constructing `tests/unit/` and `tests/integration/` test directories.
- [x] 1.3.6 Place empty, structural initialization modules (`__init__.py`) inside the package root and every single lower sub-directory to validate standard Python package lookups.

### 1.4 Cyber-Security Protection & Secret Management Blueprints
- [x] 1.4.1 Create the local operational runtime environment credentials file `.env` at the project root layer.
- [x] 1.4.2 Inject placeholder variable variables into the uncommitted file: `GOOGLE_API_KEY="your_gemini_api_key_here"` and `TAVILY_API_KEY="your_search_api_key_here"`.
- [x] 1.4.3 Create the mandatory, public-facing blueprint template file named `.env-example` at the root layer.
- [x] 1.4.4 Mirror identical key signatures into `.env-example` utilizing empty strings or dummy data to guide configuration setups without exposing active development keys.

### 1.5 Strict Build & Code Quality Configuration Injectors (`pyproject.toml`)
- [x] 1.5.1 Open `pyproject.toml` and verify the core structural metadata block containing project name, initial version string ("1.00"), and python targets ("py310").
- [x] 1.5.2 Add the explicit `[tool.ruff]` linter configuration block specifying a conservative code style line-length cap (`line-length = 100`).
- [x] 1.5.3 Populate the `[tool.ruff.lint]` array parameter to explicitly select and activate mandatory rulesets: Pyflakes ("F"), PEP 8 Styles ("E", "W"), isort imports sorting ("I"), naming conventions ("N"), and simplified comprehensions ("C4", "SIM").
- [x] 1.5.4 Define the absolute `[tool.coverage.report]` block injectively enforcing the strict compliance constraint: `fail_under = 85`.
- [x] 1.5.5 Configure the target coverage execution properties block (`[tool.coverage.run]`) explicitly omitting non-logical paths like `src/main.py` or test files from testing calculations.

### 1.6 Global Semantic Versioning Layer Core
- [x] 1.6.1 Create the specialized tracking module at `src/debate_sdk/shared/version.py`.
  - [x] 1.6.1.1 Verify that `version.py` remains strictly under 150 LOC; if the file exceeds this boundary, aggressively modularize and split the logic into separate components (e.g., using Mixins, Utilities, or Strategy files).
- [x] 1.6.2 Declare the immutable, explicit string global token inside the module: `__version__ = "1.00"`.
- [x] 1.6.3 Inject a standardized docstring at the head of `version.py` documenting the technical change logging mechanics of the system framework.

### 1.7 Verification & Validation Framework Baseline
- [x] 1.7.1 Execute the initial codebase lint validation process natively through the workspace client wrapper (`uv run ruff check .`).
- [x] 1.7.2 Assert that the toolchain yields exactly 0 code style errors, warnings, or architectural syntax infractions.
- [x] 1.7.3 Create a baseline structural script testing file at `tests/conftest.py` to establish pytest hooks.
  - [x] 1.7.3.1 Verify that `conftest.py` remains strictly under 150 LOC; if the file exceeds this boundary, aggressively modularize and split the logic into separate components (e.g., using Mixins, Utilities, or Strategy files).
- [x] 1.7.4 Execute a mock local testing suite sweep (`uv run pytest`) ensuring the test orchestrator runs completely and interfaces correctly with the core environment.

---

## Phase 2: Configuration & Gatekeeper (The API Guard)
**Priority:** High | **Status:** Pending
**Definition of Done (DoD):** `ApiGatekeeper` fully implemented as the sole entry point for network I/O traffic. Safely throttles concurrent requests based on dynamic configurations, buffers overflow operations via a functional FIFO queue, manages lock-step token expenditures, and raises a validated `BudgetExceededException` upon limit violations. Achieves 0 Ruff errors, adheres to the 150 LOC constraint, and hits >85% test coverage via decoupled mock engines.

### 2.1 Configuration Infrastructure & Schema Scheming
- [x] 2.1.1 Create `config/rate_limits.json` populating mandatory metadata fields (`version`, `requests_per_minute`, `concurrent_max`).
- [x] 2.1.2 Implement the internal JSON configuration loader utility inside `src/debate_sdk/shared/config.py`.
  - [x] 2.1.2.1 Verify that `config.py` remains strictly under 150 LOC; if the file exceeds this boundary, aggressively modularize and split the logic into separate components (e.g., using Mixins, Utilities, or Strategy files).
- [x] 2.1.3 Build a strict validation schema parser to ensure the application configuration payload is intact at boot-time.
- [x] 2.1.4 Write the semantic initialization step in `shared/config.py` that raises a explicit `ValueError` if required telemetry configuration fields are missing.

### 2.2 Singleton Interface Construction (`ApiGatekeeper`)
- [x] 2.2.1 Create `src/debate_sdk/shared/gatekeeper.py` defining the core controller class `class ApiGatekeeper`.
  - [x] 2.2.1.1 Verify that `gatekeeper.py` remains strictly under 150 LOC; if the file exceeds this boundary, aggressively modularize and split the logic into separate components (e.g., using Mixins, Utilities, or Strategy files).
- [x] 2.2.2 Implement a thread-safe Singleton instantiation pattern or secure dynamic constructor reference mapping configuration constants.
- [x] 2.2.3 Build the master signature method `def execute(self, api_call, *args, **kwargs)` acting as the comprehensive wrapper layer for all external endpoints.
- [x] 2.2.4 Integrate absolute runtime logging inside the execution target to ensure 100% of network traffic triggers detailed tracking logs.

### 2.3 Traffic Throttling, Rate Limiting & Concurrent Constraints
- [x] 2.3.1 Implement a lightweight sliding-window or token-bucket counter algorithm tracking active request frequencies (RPS/RPM).
- [x] 2.3.2 Design an active concurrency tracker utilizing operational locks or semaphores to cap simultaneous API invocations (`concurrent_max`).
- [x] 2.3.3 Build a precise internal delta evaluator to compute backoff intervals (`retry_after_seconds`) dynamically when traffic caps are breached.
- [x] 2.3.4 Ensure the throttling mechanism evaluates rate limit structures prior to releasing the execution thread to external providers.

### 2.4 Bounded Buffer Queue & Overflow Handling (FIFO Logic)
- [x] 2.4.1 Implement a thread-safe FIFO queue container to buffer incoming tasks when application constraints are momentarily saturated.
- [x] 2.4.2 Set a concrete maximum queue depth boundary parameter fetched directly from configuration variables.
- [x] 2.4.3 Design a proactive backpressure alert loop that drops incoming operations or triggers system errors if the underlying overflow queue hits maximum capacity limits.
- [x] 2.4.4 Implement an automated loop background dispatcher that sequentially de-queues and fires pending operations once token bucket windows reset.

### 2.5 Resilient Transient Error Handling & Backoff Protocols
- [x] 2.5.1 Enclose external network execution instances in a robust try-except wrapper targeting common transient network exceptions (5xx errors, HTTP Status 429).
- [x] 2.5.2 Implement an exponential backoff mathematical calculation loop modifying subsequent retry pause delays.
- [x] 2.5.3 Inject a strict `max_retries` counter loop boundary into the retry routine to prevent infinite system blocking.
- [x] 2.5.4 Ensure that terminal connection errors that survive all retry attempts are formatted into clean, un-nested system error objects.

### 2.6 Token Economy Guardrails & Custom Financial Exceptions
- [x] 2.6.1 Create `src/debate_sdk/shared/exceptions.py` defining `class BudgetExceededException(Exception)`.
  - [x] 2.6.1.1 Verify that `exceptions.py` remains strictly under 150 LOC; if the file exceeds this boundary, aggressively modularize and split the logic into separate components (e.g., using Mixins, Utilities, or Strategy files).
- [x] 2.6.2 Implement tracking state variables inside the Gatekeeper module to accumulate running counts of Input/Output tokens.
- [x] 2.6.3 Build an active compliance validator evaluating whether `tracked_consumption + projected_cost > max_budget_tokens`.
- [x] 2.6.4 Force the Gatekeeper to instantly raise `BudgetExceededException` and block network access the moment financial caps are crossed.

### 2.7 Global Runtime Version Compliance Checks
- [x] 2.7.1 Write a validation utility that automatically cross-checks the string value of the `version` property inside `rate_limits.json` against `src/debate_sdk/shared/version.py` at boot.
- [x] 2.7.2 Configure the application startup routine to execute this check immediately during module initialization.
- [x] 2.7.3 Design a targeted initialization interceptor that logs a warning or raises a version mismatch exception if the configuration template is outdated.

### 2.8 Component Testing & Mock Endpoint Simulation (TDD Suite)
- [ ] 2.8.1 Create the comprehensive component verification test file at `tests/unit/test_gatekeeper.py`.
  - [ ] 2.8.1.1 Verify that `test_gatekeeper.py` remains strictly under 150 LOC; if the file exceeds this boundary, aggressively modularize and split the logic into separate components (e.g., using Mixins, Utilities, or Strategy files).
- [ ] 2.8.2 Write a test leveraging local fixtures to assert that sequential calls exceeding the RPM thresholds are successfully delayed and queued via FIFO without dropping data.
- [ ] 2.8.3 Build a localized unit test mapping a simulated HTTP 503 error, verifying that the exponential backoff framework executes exactly the configured number of retry iterations before returning a failure.
- [ ] 2.8.4 Write a validation test mocking high token payload emissions, asserting that `BudgetExceededException` triggers properly and blocks the pipeline thread.

---

## Phase 3: Logging & Watchdog Daemon
**Priority:** High | **Status:** Pending
**Definition of Done (DoD):** Logger enforces strict FIFO boundary limits. Watchdog independently catches, terminates, and fully restores a stalled or hanging agent process without leaking OS resources or breaking the debate loop. All files strictly under 150 LOC.

### 3.1 Logging Infrastructure & FIFO Rotation
- [ ] 3.1.1 Create `config/logging_config.json` defining schema mappings for rotation parameters.
- [ ] 3.1.2 Initialize a custom Python logging handler that overrides standard file emissions.
- [ ] 3.1.3 Implement the strict 500-line limit per file tracking counter mechanism.
- [ ] 3.1.4 Implement the circular rotation logic (when file 20 hits 500 lines, purge file 1 via FIFO).
- [ ] 3.1.5 Write a unit test verifying that emitting 10,001 log lines creates exactly 20 files of 500 lines without disk bloating.

### 3.2 Watchdog Structure & Process Registration
- [ ] 3.2.1 Create the `Watchdog` background daemon class using `multiprocessing` or an independent thread.
  - [ ] 3.2.1.1 Verify that the file length remains strictly under 150 LOC; if the file exceeds this boundary, aggressively modularize and split the logic into separate components (e.g., using Mixins, Utilities, or Strategy files).
- [ ] 3.2.2 Implement a centralized cross-process dictionary or registry to map `agent_id` to its OS `PID`.
- [ ] 3.2.3 Build a dynamic storage schema for tracking "heartbeat" timestamps for each unique PID.
- [ ] 3.2.4 Implement a periodic loop (e.g., runs every 2 seconds) that checks if `current_time - last_heartbeat > timeout_threshold`.

### 3.3 Process Interruption & Graceful Termination
- [ ] 3.3.1 Implement a thread-safe telemetry method for agents to push active heartbeat signals to the tracker.
- [ ] 3.3.2 Design the forced-termination sequence using `os.kill(pid, signal.SIGKILL)` or `psutil` wrappers.
- [ ] 3.3.3 Implement cleanup logic to safely release OS pipes/queues associated with the killed PID to prevent zombie processes.
- [ ] 3.3.4 Log the precise timestamp and cause of the forced termination into the structured log layer.

### 3.4 State Recovery & Reinstantiation
- [ ] 3.4.1 Design a lightweight state serialization scheme that continuously backs up the debate context.
- [ ] 3.4.2 Implement the extraction utility to read and parse the last valid JSON packet from the backup session logs.
- [ ] 3.4.3 Write the re-spawning method to instantiate a fresh concrete agent process (`ProDebaterAgent` or `ConDebaterAgent`).
- [ ] 3.4.4 Inject the extracted history context back into the newly spawned process environment.
- [ ] 3.4.5 Re-register the new PID with the active communication channels and resume orchestration seamlessly.

### 3.5 Automated Verification & Mock Failure Tests
- [ ] 3.5.1 Write an integration test using `pytest` that spawns a mock agent process.
  - [ ] 3.5.1.1 Verify that the file length remains strictly under 150 LOC; if the file exceeds this boundary, aggressively modularize and split the logic into separate components (e.g., using Mixins, Utilities, or Strategy files).
- [ ] 3.5.2 Program the mock agent to deliberately hang (e.g., execute an infinite `time.sleep()`) to simulate an API timeout.
- [ ] 3.5.3 Assert that the Watchdog successfully detects the expired heartbeat threshold.
- [ ] 3.5.4 Assert that the original PID is dead and that a new PID has taken over the task.
- [ ] 3.5.5 Verify the recovered agent correctly reads the prior state and successfully completes a mock debate turn.

---

## Phase 4: OOP Base Agent & IPC Protocol
**Priority:** High | **Status:** Pending
**Definition of Done (DoD):** Abstract `BaseAgent` fully operational. Implements rigid, multi-process OS-level communication using isolated queues/pipes without race conditions. Enforces strict JSON structural contracts on all inbound/outbound payloads, maintains 0 code duplication, and hits >85% branch coverage via decoupled process testing.

### 4.1 Abstract Class Infrastructure (OOP & ABC)
- [ ] 4.1.1 Create `src/debate_sdk/services/base_agent.py` and import Python's abstract base class (`abc`) utilities.
  - [ ] 4.1.1.1 Verify that `base_agent.py` remains strictly under 150 LOC; if the file exceeds this boundary, aggressively modularize and split the logic into separate components (e.g., using Mixins, Utilities, or Strategy files).
- [ ] 4.1.2 Define `class BaseAgent(ABC)` and mark `handle_message` as an `@abstractmethod`.
- [ ] 4.1.3 Implement the base `__init__(self, agent_id: str, config_manager)` constructor tracking runtime state flags (e.g., `self.is_running`).
- [ ] 4.1.4 Ensure the class docstrings explicitly document the single-responsibility domain model of the base worker.

### 4.2 Inter-Process Communication (IPC Primitive Setup)
- [ ] 4.2.1 Integrate Python's `multiprocessing.Queue` (or `Pipe`) objects into the base agent constructor signatures.
- [ ] 4.2.2 Assign an isolated, non-shared input channel (`self.inbound_queue`) for the individual agent process to pull messages from.
- [ ] 4.2.3 Assign a secure outbound routing channel (`self.outbound_queue`) targeted strictly to the Parent Agent router interface.
- [ ] 4.2.4 Implement a robust, non-blocking encapsulation method for pushing typed dictionary objects into the OS pipeline.

### 4.3 The Autonomous Event Loop (`run()`)
- [ ] 4.3.1 Implement the master `run(self)` process target entry-point function.
- [ ] 4.3.2 Design the infinite event loop construct (`while self.is_running:`) handling OS runtime interrupts safely.
- [ ] 4.3.3 Implement blocking extraction (`self.inbound_queue.get(timeout=1.0)`) inside a try-except block to intercept `queue.Empty` events without consuming excessive CPU.
- [ ] 4.3.4 Create a graceful `terminate(self)` interface method setting `self.is_running = False` to support safe process teardowns.

### 4.4 Data Contracts & Schemas (JSON Payload Validation)
- [ ] 4.4.1 Create robust JSON interface model structures matching the communication schemas defined in PLAN.md (e.g., using `pydantic` or structured dictionary blueprints).
- [ ] 4.4.2 Implement a centralized `_validate_payload(self, raw_message: str)` string parser in the base class.
- [ ] 4.4.3 Wrap the payload deserialization step in a rigid `try/except (JSONDecodeError, ValidationError)` container to handle malformed strings.
- [ ] 4.4.4 Log invalid data structures straight to the Structured Logging system using the `ERROR` level and drop the malicious packet without breaking the loop execution state.

### 4.5 Token Economy Core Interface Hooks
- [ ] 4.5.1 Define a concrete `log_token_usage(self, input_tokens: int, output_tokens: int, latency_ms: float)` base method.
- [ ] 4.5.2 Implement internal logic inside this hook to instantiate a standardized telemetry message object containing timestamps and agent identity metadata.
- [ ] 4.5.3 Route this metric packet straight into the centralized `ApiGatekeeper` process layer tracking database/file logs.
- [ ] 4.5.4 Ensure all token tracking logic remains completely separated from generative prompt engineering routines.

### 4.6 Isolated Decoupled Verification (TDD Boundary Tests)
- [ ] 4.6.1 Write a dedicated unit testing script: `tests/unit/test_base_agent.py`.
  - [ ] 4.6.1.1 Verify that `test_base_agent.py` remains strictly under 150 LOC; if the file exceeds this boundary, aggressively modularize and split the logic into separate components (e.g., using Mixins, Utilities, or Strategy files).
- [ ] 4.6.2 Create a minimal concrete implementation of `BaseAgent` inside the test suite purely for boundary protocol isolation verification.
- [ ] 4.6.3 Construct a test case that populates a valid `ChildToParentMessage` JSON schema directly into the inbound channel queue.
- [ ] 4.6.4 Fire up the agent run block briefly, and assert that the object is parsed, validated, and safely hits the concrete `handle_message` execution hook.
- [ ] 4.6.5 Construct a failure test injecting broken, corrupt raw data, and assert that the contract validator drops the packet with 0 process system crashes.

---

## Phase 5: Child Agents (Pro & Con) & Tools
**Priority:** Medium | **Status:** Pending
**Definition of Done (DoD):** Concrete debater agent subclasses fully operational under strict Persona constraints. Successfully execute real-time internet search queries using independent tool calling, strictly enforce the Direct Rebuttal and Anti-Concession protocols via System Prompts, format outputs in lock-step with `ChildToParentMessage` JSON contract specifications, and pass 100% of functional prompt validation unit tests. No file exceeds 150 LOC.

### 5.1 Real-Time Intelligence Integration (Web Search Tool)
- [ ] 5.1.1 Build an abstract interface or wrapper module for the external Search API client within `src/debate_sdk/shared/`.
  - [ ] 5.1.1.1 Verify that the file length remains strictly under 150 LOC; if the file exceeds this boundary, aggressively modularize and split the logic into separate components (e.g., using Mixins, Utilities, or Strategy files).
- [ ] 5.1.2 Implement dynamic loading of Search API credentials from the `.env` context layer.
- [ ] 5.1.3 Construct the search execution mechanism with built-in input string sanitization.
- [ ] 5.1.4 Implement output parsing logic to format results into structured arrays containing strings of raw content text, source page titles, and reference URLs.
- [ ] 5.1.5 Add a hard timeout (e.g., < 15 seconds) per search network invocation to prevent pipeline blocking.

### 5.2 Intermediate Debater Abstraction (`ChildDebaterAgent`)
- [ ] 5.2.1 Create `src/debate_sdk/services/child_agent.py` defining `class ChildDebaterAgent(BaseAgent)`.
  - [ ] 5.2.1.1 Verify that `child_agent.py` remains strictly under 150 LOC; if the file exceeds this boundary, aggressively modularize and split the logic into separate components (e.g., using Mixins, Utilities, or Strategy files).
- [ ] 5.2.2 Integrate search capability into `ChildDebaterAgent` using direct composition or a reusable capability Mixin class (`WebSearchMixin`).
- [ ] 5.2.3 Implement the structural orchestration method allowing Gemini to output tool-call requests inside its structured response loop.
- [ ] 5.2.4 Build the automated serialization module converting agent argument responses into validated `ChildToParentMessage` JSON schemas.

### 5.3 Pro-Stance Agent Realization (`ProDebaterAgent`)
- [ ] 5.3.1 Create `src/debate_sdk/services/pro_agent.py` implementing `class ProDebaterAgent(ChildDebaterAgent)`.
  - [ ] 5.3.1.1 Verify that `pro_agent.py` remains strictly under 150 LOC; if the file exceeds this boundary, aggressively modularize and split the logic into separate components (e.g., using Mixins, Utilities, or Strategy files).
- [ ] 5.3.2 Formulate the explicit astrophysical specialist persona (Drake Equation, exoplanet statistical boundaries, extremophile biology data models).
- [ ] 5.3.3 Embed Gemini API client instantiation inside the initialization lifecycle.
- [ ] 5.3.4 Ensure the implementation does not embed any configurations directly into source text strings, routing model configurations straight from `setup.json`.

### 5.4 Con-Stance Agent Realization (`ConDebaterAgent`)
- [ ] 5.4.1 Create `src/debate_sdk/services/con_agent.py` implementing `class ConDebaterAgent(ChildDebaterAgent)`.
  - [ ] 5.4.1.1 Verify that `con_agent.py` remains strictly under 150 LOC; if the file exceeds this boundary, aggressively modularize and split the logic into separate components (e.g., using Mixins, Utilities, or Strategy files).
- [ ] 5.4.2 Formulate the explicit scientific skeptic persona (Fermi Paradox mechanics, Great Filter theories, physical constraints of space travel, myth debunking).
- [ ] 5.4.3 Embed Gemini API client execution targets mirroring the sibling agent's operational state to ensure a symmetrical design pattern.

### 5.5 Adversarial Rules & Behavioral Prompt Engineering
- [ ] 5.5.1 Write the "Direct Rebuttal" instruction section forcing the agent to systematically identify, quote, and log a contradiction against the opponent's prior argument block.
- [ ] 5.5.2 Write the "Anti-Concession Protocol" instruction explicitly forbidding the agent from utilizing agreeable terms, changing its stance, or people-pleasing.
- [ ] 5.5.3 Inject strict "Politically Correct" and professional linguistic rules into the system directives to maintain a civil culture of debate.
- [ ] 5.5.4 Enforce formatting guardrails demanding that all text generations strictly adhere to the defined raw JSON properties layout.

### 5.6 Functional Persona & Tool Testing (TDD Suite)
- [ ] 5.6.1 Create `tests/unit/test_child_agents.py` initializing offline pytest fixtures.
  - [ ] 5.6.1.1 Verify that `test_child_agents.py` remains strictly under 150 LOC; if the file exceeds this boundary, aggressively modularize and split the logic into separate components (e.g., using Mixins, Utilities, or Strategy files).
- [ ] 5.6.2 Write a test case utilizing a `MockEngine` to simulate a Search API response, asserting that the agent correctly parses the mock data payload.
- [ ] 5.6.3 Construct a validation test passing an opponent's message block to `ProDebaterAgent`, asserting that its generated output complies with the `ChildToParentMessage` structural contract.
- [ ] 5.6.4 Construct an identical validation test for `ConDebaterAgent`, verifying character consistency and compliance.
- [ ] 5.6.5 Assert that any runtime text emissions violating the schema format are dropped by the internal sdk exception-handlers without bringing down the running process thread.
---

## Phase 6: Parent Judge & Orchestration
**Priority:** High | **Status:** Pending
**Definition of Done (DoD):** `ParentJudgeAgent` successfully orchestrated as a centralized authority process. Enforces an unalterable loop of exactly 10 rounds, sanitizes and routes messages exclusively via the Parent-Child topology, processes Gemini-based evaluation via `FinalJudgmentSchema`, strictly outlaws ties by injecting a differential scoring mandate, and recovers gracefully from `BudgetExceededException`. 100% of end-to-end integration tests pass, and all files remain strictly under 150 LOC.

### 6.1 Orchestrator Process Initialization (`ParentJudgeAgent`)
- [ ] 6.1.1 Create `src/debate_sdk/services/judge_agent.py` implementing `class ParentJudgeAgent(BaseAgent)`.
  - [ ] 6.1.1.1 Verify that `judge_agent.py` remains strictly under 150 LOC; if the file exceeds this boundary, aggressively modularize and split the logic into separate components (e.g., using Mixins, Utilities, or Strategy files).
- [ ] 6.1.2 Initialize the Gemini API client specifically configured for high-reasoning evaluation tasks using parameters from `setup.json`.
- [ ] 6.1.3 Implement the constructor logic to accept input and outbound OS IPC queues for both child processes (Pro and Con).
- [ ] 6.1.4 Design a safe subprocess manager loop to spawn, track, and gracefully terminate the underlying child worker instances.

### 6.2 Centralized Session State & History Aggregation
- [ ] 6.2.1 Build an in-memory structured history ledger class inside the SDK layer to log conversation payloads chronologically.
  - [ ] 6.2.1.1 Verify that the file length remains strictly under 150 LOC; if the file exceeds this boundary, aggressively modularize and split the logic into separate components (e.g., using Mixins, Utilities, or Strategy files).
- [ ] 6.2.2 Implement a real-time append module that captures and serializes incoming `ChildToParentMessage` objects.
- [ ] 6.2.3 Enforce runtime history sanitation to strip any formatting anomalies or toxic string tokens before ledger insertion.
- [ ] 6.2.4 Integrate a persistent live-backup writer that flushes the history state into a backup file on every turn to support Watchdog recovery metrics.

### 6.3 Procedural Turn Management & Message Routing
- [ ] 6.3.1 Implement a strict step-counter tracking the total number of processed debate sequences (exactly 10 rounds).
- [ ] 6.3.2 Write the deterministic routing switch that blocks child-to-child traffic and forces the sequential pipeline layout: `Pro -> Parent -> Con` and `Con -> Parent -> Pro`.
- [ ] 6.3.3 Design the `ParentToChildRouter` JSON contract builder to bundle appropriate historical context snapshots into the next player's queue prompt.
- [ ] 6.3.4 Implement a Turn Watchdog ping mechanism inside the loop to verify an agent has updated its heartbeat upon receiving a routed turn.

### 6.4 The "No-Tie" Judging Engine & Schema Parsing
- [ ] 6.4.1 Formulate the core system evaluation directives instructing the judge to grade purely on persuasiveness, rhetoric, and rules adherence, ignoring absolute factual truth.
- [ ] 6.4.2 Embed the unyielding "Anti-Tie Protocol" into the final prompt context, forcing a clear winner declaration.
- [ ] 6.4.3 Implement a strict structural Pydantic contract or JSON schema matching `FinalJudgmentSchema` to extract `winner_id`, a mandatory numeric `differential_score`, and an array of granular justifications.
- [ ] 6.4.4 Build a < 150 LOC verification step for all judge-related business logic modules to maintain modularity.

### 6.5 Resilience, Budget Exceptions & Graceful Degradation
- [ ] 6.5.1 Enclose the entire orchestration routing loop inside a comprehensive try-except block targeting `BudgetExceededException`.
- [ ] 6.5.2 Implement the budget failure interceptor: when raised by the `ApiGatekeeper`, halt further child process loops immediately.
- [ ] 6.5.3 Write a fallback evaluation method that passes the partially accumulated history ledger directly to the judge process.
- [ ] 6.5.4 Force the judge to deliver a structured final decision based on the available history, clearly indicating that the debate was truncated due to exhaustion of runtime resources.

### 6.6 Automated Integration Testing (End-to-End Simulations)
- [ ] 6.6.1 Create the integration test suite script at `tests/integration/test_orchestration_flow.py`.
  - [ ] 6.6.1.1 Verify that `test_orchestration_flow.py` remains strictly under 150 LOC; if the file exceeds this boundary, aggressively modularize and split the logic into separate components (e.g., using Mixins, Utilities, or Strategy files).
- [ ] 6.6.2 Implement mock child fixtures that respond instantly with valid structured JSON packets to bypass network calls during base protocol verification.
- [ ] 6.6.3 Write a test case verifying that the orchestrator executes exactly 10 rounds and terminates smoothly.
- [ ] 6.6.4 Write a validation test mocking a token budget exhaustion event midway through round 4, asserting that the exception is caught, a winner is declared via partial history, and the OS processes shut down cleanly with 0 zombie states.

---

## Phase 7: CLI Interface & Final Delivery
**Priority:** Medium | **Status:** Pending
**Definition of Done (DoD):** Interactive CLI fully realized as a thin presentation layer, supporting full keyboard menu navigation. Successfully initiates and streams multi-process debate states in real-time, generates a complete post-debate Token Cost Breakdown, and passes 100% of final quality gates (0 Ruff errors, >85% test coverage, and 0 files exceeding 150 LOC). Mandatory README.md and Prompt Log fully compiled.

### 7.1 Interactive Terminal Menu Construction (UI/UX Layer)
- [ ] 7.1.1 Build the interactive terminal interface menu utilizing keyboard navigation (e.g., standard arrow keys using `inquirer` or manual key-loop polling).
  - [ ] 7.1.1.1 Verify that the file length remains strictly under 150 LOC; if the file exceeds this boundary, aggressively modularize and split the logic into separate components (e.g., using Mixins, Utilities, or Strategy files).
- [ ] 7.1.2 Ensure the presentation layer contains exactly 0 business or routing logic, delegating all invocation targets to the core SDK layer.
- [ ] 7.1.3 Implement input boundaries allowing the user to select parameters (e.g., number of rounds up to 10) dynamically parsed from setup frameworks.
- [ ] 7.1.4 Apply custom terminal styling (e.g., using `colorama` or ANSI escape codes) to clearly differentiate between Pro, Con, and Parent Agent messaging.

### 7.2 Live Stream Orchestration & Live Visualization
- [ ] 7.2.1 Build a thread-safe stdout streaming hook within the CLI to intercept and display ongoing IPC queue message transactions in real-time.
- [ ] 7.2.2 Implement a standard dynamic progress bar or loading spinner representing LLM thinking and search execution states.
- [ ] 7.2.3 Ensure that unexpected process terminations caught by the Watchdog are visualized smoothly in the terminal without breaking the screen alignment.

### 7.3 Token Cost Accounting & Analytical Summaries
- [ ] 7.3.1 Build the end-of-debate summary parser to read total transaction metrics from the structured Gatekeeper logs.
- [ ] 7.3.2 Implement a tabular data generator to render a complete Cost Breakdown matrix on the terminal screen (Input Tokens, Output Tokens, Total Costs).
  - [ ] 7.3.2.1 Verify that the file length remains strictly under 150 LOC; if the file exceeds this boundary, aggressively modularize and split the logic into separate components (e.g., using Mixins, Utilities, or Strategy files).
- [ ] 7.3.3 Apply the exact Google Gemini API pricing metrics (cost per million tokens) to ensure the mathematical calculations are precise.
- [ ] 7.3.4 Log the final economic summary report directly into a clean JSON tracking artifact inside the `results/` directory.

### 7.4 Final Quality Gates & Static Code Audits
- [ ] 7.4.1 Execute a comprehensive automated line-of-code (LOC) scan across all source files, ensuring exactly 0 `.py` files exceed 150 lines.
- [ ] 7.4.2 Run the final full test suite via `uv run pytest tests/ --cov=src` and assert that total branch and statement coverage meets or exceeds 85%.
- [ ] 7.4.3 Execute the final strict linter check via `uv run ruff check .` ensuring exactly 0 warnings or code style violations remain.
- [ ] 7.4.4 Verify that `.env` is completely omitted from the git tree tracking, and that a fully populated `.env-example` template is present.

### 7.5 Production Manual & Technical Documentation Delivery
- [ ] 7.5.1 Write the root-level `README.md` following the mandatory full user manual standard (Step-by-step setup, configuration reference, CLI workflows).
- [ ] 7.5.2 Embed clear text-based ASCII architecture diagrams mapping the Layered SDK layout and the Multi-Process IPC queue boundaries.
- [ ] 7.5.3 Create the mandatory Prompt Book appendix log documenting all core systemic and persona directives utilized across the development cycle.
- [ ] 7.5.4 Include a complete, unedited copy of a full 10-round debate script output dialogue directly inside the repository documentation stack.
- [ ] 7.5.5 Ensure the final README contains explicit theoretical mappings connecting system architecture traits to the international ISO/IEC 25010 product quality standards.
