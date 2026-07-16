"""Unit tests for the parsed FIX report input format converter."""

import pytest

from fxfixparser.core.exceptions import ChecksumError, ParseError, ValidationError
from fxfixparser.core.message import FixMessage
from fxfixparser.core.parser import FixParser, ParserConfig
from fxfixparser.core.report_format import looks_like_parsed_report, parsed_report_to_raw
from fxfixparser.venues.base import VenueHandler

SOH = "\x01"

SIMPLE_REPORT = (
    "(8)BeginString: FIXT.1.1\n"
    "(9)BodyLength: 100\n"
    "(34)MsgSeqNum: 42\n"
    "(35)MsgType: ExecutionReport (8)\n"
    "(55)Symbol: GBP/USD\n"
    "(10)CheckSum: 127\n"
)

GROUPED_REPORT = (
    "(8)BeginString: FIXT.1.1\n"
    "(9)BodyLength: 200\n"
    "(35)MsgType: ExecutionReport (8)\n"
    "(453)NoPartyIDs: 2\n"
    "  (447)PartyIDSource: PROPRIETARY_CUSTOM_CODE (D)\n"
    "  (448)PartyID: FIRM1\n"
    "  (802)NoPartySubIDs: 1\n"
    "    (523)PartySubID: TESTLEI00000000000AA\n"
    "    (803)PartySubIDType: LEGAL_ENTITY_IDENTIFIER (4025)\n"
    "    ----\n"
    "  (447)PartyIDSource: PROPRIETARY_CUSTOM_CODE (D)\n"
    "  (448)PartyID: FIRM2\n"
    "(10)CheckSum: 001\n"
)


class TestLooksLikeParsedReport:
    """Detection of the parsed-report layout."""

    def test_detects_simple_report(self) -> None:
        assert looks_like_parsed_report(SIMPLE_REPORT)

    def test_detects_grouped_report_with_separators(self) -> None:
        assert looks_like_parsed_report(GROUPED_REPORT)

    def test_rejects_raw_fix_with_pipes(self) -> None:
        assert not looks_like_parsed_report("8=FIX.4.4|9=100|35=8|55=EUR/USD|10=000|")

    def test_rejects_raw_fix_with_soh(self) -> None:
        raw = SOH.join(["8=FIX.4.4", "9=100", "35=8", "10=000"]) + SOH
        assert not looks_like_parsed_report(raw)

    def test_rejects_prose(self) -> None:
        assert not looks_like_parsed_report("hello world\nthis is not FIX\nat all here")

    def test_rejects_empty_and_blank(self) -> None:
        assert not looks_like_parsed_report("")
        assert not looks_like_parsed_report("   \n \n")

    def test_requires_minimum_three_report_lines(self) -> None:
        two_lines = "(8)BeginString: FIXT.1.1\n(35)MsgType: ExecutionReport (8)\n"
        assert not looks_like_parsed_report(two_lines)

    def test_tolerates_one_stray_line_in_ten(self) -> None:
        report_lines = [f"({tag})Field{tag}: value{tag}" for tag in range(1, 10)]
        text = "\n".join(["Copied from log viewer:"] + report_lines)
        assert looks_like_parsed_report(text)

    def test_rejects_mixed_text_below_threshold(self) -> None:
        text = (
            "(8)BeginString: FIXT.1.1\n"
            "(9)BodyLength: 100\n"
            "(35)MsgType: ExecutionReport (8)\n"
            "some prose line\n"
            "another prose line\n"
            "yet another prose line\n"
        )
        assert not looks_like_parsed_report(text)


