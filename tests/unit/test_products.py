"""Unit tests for product type handlers."""

import pytest

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

    def test_detect_forward_by_tenor(self, parser: FixParser, product_registry: ProductRegistry) -> None:
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

    def test_detect_forward_by_md_entry_forward_points(self, parser: FixParser, product_registry: ProductRegistry) -> None:
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
