"""Unit tests for the FIX parser."""

import pytest

from fxfixparser.core.exceptions import ParseError, ValidationError
from fxfixparser.core.parser import FixParser, ParserConfig
from tests.fixtures.sample_messages import (
    INVALID_NO_BEGIN_STRING,
    INVALID_NO_CHECKSUM,
    INVALID_WRONG_ORDER,
    SIMPLE_MESSAGE,
    SPOT_MESSAGE_PIPE,
    SPOT_MESSAGE_SOH,
)


class TestFixParser:
    """Tests for FixParser class."""

    def test_parse_basic_message(self, parser: FixParser) -> None:
        """Test parsing a basic FIX message."""
        message = parser.parse(SIMPLE_MESSAGE)

        assert message.begin_string == "FIX.4.4"
        assert message.msg_type == "0"
        assert message.sender_comp_id == "SENDER"
        assert message.target_comp_id == "TARGET"

    def test_parse_pipe_delimiter(self, parser: FixParser) -> None:
        """Test parsing a message with pipe delimiter."""
        message = parser.parse(SPOT_MESSAGE_PIPE)

        assert message.begin_string == "FIX.4.4"
        assert message.msg_type == "8"
        assert message.sender_comp_id == "FXGO"

    def test_parse_soh_delimiter(self, parser: FixParser) -> None:
        """Test parsing a message with SOH delimiter."""
        message = parser.parse(SPOT_MESSAGE_SOH)

        assert message.begin_string == "FIX.4.4"
        assert message.msg_type == "8"
        assert message.sender_comp_id == "FXGO"

    def test_parse_empty_message(self, parser: FixParser) -> None:
        """Test parsing an empty message raises ParseError."""
        with pytest.raises(ParseError, match="Empty message"):
            parser.parse("")

    def test_parse_whitespace_only(self, parser: FixParser) -> None:
        """Test parsing whitespace-only message raises ParseError."""
        with pytest.raises(ParseError, match="Empty message"):
            parser.parse("   \n\t  ")

    def test_parse_invalid_no_begin_string(self, parser: FixParser) -> None:
        """Test parsing message without BeginString raises ValidationError."""
        with pytest.raises(ValidationError, match="BeginString"):
            parser.parse(INVALID_NO_BEGIN_STRING)

    def test_parse_invalid_no_checksum(self, parser: FixParser) -> None:
        """Test parsing message without CheckSum raises ValidationError."""
        with pytest.raises(ValidationError, match="CheckSum"):
            parser.parse(INVALID_NO_CHECKSUM)

    def test_parse_invalid_wrong_order(self, parser: FixParser) -> None:
        """Test parsing message with wrong field order raises ValidationError."""
        with pytest.raises(ValidationError, match="BeginString"):
            parser.parse(INVALID_WRONG_ORDER)

    def test_field_access_by_tag(self, parser: FixParser) -> None:
        """Test accessing fields by tag number."""
        message = parser.parse(SPOT_MESSAGE_PIPE)

        symbol_field = message.get_field(55)
        assert symbol_field is not None
        assert symbol_field.raw_value == "EUR/USD"

    def test_field_access_nonexistent(self, parser: FixParser) -> None:
        """Test accessing nonexistent field returns None."""
        message = parser.parse(SIMPLE_MESSAGE)

        field = message.get_field(9999)
        assert field is None

    def test_get_multiple_fields(self, parser: FixParser) -> None:
        """Test getting multiple fields with same tag."""
        message = parser.parse(SPOT_MESSAGE_PIPE)

        # Most messages have single tags, but the method should work
        fields = message.get_fields(55)
        assert len(fields) == 1
        assert fields[0].raw_value == "EUR/USD"

    def test_calculate_checksum(self) -> None:
        """Test checksum calculation."""
        # Test with simple string
        body = "8=FIX.4.4\x019=5\x0135=0\x01"
        checksum = FixParser.calculate_checksum(body)

        # Checksum should be 3 digits zero-padded
        assert len(checksum) == 3
        assert checksum.isdigit()

    def test_parser_config_defaults(self) -> None:
        """Test ParserConfig default values."""
        config = ParserConfig()

        assert config.strict_checksum is True
        assert config.strict_body_length is False
        assert config.strict_delimiter is False
        assert config.default_delimiter == "\x01"
        assert config.allow_pipe_delimiter is True


