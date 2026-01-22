import time
from enum import IntEnum
from itertools import product
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

        self.command = None
        self.input = None
        self.output = None
        self.post_process = None

        self.args: Optional[list[str]] = None

    def with_command(self, fn) -> StdoutRunner:
        self.command = fn
        if not tool.has_arity(self.command, self.argc)[0]:
            raise ValueError(f"self.command must be a function of arity {self.argc}")
        return self

    def with_input(self, fn, optional: bool = True) -> StdoutRunner:
        self.input = fn
        if not tool.has_arity(self.input, self.argc)[0]:
            raise ValueError(f"self.input must be a function of arity {self.argc}")
        return self

    def with_output(self, fn) -> StdoutRunner:
        self.output = fn
        if not tool.has_arity(self.output, self.argc)[0]:
            raise ValueError(f"self.output must be a function of arity {self.argc}")
        return self

    def with_args(self, *args: str) -> StdoutRunner:
        num_args = len(args)
        if num_args != self.argc:
            raise ValueError(f"must have the same number of args as argc, got {num_args} expected {self.argc}")
        self.args = list(args)
        return self

    def bind_postprocessor(self, fn) -> StdoutRunner:
        self.post_process = fn
        return self

    def run(self) -> None:
        # ! Precondition: all lambdas have the correct arity
        if self.command is None:
            raise ValueError("Cannot run shell tests without a command")
        if self.args is None or len(self.args) != self.argc:
            raise ValueError("Insufficient arguments provided to run tests")

        files = [tool.get_files(self.folder, arg) for arg in self.args]

        cproduct = product(*files)
        inputs = [self.input(*f) if self.input else None for f in cproduct]
        outputs = [self.output(*f) if self.output else None for f in cproduct]
        commands = [self.command(*f) for f in cproduct]

        failed = 0
        failed_tests = []
        passed = 0

        start_time = time.time()
        for input0, output0, command0, files in zip(inputs, outputs, commands, cproduct):
            all_files_str = ", ".join(files)
            program_input = io.read(input0) if input0 is not None else ""

            out, err = shell.run(command0, input=program_input)
            expected_output = io.read(output0) if output0 is not None else ""
            processed_output = self.post_process(out) if self.post_process is not None else out

            if processed_output == expected_output:
                io.print_ok(all_files_str, end=("\n" if self.verbosity == Verbosity.HIGH else ""))
                passed += 1
                continue

            io.print_fail(all_files_str)
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
        if time_elapsed < 1:
            io.println(f"time elapsed: {time_elapsed * 1000:.5f} ms")
        else:
            io.println(f"time elapsed: {time_elapsed} s")
