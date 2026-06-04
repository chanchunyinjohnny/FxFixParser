"""Integration tests for full FIX message parsing workflow."""

import pytest

from fxfixparser.core.parser import FixParser, ParserConfig
from fxfixparser.products.base import ProductRegistry
from fxfixparser.venues.lseg_fx_matching import LSEGFXMatchingHandler
from fxfixparser.venues.registry import VenueRegistry
from fxfixparser.venues.sgx_titan_otc import SGXTitanOTCHandler
from tests.fixtures.sample_messages import (
    FORWARD_MESSAGE,
    LSEG_FXM_SWAP_EXECUTION,
    NDF_MESSAGE,
    SGX_TITAN_OTC_KU_TRADE_CAPTURE,
    SGX_TITAN_OTC_KUTM_FLEXC_TRADE_CAPTURE,
    SGX_TITAN_OTC_UC_EXEC_REPORT,
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

        assert message.venue == "Smart Trade (LiquidityFX)"
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

    def test_forward_trade_extraction(
        self,
        parser: FixParser,
        venue_registry: VenueRegistry,
    ) -> None:
        """Test trade extraction for forward trade (360T)."""
        message = parser.parse(FORWARD_MESSAGE)
        venue_handler = venue_registry.get_by_sender_id(message.sender_comp_id)
        assert venue_handler is not None

        trade = venue_handler.extract_trade(message)
        assert trade.symbol == "EUR/USD"
        assert trade.side == "Buy"
        assert trade.quantity == 5000000.0
        assert trade.price == 1.0900
        assert trade.currency == "EUR"
        assert trade.venue == "360T"
        assert trade.settlement_date == "20240415"

    def test_swap_trade_extraction(
        self,
        parser: FixParser,
        venue_registry: VenueRegistry,
    ) -> None:
        """Test trade extraction for swap trade (Smart Trade)."""
        message = parser.parse(SWAP_MESSAGE)
        venue_handler = venue_registry.get_by_sender_id(message.sender_comp_id)
        assert venue_handler is not None

        trade = venue_handler.extract_trade(message)
        assert trade.symbol == "USD/JPY"
        assert trade.side == "Buy"
        assert trade.quantity == 10000000.0
        assert trade.price == 148.50
        assert trade.currency == "USD"
        assert trade.venue == "Smart Trade (LiquidityFX)"
        assert trade.settlement_date == "20240117"

    def test_ndf_trade_extraction(
        self,
        parser: FixParser,
        venue_registry: VenueRegistry,
    ) -> None:
        """Test trade extraction for NDF trade (FXGO)."""
        message = parser.parse(NDF_MESSAGE)
        venue_handler = venue_registry.get_by_sender_id(message.sender_comp_id)
        assert venue_handler is not None

        trade = venue_handler.extract_trade(message)
        assert trade.symbol == "USD/KRW"
        assert trade.side == "Buy"
        assert trade.quantity == 5000000.0
        assert trade.price == 1320.50
        assert trade.currency == "USD"
        assert trade.venue == "FXGO"


class TestSGXFXFuturesRoundTrip:
    """Round-trip integration tests for SGX Titan OTC FX futures messages."""

    @pytest.fixture
    def parser(self) -> FixParser:
        return FixParser(config=ParserConfig(strict_checksum=False))

    @pytest.fixture
    def product_registry(self) -> ProductRegistry:
        return ProductRegistry.default()

    def test_ku_trade_capture_report_round_trip(
        self, parser: FixParser, product_registry: ProductRegistry
    ) -> None:
        msg = parser.parse(SGX_TITAN_OTC_KU_TRADE_CAPTURE, auto_detect_venue=True)

        assert msg.venue == "SGX Titan OTC"
        assert msg.venue_extras.get("product_name") == "KRW/USD FX Futures"

        trade = SGXTitanOTCHandler().extract_trade(msg)
        assert trade.symbol == "KU"

        product = product_registry.detect(msg)
        assert product is not None
        assert product.product_type == "Futures"
        details = product.extract_details(msg)
        assert details["product_code"] == "KU"
        assert details["product_name"] == "KRW/USD FX Futures"

    def test_kutm_flexc_round_trip(
        self, parser: FixParser, product_registry: ProductRegistry
    ) -> None:
        msg = parser.parse(
            SGX_TITAN_OTC_KUTM_FLEXC_TRADE_CAPTURE,
            auto_detect_venue=True,
        )
        assert msg.venue == "SGX Titan OTC"

        product = product_registry.detect(msg)
        assert product is not None
        details = product.extract_details(msg)
        assert details["product_code"] == "KUTM"
        assert details["product_name"] == "KRW/USD FlexC FX Futures"

    def test_uc_exec_report_round_trip(
        self, parser: FixParser, product_registry: ProductRegistry
    ) -> None:
        msg = parser.parse(SGX_TITAN_OTC_UC_EXEC_REPORT, auto_detect_venue=True)
        assert msg.venue == "SGX Titan OTC"

        product = product_registry.detect(msg)
        assert product is not None
        details = product.extract_details(msg)
        assert details["product_code"] == "UC"
        assert details["product_name"] == "USD/CNH FX Futures"


class TestLSEGFXMatchingRoundTrip:
    """End-to-end parse of an LSEG FX Matching (MAPI) swap execution."""

    @pytest.fixture
    def parser(self) -> FixParser:
        return FixParser(config=ParserConfig(strict_checksum=False, strict_body_length=False))

    @pytest.fixture
    def product_registry(self) -> ProductRegistry:
        return ProductRegistry.default()

    def test_swap_execution_round_trip(
        self, parser: FixParser, product_registry: ProductRegistry
    ) -> None:
        msg = parser.parse(LSEG_FXM_SWAP_EXECUTION, auto_detect_venue=True)

        # Venue auto-detected from TargetCompID(56)="TR MATCHING".
        assert msg.venue == "LSEG FX Matching"
        # FIX 5.0 SP2 standard tags decode via the auto-loaded spec (1128=9).
        assert msg.get_field(167).value_description == "FX Forward Swap (Near/Far two-leg)"

        product = product_registry.detect(msg)
        assert product is not None
        assert product.product_type == "Swap"

        trade = LSEGFXMatchingHandler().extract_trade(msg)
        assert trade.is_swap is True
        assert trade.symbol == "EUR/USD"
        assert trade.settlement_date == "20260606"
        assert trade.far_settlement_date == "20260908"
        assert trade.swap_points == pytest.approx(0.001)
        assert trade.spot_rate == pytest.approx(1.0838)
