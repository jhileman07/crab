import crab.process.interference as interference
import crab.process.liveness as liveness
from crab.runner.stdout_runner import StdoutRunner, Verbosity

if __name__ == "__main__":
    runner = StdoutRunner("./tests/liveness", argc=1, verbosity=Verbosity.NOT)
    runner.cd("../cs322-compiler/L2")
    runner.with_command(lambda f: f"./bin/L2 -l {f}")
    runner.with_output(lambda f: f"{f}.out")
    runner.with_args("*.L2f")
    runner.bind_postprocessor(liveness.sort_lines)
    runner.run()

    runner = StdoutRunner("./tests/interference", argc=1, verbosity=Verbosity.FIRST_FAIL)
    runner.cd("../cs322-compiler/L2")
    runner.with_command(lambda f: f"./bin/L2 -i {f}")
    runner.with_output(lambda f: f"{f}.out")
    runner.with_args("*.L2f")
    runner.bind_postprocessor(interference.sort_lines)
    runner.run()
    
    runner = StdoutRunner("./tests/spill", argc=1, verbosity=Verbosity.FIRST_FAIL)
    runner.cd("../cs322-compiler/L2")
    runner.with_command(lambda f: f"./bin/L2 -s {f}")
    runner.with_output(lambda f: f"{f}.out")
    runner.with_args("*.L2f")
    runner.run()
