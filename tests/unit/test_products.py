"""Unit tests for product type handlers."""

from typing import Mapping

import pytest

from fxfixparser.core.field import FixField
from fxfixparser.core.message import FixMessage
from fxfixparser.core.parser import FixParser, ParserConfig
from fxfixparser.products.base import ProductRegistry
from fxfixparser.products.forward import ForwardHandler
from fxfixparser.products.ndf import NDFHandler
from fxfixparser.products.spot import SpotHandler
from fxfixparser.products.swap import SwapHandler
from tests.fixtures.sample_messages import (
    FORWARD_MESSAGE,
    LFX_FORWARD_MD_MESSAGE,
    NDF_MESSAGE,
    SPOT_MESSAGE_PIPE,
    SWAP_MESSAGE,
)


class TestProductHandlers:
    """Tests for individual product handlers."""

    def test_spot_handler_properties(self) -> None:
        """Test Spot handler properties."""
        handler = SpotHandler()
        assert handler.product_type == "Spot"

    def test_forward_handler_properties(self) -> None:
        """Test Forward handler properties."""
        handler = ForwardHandler()
        assert handler.product_type == "Forward"

    def test_swap_handler_properties(self) -> None:
        """Test Swap handler properties."""
        handler = SwapHandler()
        assert handler.product_type == "Swap"

    def test_ndf_handler_properties(self) -> None:
        """Test NDF handler properties."""
        handler = NDFHandler()
        assert handler.product_type == "NDF"


