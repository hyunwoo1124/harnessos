#!/usr/bin/env python3
"""Minimal executable stand-in for OpenCode used by the adapter E2E test."""
import sys
import os
from pathlib import Path

prompt = sys.argv[-1]
context_marker = "CONTEXT_HAS_EXPLORER: true" if "Completed Role: explorer" in prompt else "CONTEXT_HAS_EXPLORER: false"
objective_marker = "PROMPT_HAS_TASK_OBJECTIVE: true" if "Task objective (authoritative): create the requested feature" in prompt else "PROMPT_HAS_TASK_OBJECTIVE: false"
if "Role: implementer" in prompt:
    Path("harnessos-e2e-artifact.txt").write_text("created by the implementer role\n")
if "Role: reviewer" in prompt:
    print(context_marker + "\n" + objective_marker + "\nVERDICT: PASS")
else:
    print("Completed " + prompt.splitlines()[0] + "\n" + context_marker + "\n" + objective_marker)
print("RUNTIME_CWD: " + str(Path.cwd()))
print("RUNTIME_PWD: " + os.environ.get("PWD", ""))
