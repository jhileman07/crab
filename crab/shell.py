import os
import subprocess
from typing import Tuple


def run(command, input: str) -> Tuple[str, str]:
    result = subprocess.run(
        command,
        input=input,
        capture_output=True,
        text=True,
        check=False,
    )

    return result.stdout, result.stderr


def cd(path: str) -> None:
    os.chdir(path)
