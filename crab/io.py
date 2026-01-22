RED = "\033[31m"
GREEN = "\033[32m"
BOLD = "\033[1m"
UNDERLINE = "\033[4m"
RESET = "\033[0m"


def read(fl: str) -> str:
    with open(fl, "r") as f:
        return f.read()


def echo(msg: str) -> None:
    print(f"\r{msg}\033[K", end="")


def println(msg: str) -> None:
    print(f"\r{msg}\033[K")


def print_ok(input: str) -> None:
    echo(f"{BOLD}{UNDERLINE}Test {input}{RESET}    [{GREEN}OK{RESET}]")


def print_fail(input: str) -> None:
    println(f"{BOLD}{UNDERLINE}Test {input}{RESET}    [{RED}FAIL{RESET}]")
