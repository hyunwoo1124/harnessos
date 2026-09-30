# How HarnessOS works

HarnessOS configures a repository so supported coding agents receive a shared engineering contract and discover reusable skills from the project root. HarnessOS does not replace the user's agent interface or model provider.

## Install once

Install HarnessOS in a Python environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install .
```

For development against a HarnessOS checkout, use `pip install -e .` instead. Both the `harnessos` and compatibility `harness` executables are installed.

## Configure a project

Run setup with the consuming repository as the project root:

```bash
harnessos setup --repo /path/to/network-scanner
harnessos check --repo /path/to/network-scanner
```

Bundle selection follows this order:

1. The path passed with `--bundle`.
2. A `harnessos/` child bundle in the project.
3. A HarnessOS checkout at the project root.
4. Packaged defaults from the installed HarnessOS package.

For example, if the project contains a local checkout under `network-scanner/harnessos/`, setup uses that copy and creates root links to its instructions and skills. If you omit a local checkout, setup uses the package's installed defaults. A global package link is local to that machine; put a bundle inside the repository when teammates need a shared, versioned source.

## What setup links

The canonical shared contract is `instructions/AGENTS.md`; reusable skills live in `skills/<skill-name>/SKILL.md`. Setup exposes those sources through each supported tool's discovery locations:

| Project path | Purpose |
| --- | --- |
| `AGENTS.md` | Shared root contract for AGENTS.md-compatible tools |
| `CLAUDE.md` | Claude Code-compatible instruction alias |
| `.agents/skills/<name>` | Codex and agent-compatible skill discovery |
| `.opencode/skills/<name>` | OpenCode skill discovery |
| `.claude/skills/<name>` | Claude Code skill discovery |
| `.cursor/rules/harnessos.mdc` | Cursor project rule adapter |

For skills, setup links each skill directory into an existing skills directory instead of replacing that directory. The Cursor rule is a thin adapter; the core instructions remain provider-neutral.

If the destination path already contains project-authored content, setup leaves it in place and reports a conflict. This includes an existing root `AGENTS.md`/`CLAUDE.md` and a same-named skill. Setup can still link the other available paths so conflicts can be resolved individually. Run `harnessos check` after deliberate integration to confirm the installed links.

## Start the agent in the right directory

After setup, start the agent from the consumer project's root:

```bash
cd /path/to/network-scanner
opencode
```

The working directory determines the active project. If you start OpenCode from the HarnessOS source checkout, HarnessOS development instructions apply. If you start it from `network-scanner`, the consumer project's instructions and HarnessOS root links apply. Simply placing HarnessOS in a child directory does not make that child directory's instructions active at the project root.

OpenCode combines project and global instruction sources, and discovers skill directories in supported project/global locations. Other tools have their own discovery formats, which is why setup installs aliases/adapters at the consuming project root. Review [the v0.2 design](Design-doc.md) for support boundaries and acceptance criteria.

## Agent behavior and verification

The shared contract directs agents to preserve the user's objective; inspect project rules; avoid inventing requirements or generic filler; ask about material ambiguity; use only relevant skills; run documented project checks; and report actual results accurately.

This instruction layer improves consistency, but it is not an independent task verifier. `harnessos check` proves that HarnessOS links are present and point to the selected bundle. For task correctness, the native agent must run the repository's checks and report the command and observed outcome. The older `harness run` prototype coordinates roles and independent test commands, but it is not the default v0.2 interface.

## Useful commands

```bash
# Install links from a specific local bundle
harnessos setup --repo /path/to/network-scanner --bundle /path/to/harnessos
harnessos check --repo /path/to/network-scanner --bundle /path/to/harnessos

# Check current links without modifying the project
harnessos check --repo /path/to/network-scanner

# Show setup options
harnessos setup --help
```
