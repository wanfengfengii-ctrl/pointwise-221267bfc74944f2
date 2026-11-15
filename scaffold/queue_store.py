import json
import sqlite3


class Queue:
    def __init__(self, path):
        self.db = sqlite3.connect(str(path), timeout=5)
        self.db.row_factory = sqlite3.Row
        self.db.execute("""CREATE TABLE IF NOT EXISTS tasks(
            record TEXT PRIMARY KEY, reason TEXT NOT NULL, state TEXT NOT NULL,
            attempt TEXT, payload TEXT, receipt TEXT)""")
        self.db.commit()

    def add(self, record, reason):
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO tasks VALUES(?,?,'open',NULL,NULL,NULL)",
                            (record, reason))

    def stage(self, record, attempt, payload):
        text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        with self.db:
            cursor = self.db.execute(
                "UPDATE tasks SET state='sending',attempt=?,payload=?,receipt=NULL WHERE record=?",
                (attempt, text, record))
            if cursor.rowcount != 1:
                raise ValueError("unknown quarantine record")

    def finish(self, record, receipt):
        with self.db:
            self.db.execute("UPDATE tasks SET state='closed',receipt=? WHERE record=?",
                            (json.dumps(receipt, sort_keys=True), record))

    def rows(self):
        return [{"record": r["record"], "reason": r["reason"], "state": r["state"],
                 "attempt": r["attempt"],
                 "payload": None if r["payload"] is None else json.loads(r["payload"]),
                 "receipt": None if r["receipt"] is None else json.loads(r["receipt"])}
                for r in self.db.execute("SELECT * FROM tasks ORDER BY record")]

    def close(self):
        self.db.close()
