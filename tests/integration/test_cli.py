"""Integration tests for the FxFixParser CLI (run_cli.py)."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import call, patch

import run_cli

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


class TestCLIInteractiveMode:
    """Interactive input should preserve both raw and report workflows."""

    def test_multiline_report_is_submitted_as_one_message(self) -> None:
        report_lines = [
            "(8)BeginString: FIXT.1.1",
            "(9)BodyLength: 100",
            "  (58)Text:   padded  ",
            "(10)CheckSum: 127",
        ]

        with (
            patch("builtins.input", side_effect=[*report_lines, "quit"]) as mock_input,
            patch.object(run_cli, "parse_and_display") as mock_parse,
        ):
            run_cli.interactive_mode("human", None, False, False)

        mock_parse.assert_called_once_with("\n".join(report_lines), "human", None, False, False)
        assert mock_input.call_args_list == [
            call("FIX> "),
            call("...> "),
            call("...> "),
            call("...> "),
            call("FIX> "),
        ]

    def test_raw_one_line_message_is_submitted_immediately(self) -> None:
        raw_message = "8=FIX.4.4|9=5|35=0|10=000|"

        with (
            patch("builtins.input", side_effect=[raw_message, "quit"]) as mock_input,
            patch.object(run_cli, "parse_and_display") as mock_parse,
        ):
            run_cli.interactive_mode("human", None, False, False)

        mock_parse.assert_called_once_with(raw_message, "human", None, False, False)
        assert mock_input.call_args_list == [call("FIX> "), call("FIX> ")]

    def test_blank_continuation_submits_accumulated_report_lines(self) -> None:
        report_lines = [
            "(8)BeginString: FIXT.1.1",
            "(9)BodyLength: 100",
        ]

        with (
            patch("builtins.input", side_effect=[*report_lines, "", "quit"]) as mock_input,
            patch.object(run_cli, "parse_and_display") as mock_parse,
        ):
            run_cli.interactive_mode("human", None, False, False)

        mock_parse.assert_called_once_with("\n".join(report_lines), "human", None, False, False)
        assert mock_input.call_args_list == [
            call("FIX> "),
            call("...> "),
            call("...> "),
            call("FIX> "),
        ]

    def test_eof_during_report_collection_cancels_message(self) -> None:
        with (
            patch(
                "builtins.input", side_effect=["(8)BeginString: FIXT.1.1", EOFError]
            ) as mock_input,
            patch.object(run_cli, "parse_and_display") as mock_parse,
        ):
            run_cli.interactive_mode("human", None, False, False)

        mock_parse.assert_not_called()
        assert mock_input.call_args_list == [call("FIX> "), call("...> ")]

    def test_keyboard_interrupt_during_report_collection_cancels_message(self) -> None:
        with (
            patch(
                "builtins.input",
                side_effect=["(8)BeginString: FIXT.1.1", KeyboardInterrupt],
            ) as mock_input,
            patch.object(run_cli, "parse_and_display") as mock_parse,
        ):
            run_cli.interactive_mode("human", None, False, False)

        mock_parse.assert_not_called()
        assert mock_input.call_args_list == [call("FIX> "), call("...> ")]


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
