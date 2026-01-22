import difflib

RED = "\033[31m"
GREEN = "\033[32m"
BOLD = "\033[1m"
UNDERLINE = "\033[4m"
RESET = "\033[0m"


def read(fl: str) -> str:
    with open(fl, "r") as f:
        return f.read()


def echo(msg: str, end: str = "") -> None:
    print(f"\r{msg}\033[K", end=end)


def println(msg: str) -> None:
    print(f"\r{msg}\033[K")


def print_ok(input: str, end: str = "") -> None:
    echo(f"{BOLD}{UNDERLINE}Test {input}{RESET}    [{GREEN}OK{RESET}]{end}")


def print_fail(input: str) -> None:
    println(f"{BOLD}{UNDERLINE}Test {input}{RESET}    [{RED}FAIL{RESET}]")


def print_diff(str1: str, str2: str) -> None:
    diff = difflib.unified_diff(
        str1.splitlines(keepends=True),
        str2.splitlines(keepends=True),
        fromfile="str1",
        tofile="str2",
    )

    println("".join(diff))
