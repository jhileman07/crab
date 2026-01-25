# TODO: Migrate externally
import locale

import crab.shell as shell


def sort_single_line(lines: list[str]) -> str:
    sorted_inside = sorted(set(lines), key=locale.strxfrm)
    return " ".join(sorted_inside).strip()


def sort_lines(output: str) -> str:
    locale.setlocale(locale.LC_COLLATE, "en_US.UTF-8")
    lines = [line.strip() for line in output.split("\n") if len(line) > 0]
    result = ""
    for line in lines:
        tokens = line.split(" ")
        key, inside = tokens[0], sort_single_line(tokens[1:])
        result += key + " " + inside
        result += "\n"

    # ! No better way to sort them like GNU does
    sorted_result, _ = shell.run("sort", result)
    return sorted_result.strip() + "\n"
