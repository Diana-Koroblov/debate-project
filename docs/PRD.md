# Product Requirements Document (PRD) - AI Agent Debate: Alien Existence

## 1. Project Overview & Context

### 1.1 Project Goal
The "Autonomous AI Agent Debate" project aims to architect and implement a robust, multi-process system where autonomous AI agents engage in a structured, high-stakes intellectual contest. The primary objective is to build a platform that demonstrates sophisticated orchestration of LLM-based agents, moving beyond simple chat interfaces into the realm of complex, rule-governed autonomous systems.

### 1.2 The Research Challenge: Alignment Bias & Orchestration
A significant hurdle in multi-agent LLM systems is "people-pleasing" or alignment bias—the tendency for LLMs to seek consensus and avoid friction. This project seeks to overcome this by:
*   **Forced Contradiction:** Engineering prompts and personas that demand rigorous disagreement and logical refutation.
*   **Process Isolation:** Using a Multi-Process architecture to ensure that each agent's internal state and execution environment are strictly separated.
*   **Orchestrated Flow:** Solving the coordination problem of multiple asynchronous entities communicating via a centralized authority (the Parent Agent) to prevent race conditions or "hallucinated turns."

### 1.3 Target Audience
*   **QA Engineers:** To study the reliability of multi-process AI systems and edge-case handling in autonomous conversations.
*   **AI Researchers:** Investigating agentic behavior, debate dynamics, and methods to mitigate LLM consensus bias.
*   **Systems Developers:** Looking for a blueprint on Inter-Process Communication (IPC) applied to LLM workflows.

---

## 2. Goals & Measurable KPIs

### 2.1 Strategic Goals
*   **Systemic Autonomy:** The debate must proceed from start to finish without human intervention.
*   **Logical Rigor:** Arguments must be grounded in the specific personas provided (Astrophysical vs. Skeptical).
*   **Architectural Integrity:** Successful implementation of a Parent-Child communication model via IPC.

### 2.2 Technical & Quality KPIs
*   **Operational Success:**
    *   100% adherence to JSON communication schema.
    *   Zero unhandled process crashes during a full debate cycle.
    *   Completion of exactly 10 full rounds.
*   **Code Quality Standards:**
    *   **Modularity:** Maximum 150 lines of code (LOC) per file to ensure extreme maintainability and focus.
    *   **Testing:** Minimum 85% unit and integration test coverage.
    *   **Linting:** Exactly 0 errors or warnings from the `Ruff` linter.
*   **Performance:**
    *   Agent response times must stay within defined timeout limits (e.g., < 60 seconds).

---

## 3. Agent Architecture & Debate Rules (Functional Requirements)

### 3.1 Participant Personas
*   **Agent A ("Pro"):** A specialist in scientific, statistical, and astrophysical arguments. This agent utilizes the Drake Equation, exoplanet discovery data, and extreme-environment biology to argue that life elsewhere is a statistical certainty.
*   **Agent B ("Con"):** A scientific skeptic focused on the Fermi Paradox and the "Great Filter" theory. This agent specializes in debunking myths, highlighting the fragility of life-sustaining conditions, and refuting pseudo-science/UFO claims.
*   **Parent Agent (Judge/Moderator):** The "Brain" of the operation. It enforces rules, tracks turns, validates message formats, and provides the final ruling.

### 3.2 Message Routing & Communication Rule
*   **Indirect Communication:** Child agents are strictly prohibited from direct communication.
*   **Pathing:** All messages must follow the path: `Child -> Parent -> Child`. The Parent Agent acts as the router, logging the history and sanitizing inputs/outputs.
*   **Format:** All inter-process communication (IPC) must be conducted in a structured **JSON** format. This allows for precise monitoring of token usage, metadata tracking (e.g., processing time), and automated validation.

### 3.3 Multi-Process Management (IPC)
The system shall treat every agent as an independent Operating System process.
*   **Isolation:** If Agent A crashes, the Parent Agent and Agent B remain unaffected.
*   **IPC Mechanism:** Communication shall be handled via OS-level pipes, queues, or sockets, ensuring a true decoupled architecture.

### 3.4 Procedural Enforcement
*   **Turn Counter:** The system enforces a strict turn-based logic. A "Round" consists of an argument from Agent A and a counter-argument/rebuttal from Agent B (or vice versa, managed by the Parent).
*   **Round Limit:** The debate will execute exactly 10 full rounds .
*   **SDK Layer Priority:** All business logic for routing, state management, and the Watchdog must reside within a dedicated SDK layer, separating the "logic" from the "interface" (CLI).
*   **Object-Oriented Design (OOP):** The system must strictly adhere to OOP principles. Shared agent functionalities (e.g., API communication, state tracking) must be abstracted into a common `BaseAgent` class or Mixins to prevent code duplication (DRY).

### 3.5 Real-Time Intelligence: Web Search Tool
Child agents **must** be equipped with a Web Search Tool. This allows them to:
*   Fetch recent astrophysical papers or news.
*   Verify specific skeptical claims or historical data.
*   Provide citations, grounding the debate in real-world evidence rather than purely generative speculation.

