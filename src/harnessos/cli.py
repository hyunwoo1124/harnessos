import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

from harnessos.agents.opencode import OpenCodeRuntime
from harnessos.behavior.config import load_roles
from harnessos.evaluation.metrics import build_run_record
from harnessos.installation import check as check_installation
from harnessos.installation import setup as setup_installation
from harnessos.loop.engine import Workflow
from harnessos.protocol.models import Task
from harnessos.state.store import StateStore


def main() -> None:
    parser = argparse.ArgumentParser(prog="harnessos", description="Set up and validate repository-level agent instructions and skills")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="(v0.1 prototype) coordinate a task through explore/plan/implement/test/review/verify")
    run.add_argument("objective")
    run.add_argument("--repo", default=".")
    run.add_argument("--db", default=".harness/state.sqlite3")
    run.add_argument("--test-command", default="pytest")
    run.add_argument("--max-iterations", type=int, choices=range(1, 11), default=3)
    run.add_argument("--model", help="OpenCode model selector (for example ollama/model-name or nim/served-model)")
    run.add_argument("--provider", choices=["ollama", "nim", "other"], help="provider label to save in the evaluation record")
    run.add_argument("--opencode", default="opencode", help="OpenCode executable path")
    init = sub.add_parser("init", help="create a project-local .harness configuration")
    init.add_argument("--repo", default=".")
    init.add_argument("--provider", choices=["ollama", "nim"], help="also write a starter OpenCode provider config")
    init.add_argument("--nim-model", help="NIM model ID to place in the generated OpenCode config")
    init.add_argument("--force", action="store_true")
    doctor = sub.add_parser("doctor", help="check runtime and selected inference provider availability")
    doctor.add_argument("--provider", choices=["ollama", "nim"], required=True)
    doctor.add_argument("--opencode", default="opencode")
    doctor.add_argument("--base-url", help="override provider API base URL")
    trajectory = sub.add_parser("trajectory", help="show persisted task events")
    trajectory.add_argument("task_id")
    trajectory.add_argument("--db", default=".harness/state.sqlite3")
    setup = sub.add_parser("setup", help="link HarnessOS instructions and skills into a project")
    setup.add_argument("--repo", default=".", help="consumer project root")
    setup.add_argument("--bundle", help="HarnessOS bundle path; auto-detected when omitted")
    check = sub.add_parser("check", help="check HarnessOS instruction and skill links")
    check.add_argument("--repo", default=".", help="consumer project root")
    check.add_argument("--bundle", help="HarnessOS bundle path; auto-detected when omitted")
    args = parser.parse_args()
    if args.command in {"setup", "check"}:
        repo = Path(args.repo).expanduser().resolve()
        bundle = Path(args.bundle).expanduser() if args.bundle else None
        try:
            report = setup_installation(repo, bundle) if args.command == "setup" else check_installation(repo, bundle)
        except (OSError, ValueError) as exc:
            print(f"HarnessOS {args.command} failed: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc
        print(f"BUNDLE {report.bundle_source}")
        for label, paths in (("CREATED", report.created), ("READY", report.present), ("CONFLICT", report.conflicts)):
            for path in paths:
                print(f"{label} {path}")
        if not report.ok:
            print("Resolve the listed conflicts without overwriting project-owned content, then rerun harnessos setup.", file=sys.stderr)
            raise SystemExit(1)
        print(f"HarnessOS {args.command} complete for {repo}")
        return
    if args.command == "init":
        repo = Path(args.repo).resolve()
        config = repo / ".harness" / "roles.yaml"
        provider_config = repo / "opencode.json" if args.provider else None
        existing = [path for path in (config, provider_config) if path is not None and path.exists()]
        if existing and not args.force:
            parser.error(f"{existing[0]} already exists (use --force to replace it)")
        config.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(__file__).resolve().parent / "defaults" / "roles.yaml", config)
        print(f"Created {config}")
        if args.provider:
            assert provider_config is not None
            sample = Path(__file__).resolve().parent / "defaults" / "providers" / f"opencode.{args.provider}.json"
            config_text = sample.read_text()
            if args.provider == "nim" and args.nim_model:
                config_text = config_text.replace("REPLACE_WITH_NIM_MODEL_ID", args.nim_model)
            provider_config.write_text(config_text)
            print(f"Created {provider_config}")
        return
    if args.command == "doctor":
        checks = []
        executable = shutil.which(args.opencode) or (str(Path(args.opencode).expanduser()) if Path(args.opencode).expanduser().is_file() else None)
        if executable:
            result = subprocess.run([executable, "--version"], capture_output=True, text=True, check=False)
            checks.append(("OpenCode", result.returncode == 0, (result.stdout or result.stderr).strip()))
        else:
            checks.append(("OpenCode", False, f"'{args.opencode}' was not found; pass --opencode /path/to/opencode or add it to PATH"))
        if args.base_url:
            base = args.base_url
        elif args.provider == "nim":
            base = os.environ.get("NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
        else:
            base = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
        key = os.environ.get("NVIDIA_API_KEY") if args.provider == "nim" else None
        if args.provider == "nim" and not key and "integrate.api.nvidia.com" in base:
            checks.append(("NVIDIA_API_KEY", False, "Set NVIDIA_API_KEY for the selected NIM endpoint"))
        url = base.rstrip("/") + ("/models" if args.provider == "nim" else "/api/tags")
        try:
            request = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"} if key else {})
            with urllib.request.urlopen(request, timeout=8) as response:
                body = response.read(1_000_000).decode(errors="replace")
            payload = json.loads(body)
            inventory = payload.get("data", []) if args.provider == "nim" else payload.get("models", [])
            names = [item.get("id", item.get("name", "unknown")) for item in inventory]
            checks.append((f"{args.provider} endpoint", bool(names),
                           f"Found {len(names)} model(s) at {url}: {', '.join(names[:8])}" if names
                           else f"Endpoint responded but has no discoverable models at {url}"))
        except (OSError, urllib.error.URLError) as exc:
            checks.append((f"{args.provider} endpoint", False, f"Could not reach {url}: {exc}"))
        for name, passed, detail in checks:
            print(f"{'PASS' if passed else 'FAIL'} {name}: {detail}")
        if not all(check[1] for check in checks):
            raise SystemExit(1)
        return
    store = StateStore(args.db)
    if args.command == "trajectory":
        print(json.dumps(store.trajectory(args.task_id), indent=2))
        return
    repo = Path(args.repo).resolve()
    task = Task(objective=args.objective, repository=str(repo))
    role_config = repo / ".harness" / "roles.yaml"
    try:
        role_runtimes = load_roles(role_config) if role_config.exists() else {}
    except (OSError, ValueError) as exc:
        parser.error(f"invalid role config {role_config}: {exc}")
    unsupported = {runtime for runtime in role_runtimes.values() if runtime != "opencode"}
    if unsupported:
        parser.error(f"runtime adapters not implemented: {', '.join(sorted(unsupported))}")
    runtime = {role: OpenCodeRuntime(executable=args.opencode, model=args.model) for role in role_runtimes} or OpenCodeRuntime(executable=args.opencode, model=args.model)
    workflow = Workflow(runtime, store, Path(__file__).resolve().parent / "defaults" / "skills",
                        max_iterations=args.max_iterations, test_command=args.test_command)
    print(f"HarnessOS task id: {task.id}", file=sys.stderr)
    started = time.monotonic()
    provider = args.provider or (args.model.split("/", 1)[0] if args.model and "/" in args.model else "other")
    try:
        result = workflow.run(task, repo)
    except (RuntimeError, OSError) as exc:
        metrics = build_run_record(store.trajectory(task.id), benchmark=args.objective,
                                   runtime="opencode", provider=provider, model=args.model or "configured-in-opencode",
                                   mode="harnessos", duration_seconds=time.monotonic() - started,
                                   iterations=task.iteration, failure_category="loop_or_runtime")
        store.record(task.id, "evaluation_record", metrics)
        print(f"HarnessOS task failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    metrics = build_run_record(store.trajectory(task.id), benchmark=args.objective,
                               runtime="opencode", provider=provider, model=args.model or "configured-in-opencode",
                               mode="harnessos", duration_seconds=time.monotonic() - started,
                               iterations=result.iteration)
    store.record(task.id, "evaluation_record", metrics)
    print(json.dumps({"task": result.model_dump(mode="json"), "evaluation": metrics}, indent=2))


if __name__ == "__main__":
    main()
