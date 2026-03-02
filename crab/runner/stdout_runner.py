import time
from enum import IntEnum
from itertools import product
from pathlib import Path
from typing import Optional

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


class StdoutRunner(BaseRunner):
    def __init__(self, folder: str, argc: int = 1, verbosity: Verbosity = Verbosity.NOT):
        self.folder = folder
        self.argc = argc
        self.verbosity = verbosity
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

    def run(self) -> None:
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

        io.println(f"Running tests for suite {self.folder}")

        failed = 0
        failed_tests = []
        passed = 0
        time_elapsed = 0.0
        for input0, output0, precommand0, command0, files in zip(inputs, outputs, pre_commands, commands, cproduct):
            all_files_str = ", ".join(files)
            io.printr(f"Running test {all_files_str}")
            program_input = ""
            if input0 is not None and Path(input0).is_file():
                program_input = io.read(input0)

            test_start_time = time.time()
            if precommand0 is not None:
                _, err = shell.run(precommand0, folder=self.path)
                if err:
                    io.print_fail(all_files_str, 0)
                    if self.verbosity > Verbosity.NOT:
                        io.println(f"Command to reproduce: {precommand0}")
                        io.println(f"Precommand failed, error: {err}")
                    failed += 1
                    if self.verbosity == Verbosity.FIRST_FAIL or self.verbosity == Verbosity.FAIL_ON_COMPILE_ERROR:
                        break
                    continue

            out, err = shell.run(command0, input=program_input, folder=self.path)
            test_end_time = time.time()
            time_elapsed += test_end_time - test_start_time

            expected_output = io.read(output0) if output0 is not None else ""
            if expected_output != "" and self.pre_process is not None:
                expected_output = self.pre_process(expected_output)
            processed_output = self.post_process(out) if self.post_process is not None else out

            if processed_output == expected_output:
                io.print_ok(
                    all_files_str,
                    test_end_time - test_start_time,
                    end=("\n" if self.verbosity >= Verbosity.HIGH else ""),
                )
                passed += 1
                continue

            io.print_fail(all_files_str, test_end_time - test_start_time)
            failed += 1
            failed_tests.append(all_files_str)

            if self.verbosity == Verbosity.NOT:
                continue

            if err:
                io.println(f"Err: {err}")
            io.println(f"Command to reproduce: {precommand0} && {command0}")
            io.println("Produced:")
            io.println(processed_output)
            io.println("Expected:")
            io.println(expected_output)
            io.println("Diff:")
            io.print_diff(processed_output, expected_output)

            if self.verbosity == Verbosity.FIRST_FAIL:
                break

        io.println("Summary:")
        io.println(f"passed: {passed}/{passed + failed}")
        io.println(f"failed: {', '.join(failed_tests) or 'none'}")
        io.println(f"time elapsed: {io.format_time(time_elapsed)}")
