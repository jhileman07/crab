import crab.process.liveness as liveness
from crab.runner.stdout_runner import StdoutRunner, Verbosity
from crab.shell import cd

if __name__ == "__main__":
    cd("../cs322-compiler/L2")

    runner = StdoutRunner("./tests/liveness", argc=1, verbosity=Verbosity.HIGH)
    runner = runner.with_command(lambda f: f"./bin/L2 -l {f}")
    runner = runner.with_output(lambda f: f"{f}.out")
    runner = runner.with_args("*.L2f")
    runner = runner.bind_postprocessor(liveness.sort_lines)
    runner.run()
