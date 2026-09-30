import json
import sqlite3
from pathlib import Path
from typing import Any

from harnessos.protocol.models import Handoff, Task, VerificationResult


class StateStore:
    """Small append-oriented SQLite store for tasks and their trajectory."""

    def __init__(self, path: Path | str):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, status TEXT NOT NULL, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            """)

    def _connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        return db

    def create_task(self, task: Task) -> Task:
        with self._connect() as db:
            db.execute("INSERT INTO tasks VALUES (?, ?, ?)", (task.id, task.status, task.model_dump_json()))
            self._event(db, task.id, "task_created", task.model_dump(mode="json"))
        return task

    def get_task(self, task_id: str) -> Task | None:
        with self._connect() as db:
            row = db.execute("SELECT payload FROM tasks WHERE id=?", (task_id,)).fetchone()
        return Task.model_validate_json(row[0]) if row else None

    def update_task(self, task: Task, event: str = "state_changed") -> None:
        with self._connect() as db:
            db.execute("UPDATE tasks SET status=?, payload=? WHERE id=?", (task.status, task.model_dump_json(), task.id))
            self._event(db, task.id, event, task.model_dump(mode="json"))

    def record(self, task_id: str, kind: str, payload: Any) -> None:
        body = payload.model_dump(mode="json") if hasattr(payload, "model_dump") else payload
        with self._connect() as db:
            self._event(db, task_id, kind, body)

    def record_handoff(self, handoff: Handoff) -> None:
        self.record(handoff.task_id, "handoff", handoff)

    def record_verification(self, result: VerificationResult) -> None:
        self.record(result.task_id, "verification", result)

    def trajectory(self, task_id: str) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT kind, payload, created_at FROM events WHERE task_id=? ORDER BY id", (task_id,)).fetchall()
        return [{"kind": r[0], "payload": json.loads(r[1]), "created_at": r[2]} for r in rows]

    @staticmethod
    def _event(db, task_id: str, kind: str, payload: Any) -> None:
        db.execute("INSERT INTO events(task_id, kind, payload) VALUES (?, ?, ?)", (task_id, kind, json.dumps(payload, default=str)))
