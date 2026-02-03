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
        assert config.default_delimiter == "\x01"
        assert config.allow_pipe_delimiter is True
