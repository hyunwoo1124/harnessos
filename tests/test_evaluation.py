from harnessos.evaluation.metrics import build_run_record


def test_successful_retry_has_successful_final_test_metrics():
    trajectory = [
        {"kind": "test", "payload": {"exit_code": 1}},
        {"kind": "handoff", "payload": {}},
        {"kind": "test", "payload": {"exit_code": 0}},
        {"kind": "independent_verification", "payload": {"exit_code": 0}},
        {"kind": "verification", "payload": {"passed": True}},
        {"kind": "task_completed", "payload": {}},
    ]
    result = build_run_record(trajectory, benchmark="repair", runtime="opencode", provider="ollama",
                              model="ollama/test", mode="harnessos", duration_seconds=1.23456, iterations=2)
    assert result["success"] is True
    assert result["tests_passed"] is True
    assert result["failure_category"] is None
    assert result["duration_seconds"] == 1.235
