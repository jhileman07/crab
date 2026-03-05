import re
import shutil
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


def _box_width() -> int:
    return shutil.get_terminal_size((80, 24)).columns


def _box_top(label: str, width: int) -> str:
    # ┌─ label ──...──┐
    inner = width - 2  # exclude corner chars
    if label:
        header = f"─ {label} "
        fill = "─" * max(0, inner - len(header))
        return f"┌{header}{fill}┐"
    return f"┌{'─' * inner}┐"


def _box_sep(label: str, width: int) -> str:
    # ├─ label ──...──┤
    inner = width - 2
    if label:
        header = f"─ {label} "
        fill = "─" * max(0, inner - len(header))
        return f"├{header}{fill}┤"
    return f"├{'─' * inner}┤"


def _box_bottom(width: int) -> str:
    return f"└{'─' * (width - 2)}┘"


def _box_row(text: str, width: int) -> str:
    inner = width - 4  # │ <content> │
    lines = text.splitlines() or [""]
    rows = []
    ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
    for line in lines:
        visible_len = len(ansi_escape.sub("", line))
        padding = max(0, inner - visible_len)
        rows.append(f"│ {line}{' ' * padding} │")
    return "\n".join(rows)


def print_failure_box(
    precommand: str | None,
    command: str,
    stderr: str | None,
    produced: str,
    expected: str,
) -> None:
    w = _box_width()
    cmd_str = f"{precommand} && {command}" if precommand else command
    parts = [_box_top(f"Command: {cmd_str}", w)]
    if stderr:
        parts.append(_box_row(f"{RED}Err:{RESET} {stderr}", w))
        parts.append(_box_sep("", w))
    parts.append(_box_sep("Produced", w))
    parts.append(_box_row(produced or "(empty)", w))
    parts.append(_box_sep("Expected", w))
    parts.append(_box_row(expected or "(empty)", w))
    parts.append(_box_sep("Diff", w))
    diff_str = diff.unified_diff(produced, expected, fromfile="produced", tofile="expected")
    parts.append(_box_row(diff_str, w))
    parts.append(_box_bottom(w))
    println("\n".join(parts))
