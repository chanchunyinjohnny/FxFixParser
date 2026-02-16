"""Unit tests for venue handlers."""

import pytest

from fxfixparser.core.parser import FixParser, ParserConfig
from fxfixparser.venues.fxgo import FXGOHandler
from fxfixparser.venues.registry import VenueRegistry
from fxfixparser.venues.smart_trade import SmartTradeHandler
from fxfixparser.venues.three_sixty_t import ThreeSixtyTHandler
from tests.fixtures.sample_messages import FORWARD_MESSAGE, SPOT_MESSAGE_PIPE, SWAP_MESSAGE


class TestVenueHandlers:
    """Tests for individual venue handlers."""

    def test_fxgo_handler_properties(self) -> None:
        """Test FXGO handler properties."""
        handler = FXGOHandler()

        assert handler.name == "FXGO"
        assert "FXGO" in handler.sender_comp_ids
        assert "BLOOMBERG" in handler.sender_comp_ids

    def test_smart_trade_handler_properties(self) -> None:
        """Test Smart Trade handler properties."""
        handler = SmartTradeHandler()

        assert handler.name == "Smart Trade (LiquidityFX)"
        assert "SMARTTRADE" in handler.sender_comp_ids
        assert "LFX" in handler.sender_comp_ids

    def test_three_sixty_t_handler_properties(self) -> None:
        """Test 360T handler properties."""
        handler = ThreeSixtyTHandler()

        assert handler.name == "360T"
        assert "360T" in handler.sender_comp_ids

    def test_fxgo_matches_sender(self) -> None:
        """Test FXGO sender matching."""
        handler = FXGOHandler()

        assert handler.matches_sender("FXGO")
        assert handler.matches_sender("fxgo")
        assert handler.matches_sender("BLOOMBERG")
        assert not handler.matches_sender("360T")
        assert not handler.matches_sender(None)

    def test_smart_trade_matches_sender(self) -> None:
        """Test Smart Trade sender matching including all sender IDs."""
        handler = SmartTradeHandler()

        assert handler.matches_sender("SMARTTRADE")
        assert handler.matches_sender("smarttrade")
        assert handler.matches_sender("LFX")
        assert handler.matches_sender("lfx")
        assert handler.matches_sender("LFX_CORE")
        assert handler.matches_sender("lfx_core")
        assert handler.matches_sender("ST")
        assert handler.matches_sender("UAT.ATP.RFS.MKT")
        assert not handler.matches_sender("FXGO")

    def test_three_sixty_t_matches_sender(self) -> None:
        """Test 360T sender matching with all sender IDs."""
        handler = ThreeSixtyTHandler()

        assert handler.matches_sender("360T")
        assert handler.matches_sender("360t")
        assert handler.matches_sender("THREESIXTYT")
        assert handler.matches_sender("threesixtyt")
        assert handler.matches_sender("360TGTX")
        assert handler.matches_sender("360tgtx")
        assert not handler.matches_sender("FXGO")
        assert not handler.matches_sender(None)

    def test_extract_trade_fxgo(self) -> None:
        """Test trade extraction from FXGO execution report."""
        parser = FixParser(config=ParserConfig(strict_checksum=False))
        message = parser.parse(SPOT_MESSAGE_PIPE)

        handler = FXGOHandler()
        trade = handler.extract_trade(message)

        assert trade.symbol == "EUR/USD"
        assert trade.side == "Buy"
        assert trade.quantity == 1000000.0
        assert trade.price == 1.0850
        assert trade.currency == "EUR"
        assert trade.venue == "FXGO"

    def test_extract_trade_smart_trade(self) -> None:
        """Test trade extraction from Smart Trade swap execution report."""
        parser = FixParser(config=ParserConfig(strict_checksum=False))
        message = parser.parse(SWAP_MESSAGE)

        handler = SmartTradeHandler()
        trade = handler.extract_trade(message)

        assert trade.symbol == "USD/JPY"
        assert trade.side == "Buy"
        assert trade.quantity == 10000000.0
        assert trade.price == 148.50
        assert trade.currency == "USD"
        assert trade.venue == "Smart Trade (LiquidityFX)"
        assert trade.settlement_date == "20240117"

    def test_extract_trade_360t(self) -> None:
        """Test trade extraction from 360T forward execution report."""
        parser = FixParser(config=ParserConfig(strict_checksum=False))
        message = parser.parse(FORWARD_MESSAGE)

        handler = ThreeSixtyTHandler()
        trade = handler.extract_trade(message)

        assert trade.symbol == "EUR/USD"
        assert trade.side == "Buy"
        assert trade.quantity == 5000000.0
        assert trade.price == 1.0900
        assert trade.currency == "EUR"
        assert trade.venue == "360T"
        assert trade.settlement_date == "20240415"

    def test_enhance_message_sets_venue(self) -> None:
        """Test that enhance_message sets the venue on the message."""
        parser = FixParser(config=ParserConfig(strict_checksum=False))
        message = parser.parse(SPOT_MESSAGE_PIPE)
        assert message.venue is None

        handler = FXGOHandler()
        enhanced = handler.enhance_message(message)

        assert enhanced.venue == "FXGO"
        assert enhanced is message  # Same object, mutated

    def test_enhance_message_smart_trade(self) -> None:
        """Test enhance_message for Smart Trade venue."""
        parser = FixParser(config=ParserConfig(strict_checksum=False))
        message = parser.parse(SWAP_MESSAGE)

        handler = SmartTradeHandler()
        enhanced = handler.enhance_message(message)

        assert enhanced.venue == "Smart Trade (LiquidityFX)"


