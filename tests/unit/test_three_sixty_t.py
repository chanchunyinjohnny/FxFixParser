"""Unit tests for the 360T RFS Market Taker venue handler."""

import pytest

from fxfixparser.core.parser import FixParser, ParserConfig
from fxfixparser.venues.three_sixty_t import ThreeSixtyTHandler
from tests.fixtures.sample_messages import (
    THREE_SIXTY_T_BLOCK_TRADE,
    THREE_SIXTY_T_FORWARD_EXEC,
    THREE_SIXTY_T_NDF_EXEC,
    THREE_SIXTY_T_NDS_EXEC,
    THREE_SIXTY_T_SECURITY_DEFINITION,
    THREE_SIXTY_T_SPOT_QUOTE_REQUEST,
    THREE_SIXTY_T_SWAP_EXEC,
    THREE_SIXTY_T_SWAP_QUOTE,
    THREE_SIXTY_T_SWAP_QUOTE_REQUEST,
    THREE_SIXTY_T_TIME_OPTION_EXEC,
)


def _parse(raw: str):
    parser = FixParser(config=ParserConfig(strict_checksum=False))
    return parser.parse(raw, venue="360T")


class TestThreeSixtyTHandlerProperties:
    def test_name_and_senders(self) -> None:
        handler = ThreeSixtyTHandler()
        assert handler.name == "360T"
        assert "360T" in handler.sender_comp_ids
        assert handler.matches_sender("360TGTX")
        assert not handler.matches_sender("FXGO")


class TestThreeSixtyTCustomTags:
    def test_product_type_decodes(self) -> None:
        msg = _parse(THREE_SIXTY_T_SPOT_QUOTE_REQUEST)
        f = msg.get_field(7071)
        assert f is not None
        assert f.name == "ProductType"
        assert "Spot" in (f.value_description or "")

    def test_ref_spot_date_and_far_price_tags(self) -> None:
        msg = _parse(THREE_SIXTY_T_SWAP_QUOTE)
        assert msg.get_field(7070).name == "RefSpotDate"
        assert msg.get_field(6050).name == "BidPx2"
        assert msg.get_field(6051).name == "OfferPx2"

    def test_far_exec_and_option_tags(self) -> None:
        assert _parse(THREE_SIXTY_T_SWAP_EXEC).get_field(6160).name == "LastPx2"
        opt = _parse(THREE_SIXTY_T_TIME_OPTION_EXEC)
        assert opt.get_field(9515).name == "OptionDate"
        assert opt.get_field(9514).name == "OptionPeriod"

    def test_nds_far_fixing_tag(self) -> None:
        assert _parse(THREE_SIXTY_T_NDS_EXEC).get_field(7541).name == "MaturityDate2"


class TestThreeSixtyTEnumExtensions:
    def test_quote_type_tradeable(self) -> None:
        f = _parse(THREE_SIXTY_T_SPOT_QUOTE_REQUEST).get_field(537)
        assert "Tradeable" in (f.value_description or "")

    def test_execution_venue_type_mtf(self) -> None:
        f = _parse(THREE_SIXTY_T_SPOT_QUOTE_REQUEST).get_field(7611)
        assert "MTF" in (f.value_description or "")

    def test_side_as_defined_on_block(self) -> None:
        f = _parse(THREE_SIXTY_T_BLOCK_TRADE).get_field(54)
        assert "As Defined" in (f.value_description or "")

    def test_quote_cancel_type(self) -> None:
        from tests.fixtures.sample_messages import THREE_SIXTY_T_QUOTE_CANCEL

        f = _parse(THREE_SIXTY_T_QUOTE_CANCEL).get_field(298)
        assert "request" in (f.value_description or "").lower()


