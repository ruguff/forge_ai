"""Local SQLite snapshots and replayable events; no credentials are persisted."""
import json
import os
import sqlite3
from pathlib import Path


class ProjectPersistence:
    def __init__(self, path=None):
        self.path = Path(path or os.environ.get("PROJECTFORGE_STATE_DB", "data/projects.sqlite3"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS snapshots (project_id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, project_id TEXT, payload TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT NOT NULL, payload TEXT NOT NULL)")
            db.execute("CREATE INDEX IF NOT EXISTS events_project ON events(project_id, id)")

    def connect(self):
        return sqlite3.connect(self.path, timeout=15)

    def save(self, project_id, state, context, spec=None):
        payload = json.dumps({"state": state.model_dump(mode="json"),
                              "context": context.model_dump(mode="json"),
                              "spec": spec.model_dump(mode="json") if spec else None})
        with self.connect() as db:
            previous = db.execute("SELECT payload FROM snapshots WHERE project_id=?", (project_id,)).fetchone()
            if previous and previous[0] == payload:
                return
            db.execute("INSERT OR REPLACE INTO snapshots VALUES (?, ?)", (project_id, payload))
            db.execute("INSERT INTO history(project_id, payload) VALUES (?, ?)", (project_id, payload))

    def load_all(self):
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute("SELECT payload FROM snapshots")]

    def append_event(self, project_id, payload):
        with self.connect() as db:
            cursor = db.execute("INSERT INTO events(project_id,payload) VALUES (?,?)", (project_id, json.dumps(payload)))
            return cursor.lastrowid

    def events_after(self, project_id, sequence):
        with self.connect() as db:
            return [(row[0], json.loads(row[1])) for row in db.execute(
                "SELECT id,payload FROM events WHERE project_id=? AND id>? ORDER BY id LIMIT 100",
                (project_id, sequence))]