class TestParsedReportToRaw:
    """Reconstruction of the raw tag=value stream."""

    def test_simple_report_reconstructed_with_msgtype_third(self) -> None:
        raw = parsed_report_to_raw(SIMPLE_REPORT)
        expected = f"8=FIXT.1.1{SOH}9=100{SOH}35=8{SOH}34=42{SOH}55=GBP/USD{SOH}10=127{SOH}"
        assert raw == expected

    def test_enum_suffix_yields_raw_code(self) -> None:
        raw = parsed_report_to_raw(
            "(8)BeginString: FIXT.1.1\n"
            "(9)BodyLength: 1\n"
            "(35)MsgType: ExecutionReport (8)\n"
            "(39)OrdStatus: FILLED (2)\n"
            "(150)ExecType: TRADE (F)\n"
            "(167)SecurityType: FX_SWAP (FXSWAP)\n"
            "(803)PartySubIDType: LEGAL_ENTITY_IDENTIFIER (4025)\n"
            "(1128)ApplVerID: FIX50SP2 (9)\n"
        )
        assert f"39=2{SOH}" in raw
        assert f"150=F{SOH}" in raw
        assert f"167=FXSWAP{SOH}" in raw
        assert f"803=4025{SOH}" in raw
        assert f"1128=9{SOH}" in raw

    def test_timestamp_colons_preserved(self) -> None:
        raw = parsed_report_to_raw(
            "(8)BeginString: FIXT.1.1\n"
            "(9)BodyLength: 1\n"
            "(35)MsgType: ExecutionReport (8)\n"
            "(52)SendingTime: 20260716-06:10:17.231761\n"
        )
        assert f"52=20260716-06:10:17.231761{SOH}" in raw

    def test_plain_values_verbatim(self) -> None:
        raw = parsed_report_to_raw(SIMPLE_REPORT)
        assert f"55=GBP/USD{SOH}" in raw

    def test_empty_value_preserved(self) -> None:
        raw = parsed_report_to_raw(
            "(8)BeginString: FIXT.1.1\n"
            "(9)BodyLength: 1\n"
            "(35)MsgType: ExecutionReport (8)\n"
            "(58)Text: \n"
        )
        assert f"58={SOH}" in raw

    def test_preserves_value_whitespace_beyond_presentation_space(self) -> None:
        raw = parsed_report_to_raw(
            "(8)BeginString: FIX.4.4\n"
            "(9)BodyLength: 1\n"
            "(35)MsgType: ExecutionReport (8)\n"
            "(58)Text:   padded  \n"
            "(10)CheckSum: 000\n"
        )
        assert f"58=  padded  {SOH}" in raw

    def test_multiword_parenthesized_value_kept_verbatim(self) -> None:
        raw = parsed_report_to_raw(
            "(8)BeginString: FIXT.1.1\n"
            "(9)BodyLength: 1\n"
            "(35)MsgType: ExecutionReport (8)\n"
            "(58)Text: SOME NOTE (draft)\n"
        )
        assert f"58=SOME NOTE (draft){SOH}" in raw

    def test_separators_and_indentation_dropped(self) -> None:
        raw = parsed_report_to_raw(GROUPED_REPORT)
        expected = (
            f"8=FIXT.1.1{SOH}9=200{SOH}35=8{SOH}"
            f"453=2{SOH}"
            f"447=D{SOH}448=FIRM1{SOH}802=1{SOH}"
            f"523=TESTLEI00000000000AA{SOH}803=4025{SOH}"
            f"447=D{SOH}448=FIRM2{SOH}"
            f"10=001{SOH}"
        )
        assert raw == expected

    def test_msgtype_already_third_left_in_place(self) -> None:
        text = (
            "(8)BeginString: FIX.4.4\n"
            "(9)BodyLength: 10\n"
            "(35)MsgType: Heartbeat (0)\n"
            "(10)CheckSum: 000\n"
        )
        raw = parsed_report_to_raw(text)
        assert raw == f"8=FIX.4.4{SOH}9=10{SOH}35=0{SOH}10=000{SOH}"

    def test_stray_lines_skipped(self) -> None:
        text = (
            "Copied from log viewer:\n"
            "(8)BeginString: FIX.4.4\n"
            "(9)BodyLength: 10\n"
            "(35)MsgType: Heartbeat (0)\n"
            "(10)CheckSum: 000\n"
        )
        raw = parsed_report_to_raw(text)
        assert raw == f"8=FIX.4.4{SOH}9=10{SOH}35=0{SOH}10=000{SOH}"

    def test_overlong_tag_raises_parse_error(self) -> None:
        text = SIMPLE_REPORT.replace("(55)Symbol: GBP/USD", f"({'9' * 100})Field: value")
        with pytest.raises(ParseError, match="Invalid tag number.*line 5"):
            parsed_report_to_raw(text)

    def test_malformed_field_shaped_line_is_not_silently_dropped(self) -> None:
        text = SIMPLE_REPORT.replace("(55)Symbol: GBP/USD", "(55)Symbol = GBP/USD")
        with pytest.raises(ParseError, match="Malformed parsed report field.*line 5"):
            parsed_report_to_raw(text)