class TestThreeSixtyTGroups:
    def test_security_definition_underlyings_grouped(self) -> None:
        msg = _parse(THREE_SIXTY_T_SECURITY_DEFINITION)
        groups = [sf.group for sf in msg.get_structured_fields() if sf.is_group]
        underlyings = [g for g in groups if g.count_field.tag == 711]
        assert len(underlyings) == 1
        assert underlyings[0].count == 3
        assert len(underlyings[0].entries) == 3

    def test_block_trade_legs_grouped(self) -> None:
        msg = _parse(THREE_SIXTY_T_BLOCK_TRADE)
        groups = [sf.group for sf in msg.get_structured_fields() if sf.is_group]
        legs = [g for g in groups if g.count_field.tag == 555]
        assert len(legs) == 1
        assert len(legs[0].entries) == 2

    def test_block_legs_with_one_alloc_each_group_correctly(self) -> None:
        # Each leg carries a single NoLegAllocs(670=1) entry; the flattened
        # 671/673 must not phantom-split a leg into extra entries.
        raw = (
            "8=FIX.4.4|9=0|35=AB|49=CLIENT|56=360T|34=1|52=20240115-10:36:00|"
            "1=GROUPE|11=BT-2|15=USD|38=11000|40=D|54=B|55=USD/BRL|"
            "60=20240115-10:36:00|64=20240117|117=Q|7071=FX-BT|555=2|"
            "600=USD/BRL|624=1|687=5000|670=1|671=GROUPE|673=5000|588=20240117|"
            "566=5.19540|654=L1|"
            "600=USD/BRL|624=1|687=6000|670=1|671=GROUPE|673=6000|588=20240120|"
            "566=5.21940|654=L2|"
            "10=000|"
        )
        msg = _parse(raw)
        legs = [
            sf.group
            for sf in msg.get_structured_fields()
            if sf.is_group and sf.group.count_field.tag == 555
        ]
        assert len(legs) == 1
        assert len(legs[0].entries) == 2  # not split by the per-leg alloc tags

    def test_regulatory_and_custom_field_groups(self) -> None:
        from tests.fixtures.sample_messages import THREE_SIXTY_T_SWAP_EXEC_REGULATORY

        msg = _parse(THREE_SIXTY_T_SWAP_EXEC_REGULATORY)
        groups = {
            sf.group.count_field.tag: sf.group for sf in msg.get_structured_fields() if sf.is_group
        }
        assert 1907 in groups
        assert groups[1907].count == 2
        assert len(groups[1907].entries) == 2
        assert 7546 in groups
        assert len(groups[7546].entries) == 1
        # 1906 = 5 decodes via the 360T custom tag enum.
        assert "TVTIC" in (msg.get_field(1906).value_description or "")
        # UTI surfaced into venue_extras by enhance_message.
        assert msg.venue_extras.get("uti") == "UTI-N"


class TestThreeSixtyTAdminMessagesHaveNoProduct:
    """Administrative messages must not be labelled with a tradeable product."""

    def test_quote_cancel_has_no_product(self) -> None:
        from tests.fixtures.sample_messages import THREE_SIXTY_T_QUOTE_CANCEL

        assert _parse(THREE_SIXTY_T_QUOTE_CANCEL).product_type is None

    def test_security_definition_has_no_product(self) -> None:
        assert _parse(THREE_SIXTY_T_SECURITY_DEFINITION).product_type is None

    def test_field_echoing_reject_has_no_product(self) -> None:
        # A QuoteRequestReject (35=AG) that echoes request fields (64/7070/7071)
        # must still resolve to no product (msg-type gate), not "Spot".
        raw = (
            "8=FIX.4.4|9=0|35=AG|49=360T|56=CLIENT|34=1|52=20240115-10:40:00|"
            "131=QR-SPOT-1|658=99|146=1|55=EUR/USD|537=1|15=EUR|7071=FX-STD|"
            "64=20240117|7070=20240117|58=ExpireTime is in the past.|10=000|"
        )
        assert _parse(raw).product_type is None


