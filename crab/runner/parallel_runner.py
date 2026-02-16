import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import reduce
from itertools import product
from pathlib import Path
from typing import Callable

import crab.io as io
import crab.shell as shell
import crab.tool as tool

from .base_runner import BaseRunner
from .stdout_runner import Verbosity


class StageResult:
    """Result monad for pipeline execution. Carries stdout on success,
    stderr + stage index on failure. and_then is monadic bind that
    short-circuits on failure."""

    def __init__(self, out: str, err: str, failed_stage: int | None = None):
        self.out = out
        self.err = err
        self.failed_stage = failed_stage

    @staticmethod
    def ok(out: str = "") -> StageResult:
        return StageResult(out=out, err="")

    @staticmethod
    def fail(err: str, stage: int) -> StageResult:
        return StageResult(out="", err=err, failed_stage=stage)

    @property
    def is_ok(self) -> bool:
        return self.failed_stage is None

    def and_then(self, fn: Callable[[str], StageResult]) -> StageResult:
        if not self.is_ok:
            return self
        return fn(self.out)


@dataclass
class Stage:
    command: Callable
    cwd: str


@dataclass
class TestResult:
    files_str: str
    commands: list[str]
    passed: bool
    elapsed: float
    produced: str
    expected: str
    err: str
    failed_stage: int | None = None


class ParallelRunner(BaseRunner):
    def __init__(self, folder: str, argc: int = 1, verbosity: Verbosity = Verbosity.NOT, workers: int = 4):
        self.folder = folder
        self.argc = argc
        self.verbosity = verbosity
        self.workers = workers
        self.path = "./"

        self.stages: list[Stage] = []
        self.input = None
        self.input_optional = True
        self.output = None
        self.pre_process = None
        self.post_process = None

        self.args: list[str] | None = None

    def add_stage(self, command_fn: Callable, cwd: str = "./") -> None:
        if not tool.has_arity(command_fn, self.argc)[0]:
            raise ValueError(f"stage command must be a function of arity {self.argc}")
        self.stages.append(Stage(command=command_fn, cwd=cwd))

    def with_input(self, fn: Callable, optional: bool = True) -> None:
        self.input = fn
        self.input_optional = optional
        if not tool.has_arity(self.input, self.argc)[0]:
            raise ValueError(f"self.input must be a function of arity {self.argc}")

    def with_output(self, fn: Callable) -> None:
        self.output = fn
        if not tool.has_arity(self.output, self.argc)[0]:
            raise ValueError(f"self.output must be a function of arity {self.argc}")

    def with_args(self, *args: str) -> None:
        num_args = len(args)
        if num_args != self.argc:
            raise ValueError(f"must have the same number of args as argc, got {num_args} expected {self.argc}")
        self.args = list(args)

    def bind_preprocessor(self, fn: Callable) -> None:
        self.pre_process = fn

    def bind_postprocessor(self, fn: Callable) -> None:
        self.post_process = fn

    def cd(self, path: str) -> None:
        self.path = path

    @staticmethod
    def _exec_stage(cmd: str, stdin: str, cwd: str, idx: int) -> Callable[[str], StageResult]:
        def run(_prev: str) -> StageResult:
            out, err = shell.run(cmd, input=stdin, folder=cwd)
            if err:
                return StageResult.fail(err, idx)
            return StageResult.ok(out)
        return run

    def _run_single(self, files: tuple, input_file: str | None, output_file: str | None) -> TestResult:
        all_files_str = ", ".join(files)
        commands = [stage.command(*files) for stage in self.stages]

        program_input = ""
        if input_file is not None and not (self.input_optional and not os.path.isfile(input_file)):
            program_input = io.read(input_file)

        test_start = time.time()

        # Build stage functions: intermediate stages get no stdin, final stage gets program_input
        stage_fns: list[Callable[[str], StageResult]] = [
            self._exec_stage(cmd, "", stage.cwd, i)
            for i, (stage, cmd) in enumerate(zip(self.stages[:-1], commands[:-1]))
        ]
        last_idx = len(self.stages) - 1
        stage_fns.append(self._exec_stage(commands[-1], program_input, self.stages[-1].cwd, last_idx))

        result = reduce(lambda r, fn: r.and_then(fn), stage_fns, StageResult.ok())

        elapsed = time.time() - test_start

        expected_output = io.read(output_file) if output_file is not None else ""
        if expected_output != "" and self.pre_process is not None:
            expected_output = self.pre_process(expected_output)
        produced = self.post_process(result.out) if self.post_process is not None else result.out

        return TestResult(
            files_str=all_files_str,
            commands=commands,
            passed=result.is_ok and produced == expected_output,
            elapsed=elapsed,
            produced=produced,
            expected=expected_output,
            err=result.err,
            failed_stage=result.failed_stage,
        )

    def run(self) -> None:
        if not self.stages:
            raise ValueError("Cannot run without at least one stage (use add_stage)")
        if self.args is None or len(self.args) != self.argc:
            raise ValueError("Insufficient arguments provided to run tests")

        files = [tool.get_files(Path(self.path) / self.folder, arg) for arg in self.args]
        cproduct = list(product(*files))
        inputs = [self.input(*f) if self.input else None for f in cproduct]
        outputs = [self.output(*f) if self.output else None for f in cproduct]

        io.println(f"Running tests for suite {self.folder} ({len(cproduct)} tests, {self.workers} workers)")

        wall_start = time.time()

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = [
                executor.submit(self._run_single, f, inp, out)
                for f, inp, out in zip(cproduct, inputs, outputs)
            ]
            results = [future.result() for future in futures]

        wall_elapsed = time.time() - wall_start

        failed = 0
        failed_tests = []
        passed = 0

        for result in results:
            if result.passed:
                io.print_ok(
                    result.files_str, result.elapsed, end=("\n" if self.verbosity >= Verbosity.HIGH else "")
                )
                passed += 1
                continue

            io.print_fail(result.files_str, result.elapsed)
            failed += 1
            failed_tests.append(result.files_str)

            if self.verbosity == Verbosity.NOT:
                continue

            if result.failed_stage is not None:
                io.println(f"Stage {result.failed_stage} failed: {result.commands[result.failed_stage]}")
            if result.err:
                io.println(f"Err: {result.err}")
            io.println("Pipeline to reproduce:")
            for cmd in result.commands:
                io.println(f"  {cmd}")
            if result.produced or result.expected:
                io.println("Produced:")
                io.println(result.produced)
                io.println("Expected:")
                io.println(result.expected)
                io.println("Diff:")
                io.print_diff(result.produced, result.expected)

            if self.verbosity == Verbosity.FIRST_FAIL:
                break

        io.println("Summary:")
        io.println(f"passed: {passed}/{passed + failed}")
        io.println(f"failed: {', '.join(failed_tests) or 'none'}")
        io.println(f"wall time: {io.format_time(wall_elapsed)}")
