import statistics
from enum import IntEnum
from itertools import product
from pathlib import Path
from typing import Optional

import polars as pl

import crab.diff as diff
import crab.io as io
import crab.shell as shell
import crab.tool as tool

from .base_runner import BaseRunner


class Verbosity(IntEnum):
    NOT = 0
    SOME = 1
    FIRST_FAIL = 2
    FAIL_ON_COMPILE_ERROR = 3
    HIGH = 4


class StdoutRunner(BaseRunner[pl.DataFrame]):
    def __init__(self, folder: str, argc: int = 1, verbosity: Verbosity = Verbosity.NOT):
        self.folder = folder
        self.argc = argc
        self.verbosity = verbosity
        self.repeat_count = 1
        self.path = "./"

        self.pre_command = None
        self.command = None
        self.input = None
        self.output = None
        self.pre_process = None
        self.post_process = None

        self.args: Optional[list[str]] = None

    def with_pre_command(self, fn) -> None:
        self.pre_command = fn
        if not tool.has_arity(self.pre_command, self.argc)[0]:
            raise ValueError(f"self.pre_command must be a function of arity {self.argc}")

    def with_command(self, fn) -> None:
        self.command = fn
        if not tool.has_arity(self.command, self.argc)[0]:
            raise ValueError(f"self.command must be a function of arity {self.argc}")

    def with_input(self, fn, optional: bool = True) -> None:
        self.input = fn
        if not tool.has_arity(self.input, self.argc)[0]:
            raise ValueError(f"self.input must be a function of arity {self.argc}")

    def with_output(self, fn) -> None:
        self.output = fn
        if not tool.has_arity(self.output, self.argc)[0]:
            raise ValueError(f"self.output must be a function of arity {self.argc}")

    def with_repeat_count(self, n: int) -> None:
        self.repeat_count = n

    def with_args(self, *args: str) -> None:
        num_args = len(args)
        if num_args != self.argc:
            raise ValueError(f"must have the same number of args as argc, got {num_args} expected {self.argc}")
        self.args = list(args)

    def bind_preprocessor(self, fn) -> None:
        self.pre_process = fn

    def bind_postprocessor(self, fn) -> None:
        self.post_process = fn

    def cd(self, path: str) -> None:
        self.path = path

    def _build_test_cases(self):
        # ! Precondition: all lambdas have the correct arity
        if self.command is None:
            raise ValueError("Cannot run shell tests without a command")
        if self.args is None or len(self.args) != self.argc:
            raise ValueError("Insufficient arguments provided to run tests")

        files = [tool.get_files(Path(self.path) / self.folder, arg) for arg in self.args]
        if self.argc == 1:
            files = [sorted(files[0], key=lambda f: Path(f).stat().st_size)]
        cproduct = list(product(*files))
        inputs = [self.input(*f) if self.input else None for f in cproduct]
        outputs = [self.output(*f) if self.output else None for f in cproduct]
        pre_commands = [self.pre_command(*f) if self.pre_command else None for f in cproduct]
        commands = [self.command(*f) for f in cproduct]
        return cproduct, inputs, outputs, pre_commands, commands

    def _execute(self, command0: str, program_input: str) -> tuple[list[float], str, str | None]:
        results = [shell.run(command0, input=program_input, folder=self.path) for _ in range(self.repeat_count)]
        all_times = [dt for _, _, dt in results]
        last_out = next((out for out, _, _ in reversed(results) if out), "")
        combined_err = "\n".join(err for _, err, _ in results if err) or None
        return all_times, last_out, combined_err

    def _make_row(
        self, test: str, passed: bool, all_times: list[float], stderr: str | None, diff_b64: bytes | None
    ) -> dict:
        return {
            "test": test,
            "passed": passed,
            "time_mean_s": statistics.mean(all_times) if all_times else 0.0,
            "time_min_s": min(all_times) if all_times else 0.0,
            "time_max_s": max(all_times) if all_times else 0.0,
            "time_all_s": all_times,
            "stderr": stderr,
            "diff_b64": diff_b64,
        }

    def _print_failure_details(
        self, precommand0, command0: str, stderr: str | None, produced: str, expected: str
    ) -> None:
        io.print_failure_box(precommand0, command0, stderr, produced, expected)

    def _to_dataframe(self, rows: list[dict]) -> pl.DataFrame:
        return pl.DataFrame(
            rows,
            schema={
                "test": pl.String,
                "passed": pl.Boolean,
                "time_mean_s": pl.Float64,
                "time_min_s": pl.Float64,
                "time_max_s": pl.Float64,
                "time_all_s": pl.List(pl.Float64),
                "stderr": pl.String,
                "diff_b64": pl.Binary,
            },
        )

    def run(self) -> pl.DataFrame:
        cproduct, inputs, outputs, pre_commands, commands = self._build_test_cases()

        io.println(f"Running tests for suite {self.folder}")

        failed = 0
        failed_tests = []
        passed = 0
        time_elapsed = 0.0
        rows = []
        for input0, output0, precommand0, command0, files in zip(inputs, outputs, pre_commands, commands, cproduct):
            all_files_str = ", ".join(files)
            test_name = ", ".join(Path(f).name for f in files)
            io.printr(f"Running test {all_files_str}")
            program_input = io.read(input0) if input0 is not None and Path(input0).is_file() else ""

            if precommand0 is not None:
                _, err, _ = shell.run(precommand0, folder=self.path)
                if err:
                    io.print_fail(all_files_str, 0)
                    failed += 1
                    rows.append(self._make_row(test=test_name, passed=False, all_times=[], stderr=err, diff_b64=None))
                    if self.verbosity > Verbosity.NOT:
                        io.print_precommand_failure_box(precommand0, err)
                    if self.verbosity == Verbosity.FIRST_FAIL or self.verbosity == Verbosity.FAIL_ON_COMPILE_ERROR:
                        break
                    continue

            all_times, last_out, combined_err = self._execute(command0, program_input)
            time_elapsed += sum(all_times)

            expected_output = io.read(output0).strip() if output0 is not None else ""
            if expected_output != "" and self.pre_process is not None:
                expected_output = self.pre_process(expected_output)
            processed_output = (
                self.post_process(last_out.strip()) if self.post_process is not None else last_out.strip()
            )

            if processed_output == expected_output:
                io.print_ok(all_files_str, all_times, end="\n" if self.verbosity >= Verbosity.HIGH else "")
                passed += 1
                rows.append(
                    self._make_row(test=test_name, passed=True, all_times=all_times, stderr=combined_err, diff_b64=None)
                )
                continue

            io.print_fail(all_files_str, all_times[-1])
            failed += 1
            failed_tests.append(all_files_str)
            rows.append(
                self._make_row(
                    test=test_name,
                    passed=False,
                    all_times=all_times,
                    stderr=combined_err,
                    diff_b64=diff.unified_diff_b64(
                        expected_output, processed_output, fromfile="expected", tofile="actual"
                    ),
                )
            )

            if self.verbosity == Verbosity.NOT:
                continue

            self._print_failure_details(precommand0, command0, combined_err, processed_output, expected_output)

            if self.verbosity == Verbosity.FIRST_FAIL:
                break

        io.println("Summary:")
        io.println(f"passed: {passed}/{passed + failed}")
        io.println(f"failed: {', '.join(failed_tests) or 'none'}")
        io.println(f"time elapsed: {io.format_time(time_elapsed)}")

        return self._to_dataframe(rows)
