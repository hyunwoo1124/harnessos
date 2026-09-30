# HarnessOS Design Document

## Product definition

HarnessOS is an agent-engineering layer for software repositories. It gives coding agents a clear, shared understanding of the repository's objectives, constraints, working practices, and reusable skills, and makes verification expectations explicit. It is not a foundation model, model gateway, provider, or replacement coding agent.

Users continue to work through the coding tool they choose, such as OpenCode, Claude Code, Cursor, or Codex. HarnessOS configures the repository so that supported tools discover the same core instructions and relevant skills from the directory where the user starts the agent.

OpenCode is an agent runtime and interface. Ollama and NVIDIA NIM are model providers that OpenCode can use. Provider and model selection remain in the user's agent tool configuration.

## Problem to solve

Coding agents often misread the objective, invent missing requirements, ignore repository conventions, overproduce generic text, or claim completion without useful evidence. HarnessOS should reduce those failures by making the engineering contract and task-specific skills discoverable and actionable across agent tools.

## V0.2 user experience

1. A user installs or checks out HarnessOS, either globally or inside a project folder such as `network-scanner/harnessos/`.
2. The user runs the HarnessOS setup utility for the project root. This is an installation and health-check command, not the normal task interface.
3. Setup detects the selected HarnessOS bundle and creates non-destructive links from project-root agent instruction/skill locations to the canonical bundle.
4. The user changes directory to the project root and starts their native tool, for example `opencode`.
5. The agent reads the shared instructions, the project's own instructions, and relevant skills, then works and runs the repository's checks.

The working directory is part of the contract. If an agent starts in the HarnessOS source repository, HarnessOS development instructions apply. If it starts in a consuming project, that project's root instructions and configured HarnessOS links apply. Merely storing HarnessOS in a nested folder does not make that folder the agent's instruction root.

## Instruction and skill discovery

The shared bundle has one canonical provider-neutral `AGENTS.md` and a set of reusable `SKILL.md` directories. Setup projects those into supported tool conventions:

- Root `AGENTS.md` and `CLAUDE.md` aliases point to the shared instructions when those paths are free.
- `.agents/skills/`, `.opencode/skills/`, and `.claude/skills/` expose shared skills to supported runtimes.
- `.cursor/rules/harnessos.mdc` exposes the shared instruction contract in Cursor's project rules format.
- Existing skills directories are preserved; HarnessOS skills are linked by name into them.

The root instructions are short and refer agents to relevant skills as needed. Skills are focused workflows, not a mandatory load-everything checklist. Project-specific instructions remain authoritative for project facts and constraints; if requirements conflict or the objective is materially ambiguous, the agent should identify the conflict and ask a concise question before making risky assumptions.

## Installation and source of truth

V0.2 supports both a repo-local HarnessOS bundle and an installed global package:

- If `--bundle` is supplied, it is the selected source.
- Otherwise, setup prefers a recognized `harnessos/` child bundle or a HarnessOS checkout at the project root.
- If neither is present, setup uses the installed package's bundled defaults.

Repo-local bundles are preferred for team projects because their instructions and skills can be versioned with the project. Global package links are convenient for personal use and are machine-local unless the package path is shared. `harnessos check` reports missing links and conflicts. Setup is repeatable and does not overwrite existing project files. A conflicting root instruction file is left untouched and reported for deliberate integration.

## Completion and verification

Instructions and skills can require agents to run project checks and report commands and outcomes, but instructions alone cannot independently prove a change is correct. V0.2's setup/check utility verifies HarnessOS installation and link integrity, not task correctness. Repository checks remain the evidence for task outcomes. The v0.1 orchestrated `harness run` path may remain available as a compatibility/prototype feature; it is not the default v0.2 interaction model.

Later versions may add native lifecycle integrations and richer independent verification. They must remain adapters around existing agent runtimes rather than a model gateway or replacement harness.

## V0.2 acceptance criteria

- Setup works when HarnessOS is nested inside a consuming project and the agent is later launched from the consuming project root.
- Setup also works with a globally installed HarnessOS package.
- OpenCode, Claude Code, Cursor, and Codex receive shared instructions and skills through their supported repository conventions, subject to the documented adapter coverage.
- The same canonical instructions and skill content are reused; adapter files only bridge discovery/format differences.
- Setup is idempotent and never silently replaces project-authored instruction files or same-named skills.
- Check reports all expected links, their resolved sources, missing entries, and conflicts with a failing exit status for incomplete setup.
- The instruction contract directs agents to preserve the task objective, avoid invented requirements and generic filler, use relevant skills, run project checks, and report evidence accurately.
- Automated tests cover a nested bundle, global/package defaults, idempotence, and conflict preservation.

## Stack and boundaries

V0.2 continues to use Python, Pydantic where structured data is needed, SQLite only for persisted workflow/evaluation records, YAML/Markdown configuration, subprocess/CLI integration, and pytest. Setup/linking does not require an orchestration framework, model gateway, queue, vector store, or external infrastructure.

The product is agent-tool-neutral in its canonical instructions and skills. Discovery adapters are tool-specific and live at the integration boundary. OpenCode/NIM terminology must stay accurate: OpenCode invokes models from providers such as local Ollama or NVIDIA NIM.
