import subprocess
import sys


def main():
    try:
        sys.exit(subprocess.call([sys.executable, "Crabfile"]))
    except KeyboardInterrupt:
        sys.exit(130)
