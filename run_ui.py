"""Launch the FxFixParser Streamlit UI."""

import os
import subprocess
import sys


def main() -> None:
    app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "fxfixparser", "ui", "app.py")
    sys.exit(subprocess.call([sys.executable, "-m", "streamlit", "run", app_path, *sys.argv[1:]]))


if __name__ == "__main__":
    main()
