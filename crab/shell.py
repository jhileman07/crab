import shlex
import subprocess
import time
from typing import Tuple


def run(command: str, input: str = "", folder: str = "./", shell: bool = False) -> Tuple[str, str, float]:
    start_time = time.time()
    needs_shell = any(op in command for op in ["&&", "||", "|", ";"])
    result = subprocess.run(
        command if needs_shell else shlex.split(command),
        shell=needs_shell or shell,
        input=input,
        capture_output=True,
        text=True,
        cwd=folder,
        check=False,
    )
    end_time = time.time()

    return result.stdout, result.stderr, end_time - start_time
