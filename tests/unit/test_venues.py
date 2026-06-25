"""Unit tests for venue handlers."""

from typing import Mapping

from fxfixparser.core.field import FixField
from fxfixparser.core.message import FixMessage, ParsedTrade
from fxfixparser.core.parser import FixParser, ParserConfig
from fxfixparser.products.base import ProductRegistry
from fxfixparser.venues.bloomberg_dor import BloombergDORHandler
from fxfixparser.venues.fxgo import FXGOHandler
from fxfixparser.venues.registry import VenueRegistry
from fxfixparser.venues.smart_trade import SmartTradeHandler
from fxfixparser.venues.three_sixty_t import ThreeSixtyTHandler
from tests.fixtures.sample_messages import (
    BLOOMBERG_DOR_GENERIC_COMPID_EXEC,
    BLOOMBERG_DOR_SPOT_EXEC,
    BLOOMBERG_DOR_SPOT_RFQ,
    FORWARD_MESSAGE,
    SIMPLE_MESSAGE,
    SPOT_MESSAGE_PIPE,
    SWAP_MESSAGE,
)


class TestVenueHandlers:
    """Tests for individual venue handlers."""

    def test_fxgo_handler_properties(self) -> None:
        """Test FXGO handler properties."""
        handler = FXGOHandler()

        assert handler.name == "Bloomberg FXGO"
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

        assert handler.name == "360T RFS"
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
        assert trade.venue == "Bloomberg FXGO"

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
        assert trade.venue == "360T RFS"
        assert trade.settlement_date == "20240415"

    def test_enhance_message_sets_venue(self) -> None:
        """Test that enhance_message sets the venue on the message."""
        parser = FixParser(config=ParserConfig(strict_checksum=False))
        message = parser.parse(SPOT_MESSAGE_PIPE)
        assert message.venue is None

        handler = FXGOHandler()
        enhanced = handler.enhance_message(message)

        assert enhanced.venue == "Bloomberg FXGO"
        assert enhanced is message  # Same object, mutated

    def test_enhance_message_smart_trade(self) -> None:
        """Test enhance_message for Smart Trade venue."""
        parser = FixParser(config=ParserConfig(strict_checksum=False))
        message = parser.parse(SWAP_MESSAGE)

        handler = SmartTradeHandler()
        enhanced = handler.enhance_message(message)

        assert enhanced.venue == "Smart Trade (LiquidityFX)"

    def test_bloomberg_dor_handler_properties(self) -> None:
        handler = BloombergDORHandler()
        assert handler.name == "Bloomberg DOR"
        assert "BLOOMBERG_DOR" in handler.sender_comp_ids
        assert "DOR" in handler.sender_comp_ids

    def test_bloomberg_dor_matches_sender(self) -> None:
        handler = BloombergDORHandler()
        assert handler.matches_sender("BLOOMBERG_DOR")
        assert handler.matches_sender("bloomberg_dor")
        assert handler.matches_sender("DOR")
        assert handler.matches_sender("FXOM")
        assert not handler.matches_sender("FXGO")
        assert not handler.matches_sender(None)

    def test_extract_trade_bloomberg_dor(self) -> None:
        parser = FixParser(config=ParserConfig(strict_checksum=False))
        message = parser.parse(BLOOMBERG_DOR_SPOT_EXEC, venue="Bloomberg DOR")
        handler = BloombergDORHandler()
        trade = handler.extract_trade(message)
        assert trade.symbol == "EUR/USD"
        assert trade.side == "Buy"
        assert trade.quantity == 1000000.0
        assert trade.price == 1.08500
        assert trade.currency == "EUR"
        assert trade.venue == "Bloomberg DOR"


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

        assert registry.get("Bloomberg FXGO") == handler
        assert registry.get("bloomberg fxgo") == handler

    def test_get_by_sender_id(self) -> None:
        """Test getting handler by SenderCompID."""
        registry = VenueRegistry()
        registry.register(FXGOHandler())
        registry.register(SmartTradeHandler())

        fxgo = registry.get_by_sender_id("FXGO")
        smart_trade = registry.get_by_sender_id("SMARTTRADE")
        assert fxgo is not None
        assert smart_trade is not None
        assert fxgo.name == "Bloomberg FXGO"
        assert smart_trade.name == "Smart Trade (LiquidityFX)"
        assert registry.get_by_sender_id("UNKNOWN") is None

    def test_default_registry(self, venue_registry: VenueRegistry) -> None:
        """Test default registry has all handlers."""
        venues = venue_registry.all_venues()
        venue_names = [v.name for v in venues]

        assert "Bloomberg FXGO" in venue_names
        assert "Smart Trade (LiquidityFX)" in venue_names
        assert "360T RFS" in venue_names
        assert "360T TI" in venue_names

    def test_venue_detection_from_message(self, venue_registry: VenueRegistry) -> None:
        """Test venue detection from parsed message."""
        parser = FixParser(config=ParserConfig(strict_checksum=False))

        # FXGO message
        fxgo_msg = parser.parse(SPOT_MESSAGE_PIPE)
        handler = venue_registry.get_by_sender_id(fxgo_msg.sender_comp_id)
        assert handler is not None
        assert handler.name == "Bloomberg FXGO"

        # 360T message
        msg_360t = parser.parse(FORWARD_MESSAGE)
        handler = venue_registry.get_by_sender_id(msg_360t.sender_comp_id)
        assert handler is not None
        assert handler.name == "360T RFS"

        # Smart Trade message
        st_msg = parser.parse(SWAP_MESSAGE)
        handler = venue_registry.get_by_sender_id(st_msg.sender_comp_id)
        assert handler is not None
        assert handler.name == "Smart Trade (LiquidityFX)"

    def test_default_registry_includes_bloomberg_dor(self, venue_registry: VenueRegistry) -> None:
        venues = venue_registry.all_venues()
        venue_names = [v.name for v in venues]
        assert "Bloomberg DOR" in venue_names

    def test_bloomberg_venues_are_adjacent(self, venue_registry: VenueRegistry) -> None:
        """Bloomberg FXGO and Bloomberg DOR sit next to each other so the UI
        dropdown groups the two Bloomberg entries together."""
        names = [v.name for v in venue_registry.all_venues()]
        assert names.index("Bloomberg DOR") == names.index("Bloomberg FXGO") + 1

    def test_360t_venues_are_adjacent(self, venue_registry: VenueRegistry) -> None:
        """360T RFS and 360T TI sit next to each other so the UI dropdown groups
        the two 360T interfaces together."""
        names = [v.name for v in venue_registry.all_venues()]
        assert names.index("360T TI") == names.index("360T RFS") + 1

    def test_venue_detection_bloomberg_dor(self, venue_registry: VenueRegistry) -> None:
        parser = FixParser(config=ParserConfig(strict_checksum=False))
        msg = parser.parse(BLOOMBERG_DOR_SPOT_EXEC)
        handler = venue_registry.get_by_sender_id(msg.sender_comp_id)
        assert handler is not None
        assert handler.name == "Bloomberg DOR"

    def test_detect_from_message_by_sender(self, venue_registry: VenueRegistry) -> None:
        """detect_from_message resolves a venue from SenderCompID (49)."""
        parser = FixParser(config=ParserConfig(strict_checksum=False))
        msg = parser.parse(BLOOMBERG_DOR_SPOT_EXEC)
        handler = venue_registry.detect_from_message(msg)
        assert handler is not None
        assert handler.name == "Bloomberg DOR"

    def test_detect_from_message_by_target(self, venue_registry: VenueRegistry) -> None:
        """detect_from_message resolves client-to-venue messages via the
        TargetCompID (56) / OnBehalfOfCompID (115) when the sender is the
        client rather than the venue."""
        parser = FixParser(config=ParserConfig(strict_checksum=False))
        msg = parser.parse(BLOOMBERG_DOR_SPOT_RFQ)

        # Sender alone does not identify the venue here.
        assert msg.sender_comp_id == "CLIENT"
        assert venue_registry.get_by_sender_id(msg.sender_comp_id) is None

        handler = venue_registry.detect_from_message(msg)
        assert handler is not None
        assert handler.name == "Bloomberg DOR"

    def test_detect_from_message_returns_none_when_no_match(
        self, venue_registry: VenueRegistry
    ) -> None:
        """detect_from_message returns None when no comp ID matches a venue."""
        parser = FixParser(config=ParserConfig(strict_checksum=False))
        msg = parser.parse(SIMPLE_MESSAGE)
        assert venue_registry.detect_from_message(msg) is None

    def test_generic_bloomberg_compid_resolves_to_dor_not_fxgo(
        self, venue_registry: VenueRegistry
    ) -> None:
        """A FIXT.1.1 DOR message with a generic 49=BLOOMBERG is detected as
        Bloomberg DOR via protocol markers — even though that CompID alone
        matches Bloomberg FXGO."""
        parser = FixParser(config=ParserConfig(strict_checksum=False))
        msg = parser.parse(BLOOMBERG_DOR_GENERIC_COMPID_EXEC)

        # CompID alone resolves to FXGO:
        fxgo = venue_registry.get_by_sender_id("BLOOMBERG")
        assert fxgo is not None
        assert fxgo.name == "Bloomberg FXGO"

        # Full protocol-aware detection picks DOR:
        detected = venue_registry.detect_from_message(msg)
        assert detected is not None
        assert detected.name == "Bloomberg DOR"

    def test_plain_fxgo_message_still_detected(self, venue_registry: VenueRegistry) -> None:
        """A plain FIX.4.4 Bloomberg FXGO execution is still resolved to
        Bloomberg FXGO — the protocol-aware claims pass must not swallow it."""
        parser = FixParser(config=ParserConfig(strict_checksum=False))
        msg = parser.parse(SPOT_MESSAGE_PIPE)
        detected = venue_registry.detect_from_message(msg)
        assert detected is not None
        assert detected.name == "Bloomberg FXGO"


