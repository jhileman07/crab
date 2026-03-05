import subprocess
import sys
from pathlib import Path


def main() -> None:
    args = sys.argv[1:]
    if args and args[0] == "compose":
        _run_script(args[1] if len(args) > 1 else "CrabCompose")
        return
    _run_script("CrabCompose" if Path("CrabCompose").exists() else "Crabfile")


def _run_script(path: str) -> None:
    try:
        sys.exit(subprocess.call([sys.executable, path]))
    except KeyboardInterrupt:
        sys.exit(130)
