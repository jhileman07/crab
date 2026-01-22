import locale
from pathlib import Path
import sys
import subprocess
import time

def sort_key(s: str):
    is_reg = 0 if s.startswith('%') else 1
    if s.startswith('%') and len(s) > 1:
        return (s[1:].lower(), is_reg)
    return (s.lower(), is_reg)

def run_liveness(test: str) -> str:
    result = subprocess.run(
        ["./bin/L2", "-g", "0", "-l", "-O0", test],
        capture_output=True,
        text=True,
        check=True,
    )

    stdout = result.stdout
    stderr = result.stderr
    return stdout

def sort_single_line(line: str) -> str:
    sorted_inside = sorted(set(line.split()), key=locale.strxfrm)
    return " ".join(sorted_inside)

def sort_lines(output: str) -> str:
    lines = output.split("\n");
    result = ""
    for l in lines:
        if len(l) > 0 and l[0] == '(' and l[-1] == ')':
            inside = l[1:-1]
            result += "(" + sort_single_line(inside) + ")"
            result += "\n"
            continue

        result += l
        result += "\n"
    return result.strip() + "\n"

def ok(test: str) -> None:
    print(f"\r{test}  \033[32m[OK]\033[0m    ", end="")

def fail(test: str) -> None:
    print(f"\r{test}  \033[31m[FAIL]\033[0m    ")

def main():
    start_time = time.time()

    argv = sys.argv
    test_folder = argv[1]
    path = Path(test_folder)
    test_files = [p.name for p in path.iterdir() if not p.name.endswith(".out") and not p.name.endswith(".tmp")]

    passed = 0
    failed = 0
    failed_tests = []

    for test in test_files:
        input_file = path / test
        output_file = path / (test + ".out")
        with open(output_file, "r") as f:
            obtained_output = sort_lines(run_liveness(input_file))
            correct_output = f.read()
            if obtained_output == correct_output:
                ok(test)
                passed += 1
            else:
                fail(test)
                failed += 1
                failed_tests.append(test)
    
    end_time = time.time()
    
    print()
    print(f"passed: {passed}/{passed + failed}")
    print(f"failed tests: {", ".join(failed_tests)}")
    print(f"time elapsed: {(end_time - start_time) * 1000:.5f} ms")


if __name__ == "__main__":
    locale.setlocale(locale.LC_COLLATE, "en_US.UTF-8")
    main()
