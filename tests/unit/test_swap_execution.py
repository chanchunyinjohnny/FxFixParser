"""Tests for swap-specific extraction on Execution Reports / Orders.

Covers the path through ``VenueHandler._extract_execution_info`` where a
two-leg structure (SettlDate2 / OrderQty2 / Price2) populates
``ParsedTrade`` swap fields including spot rate, swap points (with pips),
and the near/far leg side semantics derived from the trade currency.
"""

from __future__ import annotations

import pytest

from fxfixparser.core.fx_math import parse_symbol, pip_size, swap_side_actions
from fxfixparser.core.parser import FixParser, ParserConfig
from fxfixparser.venues.smart_trade import SmartTradeHandler


# User-supplied LFX NewOrderSingle swap for USD/CNH. Side=Buy, trade ccy
# = USD (base). Near 6.757113, Far 6.757698 → +0.000585 = +5.85 pips.
LFX_SWAP_ORDER_USD_BASE = (
    "8=FIX.4.4|9=313|35=D|34=886|49=UAT.ATP.RFS.TRD|"
    "52=20260602-03:50:06.994|56=LFX_CORE|11=UDH5600477412687904|"
    "15=USD|38=23232324|40=D|44=6.757113|54=1|55=USD/CNH|59=4|"
    "60=20260602-03:50:06.993|64=20260610|"
    "131=REQ_761193183997988864|192=2323232|193=20260612|"
    "299=5VVGrvqdwhI6|640=6.757698|453=2|448=algoclient|452=5|"
    "448=ATP_SW3|452=2|10=219|"
)

# Same shape but trade currency = CNH (term). Far - Near is positive too,
# but the leg actions must be expressed in CNH.
LFX_SWAP_ORDER_CNH_TERM = (
    "8=FIX.4.4|9=313|35=D|34=886|49=UAT.ATP.RFS.TRD|"
    "52=20260602-03:50:06.994|56=LFX_CORE|11=UDH5600477412687904|"
    "15=CNH|38=23232324|40=D|44=6.757113|54=1|55=USD/CNH|59=4|"
    "60=20260602-03:50:06.993|64=20260610|"
    "131=REQ_761193183997988864|192=2323232|193=20260612|"
    "299=5VVGrvqdwhI6|640=6.757698|10=000|"
)

# JPY pair to verify pip size 0.01.
LFX_SWAP_ORDER_USD_JPY = (
    "8=FIX.4.4|9=300|35=D|34=10|49=UAT.ATP.RFS.TRD|"
    "52=20260101-00:00:00.000|56=LFX_CORE|11=ORD-JPY|"
    "15=USD|38=1000000|40=D|44=148.50|54=2|55=USD/JPY|59=4|"
    "60=20260101-00:00:00.000|64=20260103|"
    "192=1000000|193=20260201|640=148.75|10=000|"
)


def _parse(msg: str):
    parser = FixParser(config=ParserConfig(strict_checksum=False, strict_body_length=False))
    return parser.parse(msg, auto_detect_venue=True)


class TestFxMath:
    """Pure helpers in ``fxfixparser.core.fx_math``."""

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("USD/CNH", ("USD", "CNH")),
            ("usd/jpy", ("USD", "JPY")),
            ("EURUSD", ("EUR", "USD")),
            ("", (None, None)),
            (None, (None, None)),
            ("USD", (None, None)),  # 3-char is ambiguous, treat as unknown
        ],
    )
    def test_parse_symbol(self, raw, expected):
        assert parse_symbol(raw) == expected

    @pytest.mark.parametrize(
        "symbol, expected",
        [
            ("USD/CNH", 0.0001),
            ("EUR/USD", 0.0001),
            ("USD/JPY", 0.01),
            ("EURJPY", 0.01),
            (None, 0.0001),
        ],
    )
    def test_pip_size(self, symbol, expected):
        assert pip_size(symbol) == expected

    def test_swap_side_buy_base(self):
        # Side=Buy, trade ccy = base (USD on USD/CNH)
        # → Near: Sell USD, Far: Buy USD
        near, far = swap_side_actions("1", "USD", "USD", "CNH")
        assert near == "Sell USD"
        assert far == "Buy USD"

    def test_swap_side_buy_term(self):
        # Side=Buy, trade ccy = term (CNH on USD/CNH)
        # → Near: Sell CNH (= Buy USD), Far: Buy CNH (= Sell USD)
        near, far = swap_side_actions("1", "CNH", "USD", "CNH")
        assert near == "Sell CNH (Buy USD)"
        assert far == "Buy CNH (Sell USD)"

    def test_swap_side_sell_base(self):
        near, far = swap_side_actions("2", "USD", "USD", "CNH")
        assert near == "Buy USD"
        assert far == "Sell USD"

    def test_swap_side_sell_term(self):
        near, far = swap_side_actions("2", "CNH", "USD", "CNH")
        assert near == "Buy CNH (Sell USD)"
        assert far == "Sell CNH (Buy USD)"

    def test_swap_side_unknown_inputs(self):
        # Missing inputs → no actions
        assert swap_side_actions(None, "USD", "USD", "CNH") == (None, None)
        assert swap_side_actions("1", None, "USD", "CNH") == (None, None)
        # Unsupported side code
        assert swap_side_actions("9", "USD", "USD", "CNH") == (None, None)