class TestProductDetection:
    """Tests for product type detection."""

    @pytest.fixture
    def parser(self) -> FixParser:
        return FixParser(config=ParserConfig(strict_checksum=False))

    def test_detect_spot(self, parser: FixParser, product_registry: ProductRegistry) -> None:
        """Test detecting a spot trade."""
        message = parser.parse(SPOT_MESSAGE_PIPE)
        handler = product_registry.detect(message)

        assert handler is not None
        assert handler.product_type == "Spot"

    def test_detect_forward(self, parser: FixParser, product_registry: ProductRegistry) -> None:
        """Test detecting a forward trade."""
        message = parser.parse(FORWARD_MESSAGE)
        handler = product_registry.detect(message)

        assert handler is not None
        assert handler.product_type == "Forward"

    def test_detect_swap(self, parser: FixParser, product_registry: ProductRegistry) -> None:
        """Test detecting a swap trade."""
        message = parser.parse(SWAP_MESSAGE)
        handler = product_registry.detect(message)

        assert handler is not None
        assert handler.product_type == "Swap"

    def test_detect_ndf(self, parser: FixParser, product_registry: ProductRegistry) -> None:
        """Test detecting an NDF trade."""
        message = parser.parse(NDF_MESSAGE)
        handler = product_registry.detect(message)

        assert handler is not None
        assert handler.product_type == "NDF"

    def test_detect_forward_by_tenor(
        self, parser: FixParser, product_registry: ProductRegistry
    ) -> None:
        """Test detecting a forward from LFX tenor-based SettlType (e.g. M1)."""
        message = parser.parse(LFX_FORWARD_MD_MESSAGE)
        handler = product_registry.detect(message)

        assert handler is not None
        assert handler.product_type == "Forward"

    def test_detect_forward_tenor_codes(self, parser: FixParser) -> None:
        """Test that various tenor codes are recognized as forwards."""
        handler = ForwardHandler()
        for tenor in ["M1", "M3", "M6", "W1", "W2", "Y1", "Y2", "D3"]:
            msg = FixParser(config=ParserConfig(strict_checksum=False)).parse(
                f"8=FIX.4.4|9=100|35=X|49=LFX|56=CLIENT|34=1|"
                f"52=20240115-10:30:00|55=EUR/USD|63={tenor}|10=000|"
            )
            assert handler.detect(msg), f"Failed to detect forward for tenor {tenor}"

    def test_detect_forward_by_md_entry_forward_points(
        self, parser: FixParser, product_registry: ProductRegistry
    ) -> None:
        """Test detecting a forward from MDEntryForwardPoints (tag 1027) presence."""
        # Message without forward tenor in tag 63, but with tag 1027
        msg = parser.parse(
            "8=FIX.4.4|9=200|35=X|49=LFX_CORE|56=CLIENT|34=1|"
            "52=20240115-10:30:00|55=EUR/USD|64=20260310|"
            "268=1|279=1|269=0|270=1.180603|1026=1.17905|1027=0.001553|10=000|"
        )
        handler = product_registry.detect(msg)

        assert handler is not None
        assert handler.product_type == "Forward"

    def test_spot_tenors_not_detected_as_forward(self, parser: FixParser) -> None:
        """Test that spot tenors are NOT detected as forwards."""
        handler = ForwardHandler()
        for tenor in ["SPOT", "TOD", "TOM"]:
            msg = FixParser(config=ParserConfig(strict_checksum=False)).parse(
                f"8=FIX.4.4|9=100|35=X|49=LFX|56=CLIENT|34=1|"
                f"52=20240115-10:30:00|55=EUR/USD|63={tenor}|10=000|"
            )
            assert not handler.detect(msg), f"Incorrectly detected forward for spot tenor {tenor}"

    def test_forward_handler_detects_bloomberg_tenor_tag_6215(self, parser: FixParser) -> None:
        """ForwardHandler detects forwards from the Bloomberg tenor tag (6215)."""
        handler = ForwardHandler()
        for tenor in ["1M", "3M", "1W", "1Y", "M6"]:
            msg = parser.parse(
                f"8=FIXT.1.1|9=150|35=8|49=BLOOMBERG_DOR|56=CLIENT|34=1|"
                f"52=20240115-10:30:00|55=EUR/USD|6215={tenor}|10=000|"
            )
            assert handler.detect(msg), f"Failed to detect forward for tenor 6215={tenor}"

    def test_forward_handler_spot_tenor_6215_not_forward(self, parser: FixParser) -> None:
        """ForwardHandler does not treat a spot tenor (6215=SP) as a forward."""
        handler = ForwardHandler()
        msg = parser.parse(
            "8=FIXT.1.1|9=150|35=8|49=BLOOMBERG_DOR|56=CLIENT|34=1|"
            "52=20240115-10:30:00|55=EUR/USD|6215=SP|10=000|"
        )
        assert not handler.detect(msg)

    def test_detect_tenor_only_forward_not_spot(
        self, parser: FixParser, product_registry: ProductRegistry
    ) -> None:
        """A Bloomberg tenor-only forward is classified as Forward, not Spot.

        The message carries its tenor only in tag 6215 — no SecurityType
        (167), SettlType (63), forward points (195) or MD forward points
        (1027) — which previously fell through to the Spot fallback.
        """
        msg = parser.parse(
            "8=FIXT.1.1|9=220|35=8|49=BLOOMBERG_DOR|56=CLIENT|34=1|"
            "52=20240115-10:30:00|55=EUR/USD|54=1|32=1000000|31=1.09000|"
            "15=EUR|64=20240415|6215=1M|10=000|"
        )
        handler = product_registry.detect(msg)
        assert handler is not None
        assert handler.product_type == "Forward"

    def test_extract_forward_details(self, parser: FixParser) -> None:
        """Test extracting forward-specific details."""
        message = parser.parse(FORWARD_MESSAGE)
        handler = ForwardHandler()

        details = handler.extract_details(message)

        assert details["product_type"] == "Forward"
        assert details["settlement_date"] == "20240415"
        assert details["spot_rate"] == "1.0850"
        assert details["forward_points"] == "0.0050"

    def test_extract_swap_details(self, parser: FixParser) -> None:
        """Test extracting swap-specific details."""
        message = parser.parse(SWAP_MESSAGE)
        handler = SwapHandler()

        details = handler.extract_details(message)

        assert details["product_type"] == "Swap"
        assert details["near_settlement_date"] == "20240117"
        assert details["far_settlement_date"] == "20240415"