class TestBloombergDORClaimsMessage:
    """Protocol-aware detection: when does Bloomberg DOR claim a message?"""

    def _msg(self, tag_values: Mapping[int, str]) -> FixMessage:
        return FixMessage(fields=[FixField(tag=t, raw_value=v) for t, v in tag_values.items()])

    def test_claims_generic_bloomberg_compid_over_fixt11(self) -> None:
        handler = BloombergDORHandler()
        msg = self._msg({8: "FIXT.1.1", 35: "8", 49: "BLOOMBERG", 56: "CLIENT"})
        assert handler.claims_message(msg) is True

    def test_claims_on_dor_routing_id_115(self) -> None:
        handler = BloombergDORHandler()
        msg = self._msg({8: "FIX.4.4", 35: "8", 49: "BLOOMBERG", 115: "DOR"})
        assert handler.claims_message(msg) is True

    def test_claims_on_dor_only_msg_type(self) -> None:
        handler = BloombergDORHandler()
        msg = self._msg({8: "FIX.4.4", 35: "AI", 49: "BLOOMBERG"})
        assert handler.claims_message(msg) is True

    def test_claims_on_appl_ver_id(self) -> None:
        handler = BloombergDORHandler()
        msg = self._msg({8: "FIXT.1.1", 35: "S", 49: "BBG", 1128: "9"})
        assert handler.claims_message(msg) is True

    def test_does_not_claim_other_venue_fixt11(self) -> None:
        # A FIXT.1.1 / FIX5.0 message from another venue (no Bloomberg CompID)
        # must NOT be claimed by DOR.
        handler = BloombergDORHandler()
        msg = self._msg({8: "FIXT.1.1", 35: "8", 49: "TR MATCHING", 1128: "9"})
        assert handler.claims_message(msg) is False

    def test_does_not_claim_plain_fxgo_message(self) -> None:
        handler = BloombergDORHandler()
        msg = self._msg({8: "FIX.4.4", 35: "8", 49: "FXGO", 56: "CLIENT"})
        assert handler.claims_message(msg) is False


