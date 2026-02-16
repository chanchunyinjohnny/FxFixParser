"""Unit tests for FixMessage and related classes."""

import pytest

from fxfixparser.core.field import FixField, FixFieldDefinition
from fxfixparser.core.message import FixMessage, ParsedTrade


class TestFixFieldDefinition:
    """Tests for FixFieldDefinition class."""

    def test_basic_definition(self) -> None:
        """Test creating a basic field definition."""
        defn = FixFieldDefinition(tag=55, name="Symbol", field_type="STRING")

        assert defn.tag == 55
        assert defn.name == "Symbol"
        assert defn.field_type == "STRING"
        assert defn.description == ""
        assert defn.valid_values == {}

    def test_definition_with_valid_values(self) -> None:
        """Test definition with enumerated values."""
        defn = FixFieldDefinition(
            tag=54,
            name="Side",
            field_type="CHAR",
            valid_values={"1": "Buy", "2": "Sell"},
        )

        assert defn.get_value_description("1") == "Buy"
        assert defn.get_value_description("2") == "Sell"
        assert defn.get_value_description("3") is None


class TestFixField:
    """Tests for FixField class."""

    def test_field_without_definition(self) -> None:
        """Test field without definition."""
        field = FixField(tag=9999, raw_value="test")

        assert field.tag == 9999
        assert field.raw_value == "test"
        assert field.name == "Unknown(9999)"
        assert field.description == ""
        assert field.value_description is None
        assert field.typed_value == "test"

    def test_field_with_definition(self) -> None:
        """Test field with definition."""
        defn = FixFieldDefinition(
            tag=55, name="Symbol", field_type="STRING", description="Instrument symbol"
        )
        field = FixField(tag=55, raw_value="EUR/USD", definition=defn)

        assert field.name == "Symbol"
        assert field.description == "Instrument symbol"

    def test_field_typed_value_int(self) -> None:
        """Test typed value conversion for INT type."""
        defn = FixFieldDefinition(tag=34, name="MsgSeqNum", field_type="INT")
        field = FixField(tag=34, raw_value="123", definition=defn)

        assert field.typed_value == 123
        assert isinstance(field.typed_value, int)

    def test_field_typed_value_float(self) -> None:
        """Test typed value conversion for FLOAT type."""
        defn = FixFieldDefinition(tag=31, name="LastPx", field_type="PRICE")
        field = FixField(tag=31, raw_value="1.0850", definition=defn)

        assert field.typed_value == 1.0850
        assert isinstance(field.typed_value, float)

    def test_field_typed_value_boolean(self) -> None:
        """Test typed value conversion for BOOLEAN type."""
        defn = FixFieldDefinition(tag=43, name="PossDupFlag", field_type="BOOLEAN")

        field_yes = FixField(tag=43, raw_value="Y", definition=defn)
        assert field_yes.typed_value is True

        field_no = FixField(tag=43, raw_value="N", definition=defn)
        assert field_no.typed_value is False

    def test_field_typed_value_boolean_numeric(self) -> None:
        """Test typed value conversion for BOOLEAN type with numeric 1/0 values."""
        defn = FixFieldDefinition(tag=43, name="PossDupFlag", field_type="BOOLEAN")

        field_one = FixField(tag=43, raw_value="1", definition=defn)
        assert field_one.typed_value is True

        field_zero = FixField(tag=43, raw_value="0", definition=defn)
        assert field_zero.typed_value is False

    def test_field_typed_value_int_invalid_returns_raw(self) -> None:
        """Test that invalid INT values return raw string without crashing."""
        defn = FixFieldDefinition(tag=34, name="MsgSeqNum", field_type="INT")
        field = FixField(tag=34, raw_value="abc", definition=defn)

        assert field.typed_value == "abc"

    def test_field_typed_value_float_invalid_returns_raw(self) -> None:
        """Test that invalid FLOAT values return raw string without crashing."""
        defn = FixFieldDefinition(tag=31, name="LastPx", field_type="PRICE")
        field = FixField(tag=31, raw_value="not_a_number", definition=defn)

        assert field.typed_value == "not_a_number"

    def test_field_value_description(self) -> None:
        """Test value description for enumerated fields."""
        defn = FixFieldDefinition(
            tag=54,
            name="Side",
            field_type="CHAR",
            valid_values={"1": "Buy", "2": "Sell"},
        )
        field = FixField(tag=54, raw_value="1", definition=defn)

        assert field.value_description == "Buy"

    def test_field_to_dict(self) -> None:
        """Test field to_dict conversion."""
        defn = FixFieldDefinition(
            tag=54,
            name="Side",
            field_type="CHAR",
            description="Side of order",
            valid_values={"1": "Buy"},
        )
        field = FixField(tag=54, raw_value="1", definition=defn)

        d = field.to_dict()
        assert d["tag"] == 54
        assert d["name"] == "Side"
        assert d["value"] == "1"
        assert d["value_description"] == "Buy"
        assert d["field_description"] == "Side of order"

    def test_field_str(self) -> None:
        """Test field string representation."""
        defn = FixFieldDefinition(
            tag=54, name="Side", field_type="CHAR", valid_values={"1": "Buy"}
        )
        field = FixField(tag=54, raw_value="1", definition=defn)

        assert str(field) == "Side (54): 1 (Buy)"


