import subprocess
import os
import platform
import sys
from pathlib import Path


def main():
    args = [sys.executable] + sys.argv[1:]
    target_path = Path("__pypackages__") / platform.python_version()[:3] / "lib"
    os.environ["PYTHONPATH"] = str(target_path)
    subprocess.check_call(args)


if __name__ == "__main__":
    main()
