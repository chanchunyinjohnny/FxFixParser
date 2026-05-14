"""Streamlit Community Cloud entry point for FxFixParser.

Streamlit Cloud runs the app from the repository root, but the package
lives under ``src/`` (src-layout). Add ``src/`` to ``sys.path`` before
importing so ``fxfixparser`` resolves without an editable install.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from fxfixparser.ui.app import main  # noqa: E402

main()