class TestParserAcceptsParsedReport:
    """FixParser.parse() should transparently accept parsed-report text."""

    def test_parse_report_sets_flag_and_fields(self) -> None:
        message = FixParser().parse(SIMPLE_REPORT)
        assert message.converted_from_report is True
        assert message.begin_string == "FIXT.1.1"
        assert message.msg_type == "8"
        assert message.get_value(55) == "GBP/USD"

    def test_raw_message_keeps_original_report_text(self) -> None:
        message = FixParser().parse(SIMPLE_REPORT)
        assert message.raw_message == SIMPLE_REPORT

    def test_replacement_venue_handler_preserves_report_provenance(self) -> None:
        class ReplacementVenueHandler(VenueHandler):
            @property
            def name(self) -> str:
                return "Replacement"

            @property
            def sender_comp_ids(self) -> list[str]:
                return []

            def enhance_message(self, message: FixMessage) -> FixMessage:
                return FixMessage(fields=message.fields)

        message = FixParser().parse(SIMPLE_REPORT, venue=ReplacementVenueHandler())

        assert message.raw_message == SIMPLE_REPORT
        assert message.converted_from_report is True

    def test_strict_checksum_and_body_length_skipped_for_converted(self) -> None:
        # SIMPLE_REPORT's checksum (127) and body length (100) are stale
        # display values — parse must still succeed with strict toggles on.
        config = ParserConfig(strict_checksum=True, strict_body_length=True)
        message = FixParser(config).parse(SIMPLE_REPORT)
        assert message.converted_from_report is True

    def test_raw_input_still_validates_checksum(self) -> None:
        raw = "8=FIX.4.4|9=5|35=0|10=999|"
        with pytest.raises(ChecksumError):
            FixParser(ParserConfig(strict_checksum=True)).parse(raw)

    def test_raw_input_flag_defaults_false(self) -> None:
        raw = "8=FIX.4.4|9=5|35=0|10=999|"
        message = FixParser(ParserConfig(strict_checksum=False)).parse(raw)
        assert message.converted_from_report is False

    def test_pipe_character_in_report_value_not_corrupted(self) -> None:
        text = (
            "(8)BeginString: FIXT.1.1\n"
            "(9)BodyLength: 1\n"
            "(35)MsgType: ExecutionReport (8)\n"
            "(58)Text: LEFT|RIGHT\n"
            "(10)CheckSum: 000\n"
        )
        message = FixParser().parse(text)
        assert message.get_value(58) == "LEFT|RIGHT"

    def test_report_venue_autodetect_flows_through(self) -> None:
        text = (
            "(8)BeginString: FIXT.1.1\n"
            "(9)BodyLength: 1\n"
            "(35)MsgType: ExecutionReport (8)\n"
            "(49)SenderCompID: TESTSND\n"
            "(115)OnBehalfOfCompID: DOR\n"
            "(10)CheckSum: 000\n"
        )
        message = FixParser().parse(text, auto_detect_venue=True)
        assert message.venue == "Bloomberg DOR"


class TestConvertedReportStructureValidation:
    """Header/trailer ordering checks must still fire on converted input."""

    def test_report_missing_checksum_still_fails_validation(self) -> None:
        text = (
            "(8)BeginString: FIXT.1.1\n"
            "(9)BodyLength: 1\n"
            "(35)MsgType: ExecutionReport (8)\n"
            "(55)Symbol: GBP/USD\n"
        )
        with pytest.raises(ValidationError):
            FixParser().parse(text)

    def test_report_missing_msgtype_still_fails_validation(self) -> None:
        text = (
            "(8)BeginString: FIXT.1.1\n"
            "(9)BodyLength: 1\n"
            "(55)Symbol: GBP/USD\n"
            "(10)CheckSum: 000\n"
        )
        with pytest.raises(ValidationError):
            FixParser().parse(text)

    def test_all_separator_text_not_detected_as_report(self) -> None:
        assert not looks_like_parsed_report("----\n----\n----\n")