class TestTradeSummaryGate:
    """The UI renders a trade / quote summary only when ``product_type`` is set;
    administrative messages get a short note instead of a wall of N/A.

    These tests pin the invariant that makes that gate safe and venue-universal:
    across every venue, ``product_type`` is present for economic messages
    (quotes / RFQs / executions / trade captures) and absent only for the known
    administrative message types. So the UI never hides a real trade summary and
    never shows trade metrics for a non-economic message.
    """

    # Fixtures the UI is expected to suppress (administrative / non-economic).
    ADMIN_FIXTURES = frozenset(
        {
            "BLOOMBERG_DOR_SPOT_RFQ_REJECT",  # 35=AG QuoteRequestReject
            "THREE_SIXTY_T_QUOTE_CANCEL",  # 35=Z QuoteCancel
            "THREE_SIXTY_T_SECURITY_DEFINITION",  # 35=d SecurityDefinition
        }
    )

    # Module constants that are not parseable venue messages.
    _NON_MESSAGES = frozenset(
        {
            "SOH",
            "SIMPLE_MESSAGE",
            "INVALID_NO_BEGIN_STRING",
            "INVALID_NO_CHECKSUM",
            "INVALID_WRONG_ORDER",
        }
    )

    def _resolved(self, venue_registry: VenueRegistry) -> dict[str, FixMessage]:
        """Parse every venue fixture the way the UI does (auto-detect venue +
        product-registry fallback) and return ``{name: message}`` for those that
        resolve to a venue handler."""
        import tests.fixtures.sample_messages as samples

        parser = FixParser(config=ParserConfig(strict_checksum=False, strict_body_length=False))
        product_registry = ProductRegistry.default()
        resolved: dict[str, FixMessage] = {}
        for name in dir(samples):
            if not name.isupper() or name in self._NON_MESSAGES:
                continue
            raw = getattr(samples, name)
            if not isinstance(raw, str):
                continue
            message = parser.parse(raw, auto_detect_venue=True)
            handler = venue_registry.get(message.venue) if message.venue else None
            if handler is None:
                continue
            product_handler = product_registry.detect(message)
            if product_handler and not message.product_type:
                message.product_type = product_handler.product_type
            resolved[name] = message
        return resolved

    def test_admin_fixtures_are_suppressed(self, venue_registry: VenueRegistry) -> None:
        """Known administrative messages resolve to a venue but carry no
        product_type, so the UI shows the note rather than a trade summary."""
        resolved = self._resolved(venue_registry)
        for name in self.ADMIN_FIXTURES:
            assert name in resolved, f"{name} did not resolve to a venue"
            assert resolved[name].product_type is None, (
                f"{name} unexpectedly has product_type " f"{resolved[name].product_type!r}"
            )

    def test_economic_fixtures_keep_their_summary(self, venue_registry: VenueRegistry) -> None:
        """Every other venue-resolved fixture has a product_type, so the UI gate
        never wrongly hides an economic message's trade / quote summary."""
        resolved = self._resolved(venue_registry)
        economic = {n: m for n, m in resolved.items() if n not in self.ADMIN_FIXTURES}
        assert economic, "expected at least one economic fixture to resolve"
        for name, message in economic.items():
            assert message.product_type is not None, (
                f"{name} (35={message.msg_type}) has no product_type; the UI "
                "would wrongly suppress its trade summary as non-economic"
            )


