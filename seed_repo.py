import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
DEST = ROOT / "repo"


def git(*args):
    return subprocess.check_output(["git", "-C", str(DEST), *args], text=True).strip()


def copy(source, target):
    path = DEST / target
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / source, path)


def commit(message, day):
    git("add", ".")
    env = dict(os.environ)
    stamp = "2026-11-%02dT12:00:00+00:00" % day
    env.update(GIT_AUTHOR_DATE=stamp, GIT_COMMITTER_DATE=stamp)
    subprocess.run(["git", "-C", str(DEST), "commit", "-q", "-m", message],
                   env=env, check=True)
    return git("rev-parse", "HEAD")


def main():
    if DEST.exists():
        for tag in ("baseline/base", "baseline/hotfix", "baseline/replay"):
            git("rev-parse", "--verify", tag + "^{commit}")
        print("existing repo retained; no reset")
        return
    DEST.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(DEST)], check=True)
    git("config", "user.name", "Pipeline Maintainer")
    git("config", "user.email", "maintainer@example.invalid")
    git("config", "commit.gpgsign", "false")
    for source, target in [
        ("CONTRACT.md", "CONTRACT.md"),
        ("scaffold/warehouse_base.py", "warehouse.py"),
        ("scaffold/runner.py", "runner.py"),
        ("scaffold/checks.py", "checks.py"),
        ("scaffold/test_original.py", "tests/test_original.py")]:
        copy(source, target)
    (DEST / ".gitignore").write_text("__pycache__/\n*.db\n*.db-*\n", encoding="utf-8")
    (DEST / "docs").mkdir()
    (DEST / "docs/maintenance.md").write_text(
        "# 入仓维护说明\n每次调用追加观测；original_receipt 返回该记录的首个原始回执。\n",
        encoding="utf-8")
    base = commit("base: durable observation ledger and original receipt reader", 1)
    git("tag", "baseline/base", base)

    git("checkout", "-q", "-b", "ingest-idempotency")
    copy("scaffold/warehouse_hotfix.py", "warehouse.py")
    copy("scaffold/test_hotfix.py", "tests/test_hotfix.py")
    copy("scaffold/docs_ingest.md", "docs/maintenance.md")
    hotfix = commit("hotfix: freeze original input and return durable duplicate receipt", 2)
    git("tag", "baseline/hotfix", hotfix)

    git("checkout", "-q", "-b", "quarantine-replay", base)
    for source, target in [
        ("scaffold/warehouse_replay.py", "warehouse.py"),
        ("scaffold/queue_store.py", "queue_store.py"),
        ("scaffold/replay.py", "replay.py"),
        ("scaffold/test_replay.py", "tests/test_replay.py"),
        ("scaffold/docs_replay.md", "docs/maintenance.md")]:
        copy(source, target)
    replay = commit("replay: deliver quarantine corrections and close local task", 3)
    git("tag", "baseline/replay", replay)
    print(json.dumps({"repo": str(DEST), "base": base, "hotfix": hotfix,
                      "replay": replay, "checkout": "quarantine-replay"}, sort_keys=True))


if __name__ == "__main__":
    main()
