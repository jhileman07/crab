import shlex
import subprocess
from typing import Tuple


def run(command: str, input: str = "", folder: str = "./", shell: bool = False) -> Tuple[str, str]:
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

    return result.stdout, result.stderr
