import sys

from harnessos.agents.base import AgentRuntime
from harnessos.agents.opencode import OpenCodeRuntime
from harnessos.loop.engine import Workflow, WorkflowError
from harnessos.protocol.models import AgentResult, Task
from harnessos.state.store import StateStore


class FakeRuntime(AgentRuntime):
    def execute(self, task, agent, context="", repository=None):
        output = "VERDICT: PASS" if agent.role.value == "reviewer" else "ok"
        return AgentResult(agent=agent, exit_code=0, output=output, success=True)


def test_workflow_requires_check_and_records_completion(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = StateStore(tmp_path / "state.sqlite3")
    task = Task(objective="make a change", repository=str(repo))
    result = Workflow(FakeRuntime(), store, tmp_path / "skills", test_command="true").run(task, repo)
    assert result.status == "COMPLETED"
    events = store.trajectory(task.id)
    assert any(event["kind"] == "verification" for event in events)
    assert events[-1]["kind"] == "task_completed"


def test_workflow_stops_after_iteration_limit_when_check_fails(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    store = StateStore(tmp_path / "state.sqlite3")
    task = Task(objective="make a change", repository=str(repo))
    workflow = Workflow(FakeRuntime(), store, tmp_path / "skills", max_iterations=1, test_command="false")
    try:
        workflow.run(task, repo)
        assert False, "expected failed verification workflow"
    except WorkflowError:
        pass
    assert store.get_task(task.id).status == "FAILED"
    handoffs = [event["payload"] for event in store.trajectory(task.id) if event["kind"] == "handoff"]
    assert handoffs
    assert handoffs[0]["findings"][0]["severity"] == "error"
    assert handoffs[0]["evidence"][0]["exit_code"] == 1


def test_full_cli_adapter_workflow_persists_artifacts_and_evidence(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    # This temporary git repo lets the black-box adapter report changed artifacts.
    import subprocess
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    store = StateStore(tmp_path / "state.sqlite3")
    task = Task(objective="create the requested feature", repository=str(repo))
    import shlex
    fake_script = __file__.replace("test_workflow.py", "fake_opencode.py")
    fake_cli = tmp_path / "opencode-stub"
    fake_cli.write_text(f"#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(fake_script)} \"$@\"\n")
    fake_cli.chmod(0o755)
    workflow = Workflow(OpenCodeRuntime(executable=str(fake_cli), model="test/stub"), store,
                        tmp_path / "skills", test_command="true")
    result = workflow.run(task, repo)
    assert result.status == "COMPLETED"
    assert (repo / "harnessos-e2e-artifact.txt").exists()
    executions = [event["payload"] for event in store.trajectory(task.id) if event["kind"] == "agent_execution"]
    implementer = next(event for event in executions if event["agent"]["role"] == "implementer")
    assert implementer["artifacts"][0]["path"] == "harnessos-e2e-artifact.txt"
    assert f"RUNTIME_PWD: {repo}" in implementer["output"]
    assert "PROMPT_HAS_TASK_OBJECTIVE: true" in implementer["output"]
    architect = next(event for event in executions if event["agent"]["role"] == "architect")
    assert "CONTEXT_HAS_EXPLORER: true" in architect["output"]
    assert any(event["kind"] == "independent_verification" for event in store.trajectory(task.id))


def test_test_failure_handoff_retries_implementation(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    check = tmp_path / "check-once.sh"
    check.write_text("#!/bin/sh\nif [ ! -f .checked ]; then touch .checked; exit 1; fi\nexit 0\n")
    check.chmod(0o755)
    store = StateStore(tmp_path / "state.sqlite3")
    task = Task(objective="make a change", repository=str(repo))
    workflow = Workflow(FakeRuntime(), store, tmp_path / "skills", max_iterations=2, test_command=str(check))
    result = workflow.run(task, repo)
    assert result.status == "COMPLETED"
    roles = [event["payload"]["agent"]["role"] for event in store.trajectory(task.id) if event["kind"] == "agent_execution"]
    assert roles.count("implementer") == 2
    assert any(event["kind"] == "handoff" for event in store.trajectory(task.id))