class TestCRLFNormalization:
    """Tests for CRLF normalization bug fix."""

    def test_crlf_between_fields_preserves_boundaries(self) -> None:
        """Test that CRLF between fields doesn't merge field values."""
        parser = FixParser(config=ParserConfig(strict_checksum=False))
        # Message with CRLF between tag 55 and tag 15
        msg = "8=FIX.4.4\x019=100\x0135=8\x0149=FXGO\x0156=CLIENT\x0155=EUR/USD\r\n15=EUR\x0110=000\x01"
        message = parser.parse(msg)

        assert message.get_value(55) == "EUR/USD"
        assert message.get_value(15) == "EUR"

    def test_lf_between_fields_preserves_boundaries(self) -> None:
        """Test that LF between fields doesn't merge field values."""
        parser = FixParser(config=ParserConfig(strict_checksum=False))
        msg = "8=FIX.4.4\x019=100\x0135=8\x0149=FXGO\x0156=CLIENT\x0155=EUR/USD\n15=EUR\x0110=000\x01"
        message = parser.parse(msg)

        assert message.get_value(55) == "EUR/USD"
        assert message.get_value(15) == "EUR"

    def test_cr_between_fields_preserves_boundaries(self) -> None:
        """Test that CR between fields doesn't merge field values."""
        parser = FixParser(config=ParserConfig(strict_checksum=False))
        msg = "8=FIX.4.4\x019=100\x0135=8\x0149=FXGO\x0156=CLIENT\x0155=EUR/USD\r15=EUR\x0110=000\x01"
        message = parser.parse(msg)

        assert message.get_value(55) == "EUR/USD"
        assert message.get_value(15) == "EUR"

    def test_newline_mid_value_reassembled(self) -> None:
        """Test that a newline within a field value is stripped, reassembling the value."""
        parser = FixParser(config=ParserConfig(strict_checksum=False))
        # Tag 58 (Text) value is split across two lines by log wrapping
        msg = "8=FIX.4.4\x019=100\x0135=8\x0149=FXGO\x0156=CLIENT\x0158=Long\ntext\x0110=000\x01"
        message = parser.parse(msg)

        assert message.get_value(58) == "Longtext"

    def test_crlf_mid_value_reassembled(self) -> None:
        """Test that CRLF within a field value is stripped, reassembling the value."""
        parser = FixParser(config=ParserConfig(strict_checksum=False))
        msg = "8=FIX.4.4\x019=100\x0135=8\x0149=FXGO\x0156=CLIENT\x0158=Long\r\ntext\x0110=000\x01"
        message = parser.parse(msg)

        assert message.get_value(58) == "Longtext"

    def test_crlf_before_checksum_preserves_tag10(self) -> None:
        """Test that CRLF before checksum doesn't lose tag 10."""
        parser = FixParser(config=ParserConfig(strict_checksum=False))
        msg = "8=FIX.4.4\x019=100\x0135=0\x0149=SENDER\x0156=TARGET\r\n10=000\x01"
        message = parser.parse(msg)

        assert message.checksum == "000"
        assert message.fields[-1].tag == 10


class TestStrictDelimiter:
    """Tests for strict_delimiter config option."""

    def test_strict_delimiter_config(self) -> None:
        """Test that strict_delimiter option exists and defaults to False."""
        config = ParserConfig()
        assert config.strict_delimiter is False

    def test_strict_delimiter_rejects_missing_trailing_soh(self) -> None:
        """Test that strict mode rejects fields without trailing SOH."""
        parser = FixParser(config=ParserConfig(
            strict_checksum=False,
            strict_delimiter=True,
        ))
        # Message where last field lacks trailing SOH
        msg = "8=FIX.4.4\x019=50\x0135=0\x0149=SENDER\x0156=TARGET\x0110=000"
        # In strict mode, tag 10 without trailing SOH won't be found
        with pytest.raises(ValidationError, match="CheckSum"):
            parser.parse(msg)


class TestChecksumValidation:
    """Tests for improved checksum validation."""

    def test_valid_checksum(self) -> None:
        """Test that a message with correct checksum passes validation."""
        # Build a message and compute correct checksum
        body = "8=FIX.4.4\x019=14\x0135=0\x0149=S\x0156=T\x01"
        checksum = FixParser.calculate_checksum(body)
        msg = body + f"10={checksum}\x01"

        parser = FixParser(config=ParserConfig(strict_checksum=True))
        message = parser.parse(msg)
        assert message.checksum == checksum
