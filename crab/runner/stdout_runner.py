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
    HIGH = 2


class StdoutRunner(BaseRunner):
    def __init__(self, folder: str, argc: int = 1, verbosity: Verbosity = Verbosity.NOT):
        self.folder = folder
        self.argc = argc
        self.verbosity = verbosity
        self.path = "./"

        self.command = None
        self.input = None
        self.output = None
        self.post_process = None

        self.args: Optional[list[str]] = None

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

        cproduct = list(product(*files))
        inputs = [self.input(*f) if self.input else None for f in cproduct]
        outputs = [self.output(*f) if self.output else None for f in cproduct]
        commands = [self.command(*f) for f in cproduct]

        failed = 0
        failed_tests = []
        passed = 0

        start_time = time.time()
        for input0, output0, command0, files in zip(inputs, outputs, commands, cproduct):
            test_start_time = time.time()

            all_files_str = ", ".join(files)
            program_input = io.read(input0) if input0 is not None else ""

            out, err = shell.run(command0, input=program_input, folder=self.path)
            expected_output = io.read(output0) if output0 is not None else ""
            processed_output = self.post_process(out) if self.post_process is not None else out

            cur_time = time.time()

            if processed_output == expected_output:
                io.print_ok(
                    all_files_str, cur_time - test_start_time, end=("\n" if self.verbosity == Verbosity.HIGH else "")
                )
                passed += 1
                continue

            io.print_fail(all_files_str, cur_time - test_start_time)
            failed += 1
            failed_tests.append(all_files_str)

            if self.verbosity == Verbosity.NOT:
                continue

            if err:
                io.println(f"Err: {err}")
            io.println(f"Command to reproduce: {command0}")
            io.println("Diff:")
            io.print_diff(out, expected_output)

        end_time = time.time()

        io.println("Summary:")
        io.println(f"passed: {passed}/{passed + failed}")
        io.println(f"failed: {', '.join(failed_tests) or 'none'}")

        time_elapsed = end_time - start_time
        io.println(f"time elapsed: {io.format_time(time_elapsed)}")
