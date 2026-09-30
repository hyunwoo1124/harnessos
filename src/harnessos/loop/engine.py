import subprocess
import shlex
import re
from pathlib import Path

from harnessos.agents.base import AgentRuntime
from harnessos.behavior.config import load_skill
from harnessos.protocol.models import Agent, Artifact, Evidence, Finding, Handoff, Role, Task, VerificationResult
from harnessos.state.store import StateStore


class WorkflowError(RuntimeError):
    pass


class Workflow:
    """Deterministic coordinator: runtime output never controls stage transitions."""

    def __init__(self, runtime: AgentRuntime | dict[Role, AgentRuntime], store: StateStore, skills_dir: Path,
                 max_iterations: int = 3, test_command: str = "pytest"):
        self.runtime, self.store, self.skills_dir = runtime, store, skills_dir
        if max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")
        self.max_iterations, self.test_command = max_iterations, test_command
        self._context: dict[str, list[str]] = {}

    def run(self, task: Task, repository: Path | None = None) -> Task:
        if self.store.get_task(task.id) is None:
            self.store.create_task(task)
        self._context[task.id] = []
        repo = (repository or Path(task.repository)).resolve()
        task.status = "EXPLORING"
        self._agent(task, Role.EXPLORER, repo, "Explore the repository and report relevant facts and evidence.")
        task.status = "PLANNING"
        self._agent(task, Role.ARCHITECT, repo, "Produce a concise implementation plan based on the objective.")
        for iteration in range(1, self.max_iterations + 1):
            task.iteration = iteration
            implementation = self._agent(task, Role.IMPLEMENTER, repo, "Implement the objective. Inspect before editing and run relevant checks.")
            self.store.record(task.id, "implementation_result", implementation.model_dump(mode="json"))
            task.status = "TESTING"
            task.current_role = Role.TESTER
            self.store.update_task(task, "stage_started")
            tests = self._command(repo, self.test_command, task.id, "test")
            if tests.exit_code != 0:
                self._handoff(task, "tester", "implementer", "Repair failing checks", tests,
                              artifacts=implementation.artifacts)
                task.status = "IMPLEMENTING"
                self.store.update_task(task)
                continue
            task.status = "REVIEWING"
            review = self._agent(task, Role.REVIEWER, repo, "Review changes for correctness, risks, and missing tests. End with VERDICT: PASS only if there are no actionable findings; otherwise end with VERDICT: FAIL and list findings.")
            if "VERDICT: PASS" not in review.output.upper():
                self._handoff(task, "reviewer", "implementer", "Address reviewer findings",
                              Evidence(kind="review", description="Reviewer requested changes",
                                       output=review.output[-12000:]), artifacts=implementation.artifacts)
                task.status = "IMPLEMENTING"
                self.store.update_task(task)
                continue
            task.status = "VERIFYING"
            self._agent(task, Role.VERIFIER, repo, "Independently inspect the requested outcome and evidence. Report gaps. The coordinator will execute a fresh verification command.")
            verify_evidence = self._command(repo, self.test_command, task.id, "independent_verification")
            result = VerificationResult(task_id=task.id, passed=verify_evidence.exit_code == 0,
                                        evidence=[verify_evidence], summary="Independent test command completed")
            self.store.record_verification(result)
            if result.passed:
                task.status = "COMPLETED"
                self.store.update_task(task, "task_completed")
                return task
            self._handoff(task, "verifier", "implementer", "Repair independent verification failure",
                          verify_evidence, artifacts=implementation.artifacts)
        task.status = "FAILED"
        self.store.update_task(task, "iteration_limit_reached")
        raise WorkflowError(f"Task did not verify after {self.max_iterations} implementation iterations")

    def _agent(self, task: Task, role: Role, repo: Path, objective: str):
        stage = {Role.EXPLORER: "EXPLORING", Role.ARCHITECT: "PLANNING", Role.IMPLEMENTER: "IMPLEMENTING",
                 Role.TESTER: "TESTING", Role.REVIEWER: "REVIEWING", Role.VERIFIER: "VERIFYING"}[role]
        task.status, task.current_role = stage, role
        self.store.update_task(task, "stage_started")
        agent = Agent(name=role.value, role=role)
        runtime = self.runtime[role] if isinstance(self.runtime, dict) else self.runtime
        prior = "\n\n--- Structured handoff/context from earlier roles ---\n".join(self._context.get(task.id, [])[-8:])
        behavior = load_skill(role, self.skills_dir)
        full_context = "\n\n".join(part for part in (behavior, prior) if part)
        full_context += f"\n\nCurrent stage action:\n{objective}"
        result = runtime.execute(task, agent, full_context, repo)
        self.store.record(task.id, "agent_execution", result.model_dump(mode="json"))
        # Keep completed findings useful and compact. A model response that only
        # asks the user for more information should not steer the next role.
        output = result.output[-12000:]
        asks_user = re.search(
            r"\b(can you|could you|please (provide|confirm|run|use)|once you provide|let me know|"
            r"what is the current|what are the|user-provided input|url: not provided|"
            r"what (specific|steps|issue|behavior)|use the (grep|webfetch) tool)\b", output, re.IGNORECASE)
        context_output = "" if asks_user else output
        self._context.setdefault(task.id, []).append(
            f"Role: {role.value}\nRequested action: {objective}\nOutput:\n{context_output}\nArtifacts: "
            + ", ".join(artifact.path for artifact in result.artifacts)
        )
        if not result.success:
            task.status = "FAILED"
            self.store.update_task(task, "agent_failed")
            raise WorkflowError(f"{role.value} runtime failed with exit code {result.exit_code}")
        return result

    def _command(self, repo: Path, command: str, task_id: str, kind: str) -> Evidence:
        try:
            proc = subprocess.run(shlex.split(command), cwd=repo, text=True, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, check=False, timeout=900)
            code, output = proc.returncode, proc.stdout
        except subprocess.TimeoutExpired as exc:
            code, output = 124, exc.stdout or ""
            if isinstance(output, bytes):
                output = output.decode(errors="replace")
            output += "\nCheck command timed out after 900 seconds"
        except OSError as exc:
            code, output = 127, f"Unable to execute check command: {exc}"
        evidence = Evidence(kind=kind, description=f"Executed {command}", command=command,
                            exit_code=code, output=output[-12000:])
        self.store.record(task_id, kind, evidence)
        if kind == "test":
            self.store.record(task_id, "agent_execution", {
                "agent": {"name": "tester", "runtime": "harnessos", "role": Role.TESTER.value},
                "exit_code": code, "output": evidence.output, "artifacts": [],
                "duration_seconds": 0, "success": code == 0,
            })
        return evidence

    def _handoff(self, task: Task, source: str, target: str, action: str, evidence: Evidence,
                 artifacts: list[Artifact] | None = None):
        summary = next((line.strip() for line in (evidence.output or "").splitlines() if line.strip()),
                       evidence.description)
        handoff = Handoff(task_id=task.id, from_agent=source, to_agent=target,
                          objective=task.objective, required_action=action,
                          findings=[Finding(summary=summary[:500], severity="error", evidence=[evidence])],
                          artifacts=artifacts or [], evidence=[evidence],
                          unresolved_questions=["Review failure details in captured evidence."])
        self.store.record_handoff(handoff)
        self._context.setdefault(task.id, []).append(
            f"Structured handoff {source} → {target}\nObjective: {task.objective}\nRequired action: {action}\n"
            f"Evidence ({evidence.kind}, exit {evidence.exit_code}):\n{evidence.output or evidence.description}"
        )
