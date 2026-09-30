from harnessos.protocol.models import Task
from harnessos.state.store import StateStore


def test_task_and_trajectory_survive_reopen(tmp_path):
    path = tmp_path / "state.sqlite3"
    task = Task(objective="fix bug")
    StateStore(path).create_task(task)
    reopened = StateStore(path)
    assert reopened.get_task(task.id) == task
    assert reopened.trajectory(task.id)[0]["kind"] == "task_created"
