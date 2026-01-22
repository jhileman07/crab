# TODO: Migrate externally
import locale


def sort_single_line(line: str) -> str:
    sorted_inside = sorted(set(line.split()), key=locale.strxfrm)
    return " ".join(sorted_inside)


def sort_lines(output: str) -> str:
    locale.setlocale(locale.LC_COLLATE, "en_US.UTF-8")
    lines = output.split("\n")
    result = ""
    for line in lines:
        if len(line) > 0 and line[0] == "(" and line[-1] == ")":
            inside = line[1:-1]
            result += "(" + sort_single_line(inside) + ")"
            result += "\n"
            continue

        result += line
        result += "\n"
    return result.strip() + "\n"
