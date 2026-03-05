import re
import shutil
import sys

import crab.diff as diff

RED = "\033[31m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
DIM = "\033[2m"
BOLD = "\033[1m"
UNDERLINE = "\033[4m"
RESET = "\033[0m"
ERASE = "\033[K"

USE_COLOR = sys.stdout.isatty()
if not USE_COLOR:
    RED = ""
    GREEN = ""
    CYAN = ""
    YELLOW = ""
    DIM = ""
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


_MAX_CONTENT_LINES = 40


def _truncate_lines(text: str) -> str:
    lines = text.splitlines()
    if len(lines) <= _MAX_CONTENT_LINES:
        return text
    shown = lines[:_MAX_CONTENT_LINES]
    remaining = len(lines) - _MAX_CONTENT_LINES
    shown.append(f"{DIM}... {remaining} more line{'s' if remaining != 1 else ''} ...{RESET}")
    return "\n".join(shown)


def _colorize_diff(diff_str: str) -> str:
    colored = []
    for line in diff_str.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            colored.append(f"{BOLD}{line}{RESET}")
        elif line.startswith("+"):
            colored.append(f"{GREEN}{line}{RESET}")
        elif line.startswith("-"):
            colored.append(f"{RED}{line}{RESET}")
        elif line.startswith("@@"):
            colored.append(f"{CYAN}{line}{RESET}")
        else:
            colored.append(line)
    return "\n".join(colored)


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


_ansi_escape = re.compile(r"\x1b\[[0-9;]*m")


def _box_sep(label: str, width: int) -> str:
    # ├─ label ──...──┤
    inner = width - 2
    if label:
        header = f"─ {label} "
        visible_len = len(_ansi_escape.sub("", header))
        fill = "─" * max(0, inner - visible_len)
        return f"├{header}{fill}┤"
    return f"├{'─' * inner}┤"


def _box_bottom(width: int) -> str:
    return f"└{'─' * (width - 2)}┘"


def _box_row(text: str, width: int) -> str:
    inner = width - 4  # │ <content> │
    lines = text.splitlines() or [""]
    rows = []
    for line in lines:
        visible_len = len(_ansi_escape.sub("", line))
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
    parts.append(_box_sep(f"{RED}Produced{RESET}", w))
    parts.append(_box_row(_truncate_lines(produced) if produced else f"{DIM}(empty){RESET}", w))
    parts.append(_box_sep(f"{GREEN}Expected{RESET}", w))
    parts.append(_box_row(_truncate_lines(expected) if expected else f"{DIM}(empty){RESET}", w))
    parts.append(_box_sep(f"{CYAN}Diff{RESET}", w))
    diff_str = diff.unified_diff(produced, expected, fromfile="produced", tofile="expected")
    parts.append(_box_row(_colorize_diff(diff_str), w))
    parts.append(_box_bottom(w))
    println("\n".join(parts))