class TestThreeSixtyTProductDerivation:
    @pytest.mark.parametrize(
        "sample, expected",
        [
            ("THREE_SIXTY_T_SPOT_QUOTE_REQUEST", "Spot"),
            ("THREE_SIXTY_T_FORWARD_QUOTE_REQUEST", "Forward"),
            ("THREE_SIXTY_T_SWAP_QUOTE_REQUEST", "Swap"),
            ("THREE_SIXTY_T_SWAP_QUOTE", "Swap"),
            ("THREE_SIXTY_T_SWAP_EXEC", "Swap"),
            ("THREE_SIXTY_T_NDF_EXEC", "NDF"),
            ("THREE_SIXTY_T_NDS_EXEC", "NDS"),
            ("THREE_SIXTY_T_TIME_OPTION_EXEC", "FX Time Option"),
            ("THREE_SIXTY_T_BLOCK_TRADE", "Block Trade"),
        ],
    )
    def test_product_type_derived(self, sample: str, expected: str) -> None:
        import tests.fixtures.sample_messages as samples

        msg = _parse(getattr(samples, sample))
        assert msg.product_type == expected


class TestProductTypeGuardUniversality:
    def test_other_venues_still_use_registry(self) -> None:
        """A venue that does not set product_type still gets it from the registry."""
        from fxfixparser.products.base import ProductRegistry
        from tests.fixtures.sample_messages import SWAP_MESSAGE

        parser = FixParser(config=ParserConfig(strict_checksum=False))
        msg = parser.parse(SWAP_MESSAGE)  # Smart Trade; no product_type set in enhance
        assert msg.product_type is None  # parser does not run product detection
        handler = ProductRegistry.default().detect(msg)
        assert handler is not None and handler.product_type == "Swap"


