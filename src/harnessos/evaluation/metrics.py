from typing import Any


def build_run_record(trajectory: list[dict[str, Any]], *, benchmark: str, runtime: str,
                     provider: str, model: str, mode: str, duration_seconds: float,
                     iterations: int, failure_category: str | None = None) -> dict[str, Any]:
    events = [event["kind"] for event in trajectory]
    verifications = [event["payload"] for event in trajectory if event["kind"] == "verification"]
    checks = [event["payload"] for event in trajectory if event["kind"] in ("test", "independent_verification")]
    test_checks = [event["payload"] for event in trajectory if event["kind"] == "test"]
    verification_passed = bool(verifications and verifications[-1].get("passed"))
    tests_passed = bool(test_checks and test_checks[-1].get("exit_code") == 0)
    success = "task_completed" in events and verification_passed and tests_passed
    if not success and failure_category is None:
        if "agent_failed" in events:
            failure_category = "agent_behavior"
        elif any(item.get("exit_code") != 0 for item in checks):
            failure_category = "verification"
        elif "handoff" in events:
            failure_category = "handoff_or_recovery"
        else:
            failure_category = "termination"
    return {
        "benchmark": benchmark,
        "runtime": runtime,
        "provider": provider,
        "model": model,
        "mode": mode,
        "success": success,
        "iterations": iterations,
        "duration_seconds": round(duration_seconds, 3),
        "tests_passed": tests_passed,
        "verification_passed": verification_passed,
        "failure_category": failure_category if not success else None,
        "estimated_cost": None,
    }
