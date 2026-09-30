from harnessos.protocol.models import Artifact, Evidence, Handoff, Role


def test_handoff_round_trips_structured_state():
    handoff = Handoff(task_id="task-1", from_agent="explorer", to_agent="implementer",
                      objective="Validate OAuth callback", required_action="Add validation",
                      artifacts=[Artifact(path="src/auth.py")],
                      evidence=[Evidence(kind="test", description="Observed failing test")])
    decoded = Handoff.model_validate_json(handoff.model_dump_json())
    assert decoded == handoff
    assert Role.IMPLEMENTER.value == "implementer"