class TestThreeSixtyTSwapEconomics:
    def test_swap_execution_far_leg_and_side(self) -> None:
        msg = _parse(THREE_SIXTY_T_SWAP_EXEC)
        trade = ThreeSixtyTHandler().extract_trade(msg)

        assert trade.is_swap is True
        assert trade.symbol == "EUR/USD"
        assert trade.base_currency == "EUR"
        assert trade.term_currency == "USD"
        # Near rate from LastPx(31); far rate from LastPx2(6160), NOT Price2(640).
        assert trade.near_leg_price == pytest.approx(1.08400)
        assert trade.far_leg_price == pytest.approx(1.08500)
        assert trade.swap_points == pytest.approx(0.00100)
        assert trade.swap_points_pips == pytest.approx(10.0)
        assert trade.spot_rate == pytest.approx(1.08380)  # LastSpotRate(194)
        # Side(54)=1, base ccy EUR, far leg ⇒ Buy EUR far / Sell EUR near.
        assert trade.near_leg_action == "Sell EUR"
        assert trade.far_leg_action == "Buy EUR"
        assert trade.swap_side_source == "360t"
        assert trade.settlement_date == "20240117"
        assert trade.far_settlement_date == "20240417"

    def test_swap_quote_far_leg_rates_and_points(self) -> None:
        msg = _parse(THREE_SIXTY_T_SWAP_QUOTE)
        trade = ThreeSixtyTHandler().extract_trade(msg)

        assert trade.is_quote is True
        assert trade.is_swap is True
        assert trade.quantity == pytest.approx(1000000.0)
        assert trade.bid_price == pytest.approx(1.08490)
        assert trade.offer_price == pytest.approx(1.08510)
        assert trade.bid_spot_rate == pytest.approx(1.08480)
        assert trade.offer_spot_rate == pytest.approx(1.08520)
        assert trade.near_quantity == pytest.approx(1000000.0)
        assert trade.far_quantity == pytest.approx(1000000.0)
        assert trade.near_leg_bid_rate == pytest.approx(1.08490)
        assert trade.near_leg_offer_rate == pytest.approx(1.08510)
        assert trade.far_leg_bid_rate == pytest.approx(1.08560)
        assert trade.far_leg_offer_rate == pytest.approx(1.08590)
        assert trade.bid_swap_points == pytest.approx(0.00070)
        assert trade.offer_swap_points == pytest.approx(0.00080)

    def test_swap_quote_request_far_leg_and_side(self) -> None:
        msg = _parse(THREE_SIXTY_T_SWAP_QUOTE_REQUEST)
        trade = ThreeSixtyTHandler().extract_trade(msg)

        assert msg.product_type == "Swap"
        assert trade.is_quote is False
        assert trade.is_swap is True
        assert trade.symbol == "EUR/USD"
        assert trade.base_currency == "EUR"
        assert trade.term_currency == "USD"
        assert trade.quantity == pytest.approx(1000000.0)
        assert trade.near_quantity == pytest.approx(1000000.0)
        assert trade.far_quantity == pytest.approx(1000000.0)
        assert trade.settlement_date == "20240117"
        assert trade.far_settlement_date == "20240417"
        assert trade.near_leg_action == "Sell EUR"
        assert trade.far_leg_action == "Buy EUR"
        assert trade.swap_side_source == "360t"

    def test_spot_quote_is_not_swap(self) -> None:
        from tests.fixtures.sample_messages import THREE_SIXTY_T_SPOT_QUOTE

        trade = ThreeSixtyTHandler().extract_trade(_parse(THREE_SIXTY_T_SPOT_QUOTE))
        assert trade.is_quote is True
        assert trade.is_swap is False
        assert trade.far_leg_bid_rate is None
        assert trade.far_leg_offer_rate is None
        assert trade.bid_swap_points is None
        assert trade.offer_swap_points is None
        assert trade.quantity == pytest.approx(1000000.0)
        assert trade.bid_price == pytest.approx(1.08490)

    def test_nds_economics(self) -> None:
        msg = _parse(THREE_SIXTY_T_NDS_EXEC)
        trade = ThreeSixtyTHandler().extract_trade(msg)
        assert trade.is_swap is True
        assert trade.symbol == "USD/KRW"
        assert trade.near_leg_price == pytest.approx(1320.50)
        assert trade.far_leg_price == pytest.approx(1325.00)
        assert trade.swap_points == pytest.approx(4.5)
        # USD/KRW is quoted to 2 dp ⇒ pip 0.01 ⇒ 450 pips (not 45000).
        assert trade.swap_points_pips == pytest.approx(450.0)
        assert trade.far_settlement_date == "20240517"

    def test_time_option_economics(self) -> None:
        msg = _parse(THREE_SIXTY_T_TIME_OPTION_EXEC)
        trade = ThreeSixtyTHandler().extract_trade(msg)
        assert msg.product_type == "FX Time Option"
        assert trade.is_swap is False
        assert trade.symbol == "EUR/USD"
        assert trade.side == "Buy"
        assert trade.price == pytest.approx(1.09000)
        assert trade.settlement_date == "20240415"
        assert msg.get_value(9514) == "1M"
        assert msg.get_value(9515) == "20240415"

    def test_block_trade_is_not_a_swap(self) -> None:
        msg = _parse(THREE_SIXTY_T_BLOCK_TRADE)
        trade = ThreeSixtyTHandler().extract_trade(msg)
        assert trade.is_swap is False
        assert trade.symbol == "USD/BRL"
        assert "As Defined" in (trade.side or "")
        # Swap economics the base handler derived from the 2 legs are cleared.
        assert trade.near_leg_price is None
        assert trade.far_leg_price is None
        assert trade.swap_points is None
        assert trade.swap_side_source is None

    def test_forward_execution_basic(self) -> None:
        msg = _parse(THREE_SIXTY_T_FORWARD_EXEC)
        trade = ThreeSixtyTHandler().extract_trade(msg)
        assert trade.is_swap is False
        assert trade.symbol == "EUR/USD"
        assert trade.side == "Buy"
        assert trade.price == pytest.approx(1.09000)
        assert trade.settlement_date == "20240415"

    def test_ndf_execution_fixing(self) -> None:
        msg = _parse(THREE_SIXTY_T_NDF_EXEC)
        trade = ThreeSixtyTHandler().extract_trade(msg)
        assert trade.is_swap is False
        assert trade.symbol == "USD/KRW"
        assert msg.product_type == "NDF"
        assert msg.get_value(541) == "20240413"  # fixing date
