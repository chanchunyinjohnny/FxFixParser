"""Integration tests for the FxFixParser CLI (run_cli.py)."""

import subprocess
import sys
from pathlib import Path

from tests.fixtures.sample_messages import BLOOMBERG_DOR_ALGO_EXEC

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI = REPO_ROOT / "run_cli.py"


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    """Invoke run_cli.py as a subprocess and capture its output."""
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        capture_output=True,
        text=True,
    )


class TestCLIVenueAutoDetection:
    """The CLI should apply venue tag definitions when auto-detecting."""

    def test_autodetect_resolves_venue_custom_tags(self) -> None:
        """Without -v, a Bloomberg DOR message resolves venue custom tags.

        Tag 22913 (LastMktSpotRate) is a Bloomberg DOR custom tag; under
        auto-detection it must render with its name rather than as
        Unknown(22913).
        """
        result = _run_cli(BLOOMBERG_DOR_ALGO_EXEC, "-o", "table")
        assert result.returncode == 0, result.stderr
        assert "LastMktSpotRate" in result.stdout
        assert "Unknown(22913)" not in result.stdout

    def test_explicit_venue_still_resolves_custom_tags(self) -> None:
        """With -v, custom tags resolve as before (regression guard)."""
        result = _run_cli(BLOOMBERG_DOR_ALGO_EXEC, "-v", "Bloomberg DOR", "-o", "table")
        assert result.returncode == 0, result.stderr
        assert "LastMktSpotRate" in result.stdout