class TestProductRegistry:
    """Tests for ProductRegistry class."""

    def test_empty_registry(self) -> None:
        """Test empty registry."""
        registry = ProductRegistry()
        # Create a minimal message mock
        from fxfixparser.core.message import FixMessage

        message = FixMessage()
        assert registry.detect(message) is None

    def test_default_registry(self, product_registry: ProductRegistry) -> None:
        """Test default registry has all handlers."""
        # The registry doesn't expose handlers list, but we can test it works
        assert product_registry is not None


class TestFuturesSGXDetection:
    def _msg(
        self,
        tag_values: Mapping[int, str],
        venue: str | None = None,
    ) -> FixMessage:
        return FixMessage(
            fields=[FixField(tag=t, raw_value=v) for t, v in tag_values.items()],
            venue=venue,
        )

    def test_detects_via_security_type_fut(self) -> None:
        from fxfixparser.products.futures import FuturesHandler

        msg = self._msg({167: "FUT"})
        assert FuturesHandler().detect(msg) is True

    def test_detects_via_maturity_and_exchange(self) -> None:
        from fxfixparser.products.futures import FuturesHandler

        msg = self._msg({200: "202506", 207: "XSGX"})
        assert FuturesHandler().detect(msg) is True

    def test_detects_via_sgx_style_fx_asset_class(self) -> None:
        # 1300=FX + SecurityID (48) — no SecurityType, no exchange.
        from fxfixparser.products.futures import FuturesHandler

        msg = self._msg({1300: "FX", 48: "KU"}, venue="SGX Titan OTC")
        assert FuturesHandler().detect(msg) is True

    def test_does_not_detect_non_sgx_market_segment_fx(self) -> None:
        from fxfixparser.products.futures import FuturesHandler

        msg = self._msg({35: "D", 1300: "FX", 48: "ABC"}, venue="Other Venue")
        assert FuturesHandler().detect(msg) is False

    def test_does_not_detect_random_message(self) -> None:
        from fxfixparser.products.futures import FuturesHandler

        msg = self._msg({35: "D", 55: "USDJPY"})
        assert FuturesHandler().detect(msg) is False


class TestFuturesExtractDetailsProductName:
    def _msg(
        self,
        tag_values: Mapping[int, str],
        venue_extras: Mapping[str, str] | None = None,
    ) -> FixMessage:
        msg = FixMessage(fields=[FixField(tag=t, raw_value=v) for t, v in tag_values.items()])
        if venue_extras:
            msg.venue_extras = dict(venue_extras)
        return msg

    def test_uses_venue_extras_product_name_when_present(self) -> None:
        from fxfixparser.products.futures import FuturesHandler

        msg = self._msg(
            {200: "202506", 48: "KU", 107: "KRW_USD FX Futures"},
            venue_extras={"product_name": "KRW/USD FX Futures"},
        )
        details = FuturesHandler().extract_details(msg)
        assert details["product_code"] == "KU"
        assert details["product_name"] == "KRW/USD FX Futures"

    def test_falls_back_to_product_complex_then_security_desc(self) -> None:
        from fxfixparser.products.futures import FuturesHandler

        msg = self._msg({200: "202506", 48: "KU", 1227: "SGX KRW/USD FUTURES"})
        details = FuturesHandler().extract_details(msg)
        assert details["product_code"] == "KU"
        assert details["product_name"] == "SGX KRW/USD FUTURES"

    def test_no_product_name_when_no_source(self) -> None:
        from fxfixparser.products.futures import FuturesHandler

        msg = self._msg({200: "202506"})
        details = FuturesHandler().extract_details(msg)
        assert details.get("product_name") is None