### 3.6 Conduct & Phrasing
*   **Respectful Debate:** Agents must adhere to a strict culture of intellectual debate. No abusive language, ad hominem attacks, or derogatory remarks.
*   **PC Alignment:** Phrasing must remain professional and "Politically Correct" to ensure the focus remains on the scientific merits of the arguments.

### 3.7 Debate Dynamics & Rebuttals
* **Direct Rebuttal Requirement:** Agents must explicitly acknowledge and reference the specific claim made by their opponent in the preceding turn before introducing new arguments or moving the conversation forward (e.g., "While the vastness of the galaxy makes statistical arguments tempting, the lack of observable evidence...").
* **Anti-Concession Protocol:** Agents must resolutely maintain their assigned stance. They are strictly forbidden from conceding, folding, or "people-pleasing," even if the opposing argument appears logically sound. The debate must remain genuinely adversarial at all times.
---

## 4. Judging Mechanism & Final Decision

### 4.1 The Final Ruling Process
Once the predefined rounds are completed, the Parent Agent aggregates the entire conversation history from its state management system and performs a comprehensive analysis.

### 4.2 The No-Tie Rule
The Parent Agent is strictly forbidden from declaring a "Tie." 
*   **Decisiveness:** A winner must be declared.
*   **Differential Scoring:** The judge must provide a score (e.g., 0-100) that reflects a clear gap between the winner and the loser.

### 4.3 Judging Criteria
The ruling is based on:
1.  **Persuasiveness:** How effectively did the agent utilize evidence and logic?
2.  **Rhetorical Ability:** The quality of the counter-arguments and the ability to identify flaws in the opponent's logic.
3.  **Adherence to Rules:** Did the agent stay in character and respect the turn-based structure?
*Note: The judge prioritizes the strength of the argument presented over the absolute "truth" of the existence of aliens.*

---

## 5. System Requirements & Protection Mechanisms

### 5.1 Timeout & Resilience
*   **Response Timeouts:** Every API call to an LLM provider or Web Search tool must have a hard timeout. If an agent exceeds this, the Parent Agent must handle the exception (e.g., forfeiting a turn or retrying).
*   **Watchdog (Keep-Alive):** A background monitoring process (Watchdog) must track the PID (Process ID) of every agent. If a process stops responding or consumes excessive resources, the Watchdog will terminate and restart it (Graceful Recovery).
*   **API Gatekeeper & Rate Limiting:** All external API calls (LLM and Search) must pass through a centralized Gatekeeper. Rate limits must be dynamically loaded from a configuration file (e.g., `rate_limits.json`). If limits are reached, the Gatekeeper must place requests in a queue (FIFO) rather than dropping them or crashing.

### 5.2 Security & Environment
*   **Secrets Management:** No hardcoded API keys. All credentials (OpenAI, Anthropic, Tavily, etc.) must be stored in a `.env` file.
*   **Documentation:** A `.env-example` must be provided to guide users on required variables.

### 5.3 Dependency Management
*   **Tooling:** `uv` is the mandatory package manager for this project.
*   **Environment:** All dependencies, virtual environments, and script execution must be managed via `uv` (e.g., `uv pip install`, `uv run`).

### 5.4 Structured Logging
* **FIFO Log Management:** The system must implement structured logging defined via configuration files. It must follow a FIFO rotation policy (e.g., maintaining a maximum of 20 log files, with each file restricted to 500 lines) to prevent memory and disk overflow.

### 5.5 Token Economy & Cost Management
* **Gatekeeper Token Tracking:** The centralized Gatekeeper must actively monitor and log the exact number of Input and Output tokens consumed during each API call in real-time.
* **Economic Blocking Layer:** A hard budget limit must be defined in the configuration files. The Gatekeeper is responsible for enforcing this limit and blocking further API requests if the predefined budget is reached, thereby preventing unexpected costs.
* **Context Engineering & Optimization:** The system must actively manage the Context Window to prevent token bloat. This includes enforcing concise JSON communication and filtering redundant conversation history before passing it to the LLMs.
* **Cost Breakdown Analysis:** The system must generate token usage logs sufficient for a comprehensive post-debate cost analysis. The final project documentation must include a detailed cost breakdown table (calculating total Input/Output tokens and overall cost based on the specific LLM pricing model) and document any active optimization strategies implemented.

---

## 6. Assumptions, Dependencies & Out of Scope

### 6.1 Out of Scope
*   **Graphical User Interface (GUI):** This project focuses on the CLI, the SDK, and the underlying process architecture. A web-based dashboard is not required.
*   **Multi-Topic Support:** While the architecture should be generic, the initial implementation and testing are strictly scoped to the "Alien Existence" debate.

### 6.2 Dependencies
* **LLM Provider:** Google Gemini (via Gemini CLI and API) for high-reasoning tasks and agent orchestration.
* **Search API:** A tool-accessible search engine API to fulfill the mandatory web search tool requirement (e.g., enabling agents to cite real-time astrophysical data).
* **Python Environment:** Python 3.10+ to support modern multiprocessing primitives and the required Ruff linter targets.

### 6.3 Assumptions
*   The user has a stable internet connection for API requests.
*   Sufficient API credits are available for the 10-round duration.
*   The OS supports standard IPC primitives (Unix-like or Windows-specific multiprocessing).
