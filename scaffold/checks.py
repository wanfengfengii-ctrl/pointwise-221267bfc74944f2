import argparse
import hashlib
import json
from pathlib import Path
import queue as thread_queue
import subprocess
import sys
import tempfile
import threading
import unittest
from warehouse import Warehouse

ROOT = Path(__file__).resolve().parent
CORRECTION = {"station": "S1", "value": 13}


def seed(folder):
    from queue_store import Queue
    w, q = str(Path(folder) / "warehouse.db"), str(Path(folder) / "quarantine.db")
    warehouse, quarantine = Warehouse(w), Queue(q)
    warehouse.accept("r1", {"station": "S1", "value": 10})
    quarantine.add("r1", "outlier")
    warehouse.close()
    quarantine.close()
    return w, q


def snapshot(w, q):
    from queue_store import Queue
    warehouse, quarantine = Warehouse(w), Queue(q)
    try:
        return {"events": warehouse.rows(), "tasks": quarantine.rows()}
    finally:
        warehouse.close()
        quarantine.close()


def check_one_correction(result, marker):
    events, tasks = result["events"], result["tasks"]
    expected_payloads = [{"station": "S1", "value": 10}, CORRECTION]
    valid = len(events) == 2 and len(tasks) == 1
    if valid:
        valid = ([e["record"] for e in events] == ["r1", "r1"]
                 and [e["attempt"] for e in events] == [None, "t1"]
                 and [e["payload"] for e in events] == expected_payloads
                 and tasks[0]["state"] == "closed" and tasks[0]["attempt"] == "t1"
                 and tasks[0]["payload"] == CORRECTION
                 and tasks[0]["receipt"] == events[1]["receipt"])
        for event in events:
            raw = json.dumps(event["payload"], sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            valid = valid and event["digest"] == hashlib.sha256(raw.encode()).hexdigest()
            valid = valid and all(event["receipt"].get(key) == event[key]
                                  for key in ("seq", "record", "digest"))
    assert valid, marker


def incident():
    from replay import ResponseLost, apply
    with tempfile.TemporaryDirectory() as folder:
        w, q = seed(folder)
        try:
            apply(w, q, "r1", "t1", CORRECTION, lose_response=True)
        except ResponseLost:
            pass
        before = snapshot(w, q)
        receipt = apply(w, q, "r1", "t1", CORRECTION)
        result = snapshot(w, q)
        print(json.dumps({"after_lost_response": before, "retry_receipt": receipt,
                          "after_retry": result}, sort_keys=True), flush=True)
        check_one_correction(result, "QUARANTINE_REPLAY_DIVERGENCE")


def crash(boundary):
    with tempfile.TemporaryDirectory() as folder:
        w, q = seed(folder)
        command = [sys.executable, str(ROOT / "runner.py"), "replay",
                   "--warehouse", w, "--queue", q, "--record", "r1",
                   "--attempt", "t1", "--payload", json.dumps(CORRECTION)]
        child = subprocess.Popen(command + ["--pause-at", boundary], stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        mailbox = thread_queue.Queue()
        reader = threading.Thread(target=lambda: mailbox.put(child.stdout.readline()), daemon=True)
        reader.start()
        try:
            line = mailbox.get(timeout=10)
            assert json.loads(line) == {"hook": boundary}, line
        finally:
            child.kill()
            child.communicate(timeout=10)
        assert child.returncode < 0, "child was not killed"
        completed = subprocess.run(command, capture_output=True, text=True, timeout=10)
        result = snapshot(w, q)
        print(json.dumps({"boundary": boundary, "killed_exit": child.returncode,
                          "retry_exit": completed.returncode, "retry_stdout": completed.stdout,
                          "snapshot": result}, sort_keys=True), flush=True)
        assert completed.returncode == 0, completed.stderr
        check_one_correction(result, "QUARANTINE_HANDOFF_DIVERGENCE")


def demo():
    from replay import apply
    with tempfile.TemporaryDirectory() as folder:
        w, q = seed(folder)
        apply(w, q, "r1", "t1", CORRECTION)
        print(json.dumps(snapshot(w, q), sort_keys=True, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["normal", "incident", "crash", "demo"])
    parser.add_argument("--boundary", choices=["staged", "warehouse_committed", "before_close", "after_close"],
                        default="warehouse_committed")
    args = parser.parse_args()
    if args.mode == "normal":
        suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
        return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
    if args.mode == "incident":
        incident()
    elif args.mode == "crash":
        crash(args.boundary)
    else:
        demo()
    return 0


if __name__ == "__main__":
    sys.exit(main())
