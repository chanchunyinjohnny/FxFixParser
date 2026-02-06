"""Launch the FxFixParser Streamlit UI."""

import os
import subprocess
import sys


def main() -> None:
    project_root = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(project_root, "src", "fxfixparser", "ui", "app.py")
    src_path = os.path.join(project_root, "src")

    env = os.environ.copy()
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")

    sys.exit(subprocess.call([sys.executable, "-m", "streamlit", "run", app_path, *sys.argv[1:]], env=env))


if __name__ == "__main__":
    main()
