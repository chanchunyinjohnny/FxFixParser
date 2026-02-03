"""Integration tests for full FIX message parsing workflow."""

import pytest

from fxfixparser.core.parser import FixParser, ParserConfig
from fxfixparser.products.base import ProductRegistry
from fxfixparser.venues.registry import VenueRegistry
from tests.fixtures.sample_messages import (
    FORWARD_MESSAGE,
    NDF_MESSAGE,
    SPOT_MESSAGE_PIPE,
    SPOT_MESSAGE_SOH,
    SWAP_MESSAGE,
)


class TestFullParseWorkflow:
    """Integration tests for complete parsing workflow."""

    @pytest.fixture
    def parser(self) -> FixParser:
        return FixParser(config=ParserConfig(strict_checksum=False))

    @pytest.fixture
    def venue_registry(self) -> VenueRegistry:
        return VenueRegistry.default()

    @pytest.fixture
    def product_registry(self) -> ProductRegistry:
        return ProductRegistry.default()

    def test_spot_trade_full_workflow(
        self,
        parser: FixParser,
        venue_registry: VenueRegistry,
        product_registry: ProductRegistry,
    ) -> None:
        """Test complete workflow for spot trade."""
        # Parse message
        message = parser.parse(SPOT_MESSAGE_PIPE)

        # Detect venue
        venue_handler = venue_registry.get_by_sender_id(message.sender_comp_id)
        assert venue_handler is not None
        message = venue_handler.enhance_message(message)

        # Detect product
        product_handler = product_registry.detect(message)
        assert product_handler is not None
        message.product_type = product_handler.product_type

        # Verify results
        assert message.venue == "FXGO"
        assert message.product_type == "Spot"
        assert message.get_value(55) == "EUR/USD"

        # Extract trade
        trade = venue_handler.extract_trade(message)
        assert trade.symbol == "EUR/USD"
        assert trade.side == "Buy"
        assert trade.quantity == 1000000.0
        assert trade.price == 1.0850

    def test_forward_trade_full_workflow(
        self,
        parser: FixParser,
        venue_registry: VenueRegistry,
        product_registry: ProductRegistry,
    ) -> None:
        """Test complete workflow for forward trade."""
        message = parser.parse(FORWARD_MESSAGE)

        venue_handler = venue_registry.get_by_sender_id(message.sender_comp_id)
        assert venue_handler is not None
        message = venue_handler.enhance_message(message)

        product_handler = product_registry.detect(message)
        assert product_handler is not None
        message.product_type = product_handler.product_type

        assert message.venue == "360T"
        assert message.product_type == "Forward"
        assert message.get_value(195) == "0.0050"  # Forward points

    def test_swap_trade_full_workflow(
        self,
        parser: FixParser,
        venue_registry: VenueRegistry,
        product_registry: ProductRegistry,
    ) -> None:
        """Test complete workflow for swap trade."""
        message = parser.parse(SWAP_MESSAGE)

        venue_handler = venue_registry.get_by_sender_id(message.sender_comp_id)
        assert venue_handler is not None
        message = venue_handler.enhance_message(message)

        product_handler = product_registry.detect(message)
        assert product_handler is not None
        message.product_type = product_handler.product_type

        assert message.venue == "Smart Trade"
        assert message.product_type == "Swap"
        assert message.get_value(64) == "20240117"  # Near leg
        assert message.get_value(193) == "20240415"  # Far leg

    def test_ndf_trade_full_workflow(
        self,
        parser: FixParser,
        venue_registry: VenueRegistry,
        product_registry: ProductRegistry,
    ) -> None:
        """Test complete workflow for NDF trade."""
        message = parser.parse(NDF_MESSAGE)

        venue_handler = venue_registry.get_by_sender_id(message.sender_comp_id)
        assert venue_handler is not None
        message = venue_handler.enhance_message(message)

        product_handler = product_registry.detect(message)
        assert product_handler is not None
        message.product_type = product_handler.product_type

        assert message.venue == "FXGO"
        assert message.product_type == "NDF"
        assert message.get_value(120) == "USD"  # Settlement currency

    def test_soh_and_pipe_produce_same_result(
        self,
        parser: FixParser,
    ) -> None:
        """Test that SOH and pipe delimited messages produce same result."""
        msg_soh = parser.parse(SPOT_MESSAGE_SOH)
        msg_pipe = parser.parse(SPOT_MESSAGE_PIPE)

        assert msg_soh.begin_string == msg_pipe.begin_string
        assert msg_soh.msg_type == msg_pipe.msg_type
        assert msg_soh.sender_comp_id == msg_pipe.sender_comp_id
        assert msg_soh.get_value(55) == msg_pipe.get_value(55)
        assert len(msg_soh.fields) == len(msg_pipe.fields)

    def test_message_to_human_readable(self, parser: FixParser) -> None:
        """Test human readable output format."""
        message = parser.parse(SPOT_MESSAGE_PIPE)

        output = message.to_human_readable()

        assert "FIX Message: FIX.4.4" in output
        assert "Symbol (55): EUR/USD" in output
        assert "Side (54): 1 (Buy)" in output

    def test_message_to_dict(self, parser: FixParser) -> None:
        """Test dictionary output format."""
        message = parser.parse(SPOT_MESSAGE_PIPE)

        d = message.to_dict()

        assert d["begin_string"] == "FIX.4.4"
        assert d["msg_type"] == "8"
        assert len(d["fields"]) > 0

        # Check field structure
        symbol_field = next((f for f in d["fields"] if f["tag"] == 55), None)
        assert symbol_field is not None
        assert symbol_field["value"] == "EUR/USD"
        assert symbol_field["name"] == "Symbol"
