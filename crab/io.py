import sys

import crab.diff as diff

RED = "\033[31m"
GREEN = "\033[32m"
BOLD = "\033[1m"
UNDERLINE = "\033[4m"
RESET = "\033[0m"
ERASE = "\033[K"

USE_COLOR = sys.stdout.isatty()
if not USE_COLOR:
    RED = ""
    GREEN = ""
    BOLD = ""
    UNDERLINE = ""
    RESET = ""
    ERASE = ""


def read(fl: str) -> str:
    with open(fl, "r") as f:
        return f.read()


def echo(msg: str, end: str = "") -> None:
    print(f"\r{msg}{ERASE}", end=end)


def printr(msg: str) -> None:
    print(f"\r{msg}{ERASE}", end="")


def println(msg: str) -> None:
    print(f"\r{msg}{ERASE}")


def format_time(t: float) -> str:
    if t < 1:
        return f"{t * 1000:.3f} ms"
    return f"{t:.3f} s"


def print_ok(input: str, time: float | list[float] | None = None, end: str = "") -> None:
    if isinstance(time, list):
        time_str = " ".join(format_time(t) for t in time)
    else:
        time_str = format_time(time) if time is not None else ""
    echo(f"{BOLD}{UNDERLINE}Test {input}{RESET}    [{GREEN}OK{RESET}] {time_str}{end}")


def print_fail(input: str, time: float | None = None) -> None:
    time_str = format_time(time) if time is not None else ""
    println(f"{BOLD}{UNDERLINE}Test {input}{RESET}    [{RED}FAIL{RESET}] {time_str}")


def print_diff(str1: str, str2: str) -> None:
    println(diff.unified_diff(str1, str2, fromfile="produced", tofile="expected"))
