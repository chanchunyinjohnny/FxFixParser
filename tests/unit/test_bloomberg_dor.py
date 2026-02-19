"""Unit tests for Bloomberg DOR venue handler."""

import pytest

from fxfixparser.core.parser import FixParser, ParserConfig
from fxfixparser.venues.bloomberg_dor import BloombergDORHandler
from tests.fixtures.sample_messages import (
    BLOOMBERG_DOR_SPOT_EXEC,
    BLOOMBERG_DOR_FORWARD_EXEC,
    BLOOMBERG_DOR_SWAP_EXEC,
    BLOOMBERG_DOR_ALGO_EXEC,
    BLOOMBERG_DOR_SPOT_RFQ,
    BLOOMBERG_DOR_SPOT_QUOTE,
)


class TestBloombergDORBasic:
    """Tests for Bloomberg DOR handler basic properties."""

    def test_handler_name(self) -> None:
        """Handler name should be 'Bloomberg DOR'."""
        handler = BloombergDORHandler()
        assert handler.name == "Bloomberg DOR"

    def test_sender_comp_ids(self) -> None:
        """Handler should include key Bloomberg DOR sender IDs."""
        handler = BloombergDORHandler()
        ids = handler.sender_comp_ids

        assert "BLOOMBERG_DOR" in ids
        assert "BBGDOR" in ids
        assert "DOR" in ids
        assert "FXOM" in ids
        assert "ORP" in ids

    def test_matches_sender(self) -> None:
        """matches_sender should be case-insensitive and reject non-DOR IDs."""
        handler = BloombergDORHandler()

        # Positive cases — exact and case-insensitive
        assert handler.matches_sender("BLOOMBERG_DOR")
        assert handler.matches_sender("bloomberg_dor")
        assert handler.matches_sender("DOR")
        assert handler.matches_sender("dor")
        assert handler.matches_sender("FXOM")
        assert handler.matches_sender("fxom")
        assert handler.matches_sender("ORP")
        assert handler.matches_sender("orp")
        assert handler.matches_sender("BBGDOR")
        assert handler.matches_sender("bbgdor")

        # Negative cases
        assert not handler.matches_sender("FXGO")
        assert not handler.matches_sender("SMARTTRADE")
        assert not handler.matches_sender("360T")
        assert not handler.matches_sender("")
        assert not handler.matches_sender(None)


class TestBloombergDORCustomTags:
    """Tests for Bloomberg DOR custom tag definitions."""

    def test_custom_tags_returns_definitions(self) -> None:
        """Handler should return custom tag definitions."""
        handler = BloombergDORHandler()
        tags = handler.custom_tags
        assert len(tags) > 0

    def test_custom_tags_include_bloomberg_specific(self) -> None:
        """Bloomberg-specific tags should be present."""
        handler = BloombergDORHandler()
        tags_by_number = {t.tag: t for t in handler.custom_tags}

        # Tag 22913 — LastMktSpotRate
        assert 22913 in tags_by_number
        assert tags_by_number[22913].name == "LastMktSpotRate"

        # Tag 22858 — AlgoStrategyID
        assert 22858 in tags_by_number
        assert tags_by_number[22858].name == "AlgoStrategyID"

        # Tag 6215 — Tenor
        assert 6215 in tags_by_number
        assert tags_by_number[6215].name == "Tenor"

    def test_custom_tags_have_descriptions(self) -> None:
        """Custom tags should have meaningful descriptions."""
        handler = BloombergDORHandler()
        tags_by_number = {t.tag: t for t in handler.custom_tags}

        tag_22913 = tags_by_number[22913]
        assert "spot rate" in tag_22913.description.lower()

    def test_custom_tags_have_enumerations(self) -> None:
        """Tags with valid_values should have correct enumerations."""
        handler = BloombergDORHandler()
        tags_by_number = {t.tag: t for t in handler.custom_tags}

        # ManualTicket (22923) has valid_values
        assert 22923 in tags_by_number
        manual_ticket = tags_by_number[22923]
        assert "0" in manual_ticket.valid_values
        assert "1" in manual_ticket.valid_values

        # OffshoreIndicator (2795) has valid_values
        assert 2795 in tags_by_number
        offshore = tags_by_number[2795]
        assert "0" in offshore.valid_values
        assert "1" in offshore.valid_values


class TestBloombergDORTradeExtraction:
    """Tests for Bloomberg DOR trade extraction from parsed messages."""

    @pytest.fixture
    def handler(self):
        return BloombergDORHandler()

    @pytest.fixture
    def parser(self):
        return FixParser(config=ParserConfig(strict_checksum=False))

    def test_extract_spot_execution(self, handler, parser):
        """Spot execution should extract symbol, side, qty, price, currency, settlement date."""
        message = parser.parse(BLOOMBERG_DOR_SPOT_EXEC, venue=handler)
        trade = handler.extract_trade(message)
        assert trade.venue == "Bloomberg DOR"
        assert trade.symbol == "EUR/USD"
        assert trade.side == "Buy"
        assert trade.quantity == 1000000.0
        assert trade.price == 1.08500
        assert trade.currency == "EUR"
        assert trade.settlement_date == "20240117"

    def test_extract_forward_execution(self, handler, parser):
        """Forward execution should extract symbol, qty, price, settlement date."""
        message = parser.parse(BLOOMBERG_DOR_FORWARD_EXEC, venue=handler)
        trade = handler.extract_trade(message)
        assert trade.venue == "Bloomberg DOR"
        assert trade.symbol == "EUR/USD"
        assert trade.quantity == 5000000.0
        assert trade.price == 1.09000
        assert trade.settlement_date == "20240715"

    def test_extract_swap_execution(self, handler, parser):
        """Swap execution should extract symbol, qty, currency."""
        message = parser.parse(BLOOMBERG_DOR_SWAP_EXEC, venue=handler)
        trade = handler.extract_trade(message)
        assert trade.venue == "Bloomberg DOR"
        assert trade.symbol == "EUR/USD"
        assert trade.quantity == 10000000.0
        assert trade.currency == "EUR"

    def test_extract_algo_execution(self, handler, parser):
        """Algo execution should extract symbol, qty, price, currency."""
        message = parser.parse(BLOOMBERG_DOR_ALGO_EXEC, venue=handler)
        trade = handler.extract_trade(message)
        assert trade.venue == "Bloomberg DOR"
        assert trade.symbol == "EUR/USD"
        assert trade.quantity == 2000000.0
        assert trade.price == 1.08520
        assert trade.currency == "EUR"

    def test_extract_spot_quote(self, handler, parser):
        """Spot quote should extract symbol, bid/offer prices."""
        message = parser.parse(BLOOMBERG_DOR_SPOT_QUOTE, venue=handler)
        trade = handler.extract_trade(message)
        assert trade.venue == "Bloomberg DOR"
        assert trade.symbol == "EUR/USD"
        assert trade.bid_price == 1.08490
        assert trade.offer_price == 1.08510

    def test_extract_spot_rfq(self, handler, parser):
        """Spot RFQ should extract symbol and quantity."""
        message = parser.parse(BLOOMBERG_DOR_SPOT_RFQ, venue=handler)
        trade = handler.extract_trade(message)
        assert trade.venue == "Bloomberg DOR"
        assert trade.symbol == "EUR/USD"
        assert trade.quantity == 1000000.0