class TestVenueRegistry:
    """Tests for VenueRegistry class."""

    def test_empty_registry(self) -> None:
        """Test empty registry."""
        registry = VenueRegistry()

        assert registry.get("FXGO") is None
        assert registry.get_by_sender_id("FXGO") is None
        assert len(registry.all_venues()) == 0

    def test_register_and_get(self) -> None:
        """Test registering and retrieving handlers."""
        registry = VenueRegistry()
        handler = FXGOHandler()
        registry.register(handler)

        assert registry.get("FXGO") == handler
        assert registry.get("fxgo") == handler

    def test_get_by_sender_id(self) -> None:
        """Test getting handler by SenderCompID."""
        registry = VenueRegistry()
        registry.register(FXGOHandler())
        registry.register(SmartTradeHandler())

        assert registry.get_by_sender_id("FXGO") is not None
        assert registry.get_by_sender_id("FXGO").name == "FXGO"
        assert registry.get_by_sender_id("SMARTTRADE").name == "Smart Trade (LiquidityFX)"
        assert registry.get_by_sender_id("UNKNOWN") is None

    def test_default_registry(self, venue_registry: VenueRegistry) -> None:
        """Test default registry has all handlers."""
        venues = venue_registry.all_venues()
        venue_names = [v.name for v in venues]

        assert "FXGO" in venue_names
        assert "Smart Trade (LiquidityFX)" in venue_names
        assert "360T" in venue_names

    def test_venue_detection_from_message(self, venue_registry: VenueRegistry) -> None:
        """Test venue detection from parsed message."""
        parser = FixParser(config=ParserConfig(strict_checksum=False))

        # FXGO message
        fxgo_msg = parser.parse(SPOT_MESSAGE_PIPE)
        handler = venue_registry.get_by_sender_id(fxgo_msg.sender_comp_id)
        assert handler is not None
        assert handler.name == "FXGO"

        # 360T message
        msg_360t = parser.parse(FORWARD_MESSAGE)
        handler = venue_registry.get_by_sender_id(msg_360t.sender_comp_id)
        assert handler is not None
        assert handler.name == "360T"

        # Smart Trade message
        st_msg = parser.parse(SWAP_MESSAGE)
        handler = venue_registry.get_by_sender_id(st_msg.sender_comp_id)
        assert handler is not None
        assert handler.name == "Smart Trade (LiquidityFX)"
