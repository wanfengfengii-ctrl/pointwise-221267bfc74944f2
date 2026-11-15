import hashlib
import json
import sqlite3


def encoded(payload):
    if (not isinstance(payload, dict) or set(payload) != {"station", "value"}
            or not isinstance(payload["station"], str) or not payload["station"]
            or type(payload["value"]) is not int):
        raise ValueError("invalid observation")
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return text, hashlib.sha256(text.encode()).hexdigest()


class Warehouse:
    def __init__(self, path):
        self.db = sqlite3.connect(str(path), timeout=5)
        self.db.row_factory = sqlite3.Row
        self.db.execute("""CREATE TABLE IF NOT EXISTS events(
            seq INTEGER PRIMARY KEY, record TEXT NOT NULL, attempt TEXT,
            payload TEXT NOT NULL, digest TEXT NOT NULL, receipt TEXT)""")
        self.db.commit()

    def _append(self, record, attempt, text, digest):
        cursor = self.db.execute(
            "INSERT INTO events(record,attempt,payload,digest) VALUES(?,?,?,?)",
            (record, attempt, text, digest))
        receipt = {"seq": cursor.lastrowid, "record": record, "digest": digest}
        self.db.execute("UPDATE events SET receipt=? WHERE seq=?",
                        (json.dumps(receipt, sort_keys=True), cursor.lastrowid))
        return receipt

    def accept(self, record, payload, attempt=None):
        text, digest = encoded(payload)
        if attempt is not None:
            raise ValueError("corrections unsupported")
        with self.db:
            return self._append(record, None, text, digest)

    def original_receipt(self, record):
        row = self.db.execute(
            "SELECT receipt FROM events WHERE record=? AND attempt IS NULL ORDER BY seq LIMIT 1",
            (record,)).fetchone()
        return None if row is None else json.loads(row["receipt"])

    def rows(self):
        return [{"seq": r["seq"], "record": r["record"], "attempt": r["attempt"],
                 "payload": json.loads(r["payload"]), "digest": r["digest"],
                 "receipt": json.loads(r["receipt"])}
                for r in self.db.execute("SELECT * FROM events ORDER BY seq")]

    def close(self):
        self.db.close()
