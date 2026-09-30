# HarnessOS

HarnessOS is a repository-level agent engineering layer. It makes shared instructions and reusable skills discoverable to coding agents such as OpenCode, Claude Code, Cursor, and Codex. Users continue to start their chosen agent directly; HarnessOS's normal CLI use is setup and link validation, not task prompting.

## Set up a project

Install HarnessOS once, then link its instructions and skills into the consuming project:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
harnessos setup --repo /path/to/network-scanner
harnessos check --repo /path/to/network-scanner
```

If HarnessOS is checked out inside the project, its bundle is detected automatically when it lives at `network-scanner/harnessos/`:

```text
network-scanner/
├── harnessos/                 # Shared instructions and skills
├── src/
├── AGENTS.md -> harnessos/instructions/AGENTS.md
├── CLAUDE.md -> harnessos/instructions/AGENTS.md
├── .agents/skills/            # Codex and agent-compatible skills
├── .opencode/skills/          # OpenCode skills
├── .claude/skills/            # Claude Code skills
└── .cursor/rules/harnessos.mdc
```

Then start the native agent from the project root, for example:

```bash
cd /path/to/network-scanner
opencode
```

The agent's working directory determines the project scope. Starting OpenCode in the HarnessOS source repository loads HarnessOS's development rules; starting it in a consumer project loads that project's rules and the HarnessOS links configured there. A nested `harnessos/` folder alone is not an instruction root, which is why setup adds root-level discovery links.

If automatic detection is ambiguous, select the source bundle directly:

```bash
harnessos setup --repo /path/to/network-scanner --bundle /path/to/harnessos
```

With no local bundle, setup uses the packaged instructions and skills from the installed HarnessOS package. Those links are machine-local; vendoring HarnessOS in the project is preferable when the whole team should share a pinned copy.

## Setup behavior

Setup creates symlinks for root `AGENTS.md` and `CLAUDE.md`, adapter skill directories under `.agents/skills`, `.opencode/skills`, and `.claude/skills`, and a Cursor rule at `.cursor/rules/harnessos.mdc`. It links individual skills so existing skill directories can coexist.

Setup is repeatable. It never replaces existing project instructions or a same-named skill; it reports those as conflicts. Resolve conflicts deliberately, then rerun setup. `check` validates the expected links without changing files and exits unsuccessfully when any link is missing or points elsewhere.

## Skills and shared contract

The provider-neutral contract is in `instructions/AGENTS.md`; Cursor's adapter is in `adapters/cursor/harnessos.mdc`. Reusable skills are under `skills/<skill-name>/SKILL.md`. The skills use the Agent Skills directory convention and can include supporting files alongside `SKILL.md`.

The shared contract asks agents to preserve the user's objective, inspect project rules, avoid invented requirements and generic filler, ask about material ambiguity, use relevant skills, run repository checks, and report observed evidence accurately. It does not replace project-specific instructions.

## Model and provider choice

HarnessOS does not host models or configure model gateways. OpenCode, Claude Code, Cursor, or Codex remains the agent interface/runtime. Configure models through that tool. For example, OpenCode can use a local Ollama model or a cloud NVIDIA NIM model, but OpenCode is the runtime and Ollama/NIM are model providers.

## Stack and boundaries

The project uses Python, YAML/Markdown configuration, subprocess/CLI integration, and pytest. SQLite and Pydantic support the retained workflow/evaluation prototype. No orchestration framework, model gateway, queue, or vector store is needed for setup and discovery links.

The current implementation adds the v0.2 setup/check path. The earlier `harness run` explore/plan/implement/review/verify workflow remains available as a v0.1 prototype, but it is not the intended default way to use HarnessOS. See [the v0.2 design](docs/Design-doc.md) and [the setup walkthrough](docs/how-it-works.md).