class TestSwapExecutionExtraction:
    """End-to-end extraction through Smart Trade venue handler."""

    def test_buy_base_trade_currency(self):
        message = _parse(LFX_SWAP_ORDER_USD_BASE)
        trade = SmartTradeHandler().extract_trade(message)

        assert trade.is_swap is True
        assert trade.symbol == "USD/CNH"
        assert trade.base_currency == "USD"
        assert trade.term_currency == "CNH"
        assert trade.trade_currency == "USD"
        assert trade.side == "Buy"

        # Legs
        assert trade.settlement_date == "20260610"
        assert trade.far_settlement_date == "20260612"
        assert trade.near_quantity == 23232324.0
        assert trade.far_quantity == 2323232.0
        assert trade.near_leg_price == pytest.approx(6.757113)
        assert trade.far_leg_price == pytest.approx(6.757698)

        # Spot rate falls back to near leg price (no tag 194)
        assert trade.spot_rate == pytest.approx(6.757113)

        # Swap points = far - near = 0.000585, 5.85 pips for USD/CNH
        assert trade.swap_points == pytest.approx(0.000585, abs=1e-9)
        assert trade.pip_size == 0.0001
        assert trade.swap_points_pips == pytest.approx(5.85, abs=1e-6)

        # Side semantics — user's stated expectation for this message
        assert trade.near_leg_action == "Sell USD"
        assert trade.far_leg_action == "Buy USD"

    def test_buy_term_trade_currency(self):
        message = _parse(LFX_SWAP_ORDER_CNH_TERM)
        trade = SmartTradeHandler().extract_trade(message)

        assert trade.is_swap is True
        assert trade.trade_currency == "CNH"
        # Side actions now stated in term currency with base equivalents
        assert trade.near_leg_action == "Sell CNH (Buy USD)"
        assert trade.far_leg_action == "Buy CNH (Sell USD)"

    def test_jpy_pip_size_and_sell_side(self):
        message = _parse(LFX_SWAP_ORDER_USD_JPY)
        trade = SmartTradeHandler().extract_trade(message)

        assert trade.is_swap is True
        assert trade.pip_size == 0.01
        # 148.75 - 148.50 = 0.25 raw → 25 pips at 0.01 pip size
        assert trade.swap_points == pytest.approx(0.25, abs=1e-9)
        assert trade.swap_points_pips == pytest.approx(25.0, abs=1e-6)
        # Side=Sell, trade ccy=USD (base)
        assert trade.near_leg_action == "Buy USD"
        assert trade.far_leg_action == "Sell USD"

    def test_explicit_spot_rate_tag_194(self):
        # SWAP_MESSAGE fixture: 194=148.50 (LastSpotRate). Per LFX spec
        # page 45, 195 LastForwardPoints is the *near-leg* fwd pts, not
        # swap points — so without 640 (Price2) or 641 the fixture cannot
        # produce swap points. Verify spot is sourced from 194, not the
        # near leg fallback.
        from tests.fixtures.sample_messages import SWAP_MESSAGE

        message = _parse(SWAP_MESSAGE)
        trade = SmartTradeHandler().extract_trade(message)

        assert trade.is_swap is True
        assert trade.spot_rate == pytest.approx(148.50)
        # Near and far prices are both 148.50 (31=LastPx, no Price2/640) →
        # no Price2 means we fall back to (641 - 195). Fixture lacks 641,
        # so swap_points is None.
        assert trade.swap_points is None
        assert trade.pip_size == 0.01  # USD/JPY

    def test_swap_points_from_lfx_individual_forward_points(self):
        # Construct an execution-report-shaped swap where Price2 is not
        # given but both LastForwardPoints (195, near) and
        # LastForwardPoints2 (641, far) are.
        msg = (
            "8=FIX.4.4|9=200|35=8|49=LFX_CORE|56=CLIENT|34=1|"
            "52=20240115-10:30:00|37=O1|17=E1|150=F|39=2|55=USD/JPY|"
            "54=1|32=1000000|31=148.50|15=USD|64=20240117|193=20240415|"
            "192=1000000|194=148.50|195=0.10|641=0.60|"
            "60=20240115-10:30:00|10=000|"
        )
        message = _parse(msg)
        trade = SmartTradeHandler().extract_trade(message)
        assert trade.is_swap is True
        assert trade.spot_rate == pytest.approx(148.50)
        # 641 - 195 = 0.50 → 50 pips at 0.01 pip size
        assert trade.swap_points == pytest.approx(0.50, abs=1e-9)
        assert trade.swap_points_pips == pytest.approx(50.0, abs=1e-6)

    def test_to_dict_includes_swap_fields(self):
        message = _parse(LFX_SWAP_ORDER_USD_BASE)
        trade = SmartTradeHandler().extract_trade(message)
        d = trade.to_dict()

        for key in (
            "near_leg_price",
            "far_leg_price",
            "near_quantity",
            "far_quantity",
            "spot_rate",
            "swap_points",
            "swap_points_pips",
            "pip_size",
            "near_leg_action",
            "far_leg_action",
            "base_currency",
            "term_currency",
            "trade_currency",
        ):
            assert key in d, f"Missing swap field: {key}"
