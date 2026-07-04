"""A sample app whose real filesystem effect is built at RUNTIME.

Static analysis under-declares it: the argument to open() is a variable, not a literal, so
the synthesizer records only a hint ("path") — not the concrete file the program actually
writes. The dry-run observes the concrete effect. (Analyzed and executed by run_dryrun_demo.py.)
"""

import os


def run():
    env = os.environ.get("APP_ENV", "dev")                  # ENV read
    path = os.path.join("out", "report_" + env + ".log")     # dynamic filename
    with open(path, "w") as f:                               # static sees a variable, not a literal
        f.write("processed")


if __name__ == "__main__":
    run()
