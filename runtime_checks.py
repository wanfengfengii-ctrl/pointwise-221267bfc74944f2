import subprocess
import sys
from pathlib import Path


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    result = subprocess.run(
        [sys.executable, str(root / "repo" / "checks.py"), *sys.argv[1:]],
        cwd=root)
    sys.exit(result.returncode)
