import shlex
import subprocess
from typing import Tuple


def run(command: str, input: str, folder: str = "./") -> Tuple[str, str]:
    result = subprocess.run(
        shlex.split(command),
        input=input,
        capture_output=True,
        text=True,
        cwd=folder,
        check=False,
    )

    return result.stdout, result.stderr