class TestFixMessage:
    """Tests for FixMessage class."""

    def test_empty_message(self) -> None:
        """Test empty message."""
        message = FixMessage()

        assert len(message) == 0
        assert message.begin_string is None
        assert message.msg_type is None

    def test_message_with_fields(self) -> None:
        """Test message with fields."""
        fields = [
            FixField(tag=8, raw_value="FIX.4.4"),
            FixField(tag=9, raw_value="100"),
            FixField(tag=35, raw_value="8"),
        ]
        message = FixMessage(fields=fields)

        assert len(message) == 3
        assert message.begin_string == "FIX.4.4"
        assert message.msg_type == "8"

    def test_message_iteration(self) -> None:
        """Test iterating over message fields."""
        fields = [
            FixField(tag=8, raw_value="FIX.4.4"),
            FixField(tag=35, raw_value="8"),
        ]
        message = FixMessage(fields=fields)

        tags = [f.tag for f in message]
        assert tags == [8, 35]

    def test_message_to_dict(self) -> None:
        """Test message to_dict conversion."""
        fields = [
            FixField(tag=8, raw_value="FIX.4.4"),
            FixField(tag=35, raw_value="8"),
            FixField(tag=49, raw_value="SENDER"),
        ]
        message = FixMessage(fields=fields, venue="TestVenue")

        d = message.to_dict()
        assert d["begin_string"] == "FIX.4.4"
        assert d["msg_type"] == "8"
        assert d["venue"] == "TestVenue"
        assert len(d["fields"]) == 3


class TestParsedTrade:
    """Tests for ParsedTrade class."""

    def test_empty_trade(self) -> None:
        """Test empty trade."""
        trade = ParsedTrade()

        assert trade.symbol is None
        assert trade.side is None
        assert trade.quantity is None

    def test_trade_with_values(self) -> None:
        """Test trade with values."""
        trade = ParsedTrade(
            symbol="EUR/USD",
            side="Buy",
            quantity=1000000.0,
            price=1.0850,
            venue="FXGO",
        )

        assert trade.symbol == "EUR/USD"
        assert trade.side == "Buy"
        assert trade.quantity == 1000000.0

    def test_trade_to_dict(self) -> None:
        """Test trade to_dict conversion."""
        trade = ParsedTrade(symbol="EUR/USD", side="Buy")

        d = trade.to_dict()
        assert d["symbol"] == "EUR/USD"
        assert d["side"] == "Buy"
        assert d["quantity"] is None