class TestSymbolFallback:
    """Symbol resolution when tag 55 is missing or sentinel."""

    def _trade(self, tag_values: Mapping[int, str]) -> ParsedTrade:
        msg = FixMessage(fields=[FixField(tag=t, raw_value=v) for t, v in tag_values.items()])
        return BloombergDORHandler().extract_trade(msg)

    def test_uses_tag_55_when_present(self) -> None:
        trade = self._trade({35: "AE", 55: "USDJPY"})
        assert trade.symbol == "USDJPY"

    def test_falls_back_to_security_id_when_tag_55_missing(self) -> None:
        trade = self._trade({35: "AE", 48: "KU"})
        assert trade.symbol == "KU"

    def test_falls_back_when_tag_55_is_na_sentinel(self) -> None:
        trade = self._trade({35: "AE", 55: "[N/A]", 48: "KU"})
        assert trade.symbol == "KU"

    def test_falls_back_to_security_desc_when_no_security_id(self) -> None:
        trade = self._trade({35: "AE", 55: "[N/A]", 107: "KRW_USD FX Futures"})
        assert trade.symbol == "KRW_USD FX Futures"

    def test_falls_back_to_product_complex_last(self) -> None:
        trade = self._trade({35: "AE", 55: "[N/A]", 1227: "SGX KRW/USD FX FUTURES"})
        assert trade.symbol == "SGX KRW/USD FX FUTURES"

    def test_blank_symbol_treated_as_missing(self) -> None:
        trade = self._trade({35: "AE", 55: "   ", 48: "KU"})
        assert trade.symbol == "KU"
