# HarnessOS repository contract

HarnessOS does not implement a foundation model, model gateway, or replacement coding harness. It coordinates existing agent runtimes and defines how agents collaborate and converge on verified outcomes.

Keep runtime-specific behavior inside `src/harnessos/agents/`. The orchestration layer must make state transitions itself and must require independent verification evidence before marking a task complete. Protocol messages transfer concise structured state and artifact references, not conversation histories.

V1 uses Python, Pydantic, SQLite, YAML/Markdown configuration, subprocess/CLI runtime adapters, and pytest. Avoid adding orchestration frameworks, model gateways, queues, vector stores, or external infrastructure without a demonstrated requirement.
