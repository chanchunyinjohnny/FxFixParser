"""Unit tests for the 360T TradeImporter (TI) venue handler."""

import pytest

from fxfixparser.core.parser import FixParser, ParserConfig
from fxfixparser.venues.registry import VenueRegistry
from fxfixparser.venues.three_sixty_t_ti import ThreeSixtyTTIHandler
from tests.fixtures.sample_messages import (
    THREE_SIXTY_T_SWAP_EXEC,  # RFS swap (7071=FX-STD) — detection regression
)
from tests.fixtures.sample_messages import (
    THREE_SIXTY_T_TI_FORWARD,
    THREE_SIXTY_T_TI_MONEY_MARKET,
    THREE_SIXTY_T_TI_NDS,
    THREE_SIXTY_T_TI_OPTION,
    THREE_SIXTY_T_TI_SPOT,
    THREE_SIXTY_T_TI_SWAP,
)


def _parse(raw: str):
    """Parse with the TI venue explicitly selected."""
    parser = FixParser(config=ParserConfig(strict_checksum=False))
    return parser.parse(raw, venue="360T TI")


def _parse_raw(raw: str):
    """Parse with no venue (for claims_message / auto-detect tests)."""
    parser = FixParser(config=ParserConfig(strict_checksum=False))
    return parser.parse(raw)


def _autodetect(raw: str):
    parser = FixParser(config=ParserConfig(strict_checksum=False))
    return parser.parse(raw, auto_detect_venue=True)


class TestTIHandlerProperties:
    def test_name(self) -> None:
        assert ThreeSixtyTTIHandler().name == "360T TI"

    def test_sender_comp_ids(self) -> None:
        handler = ThreeSixtyTTIHandler()
        assert handler.matches_sender("360T_TI")
        assert not handler.matches_sender("360T")  # that is the RFS alias
        assert not handler.matches_sender("FXGO")


class TestTIClaimsMessage:
    """claims_message must claim TI traffic and abstain on everything else."""

    def test_claims_on_ti_product_type(self) -> None:
        handler = ThreeSixtyTTIHandler()
        assert handler.claims_message(_parse_raw(THREE_SIXTY_T_TI_SPOT))

    def test_claims_on_competing_quotes(self) -> None:
        handler = ThreeSixtyTTIHandler()
        # NoCompetingQuotes(9516) present even without a TI product code.
        raw = (
            "8=FIX.4.4|9=0|35=8|49=SOMECLIENT|56=ALSO|34=1|52=20190731-10:40:36|"
            "37=1|17=1|150=F|39=2|55=EUR/USD|9516=1|9517=BANK|9518=1.1|10=000|"
        )
        assert handler.claims_message(_parse_raw(raw))

    def test_claims_on_ti_compid(self) -> None:
        handler = ThreeSixtyTTIHandler()
        raw = "8=FIX.4.4|9=0|35=8|49=360T_TI|56=ACME_TI|34=1|55=EUR/USD|10=000|"
        assert handler.claims_message(_parse_raw(raw))

    def test_does_not_claim_rfs_message(self) -> None:
        handler = ThreeSixtyTTIHandler()
        # RFS swap: 7071=FX-STD, CompID 360T, no 9516 → must NOT be claimed.
        assert not handler.claims_message(_parse_raw(THREE_SIXTY_T_SWAP_EXEC))

    def test_does_not_claim_non_execution_report(self) -> None:
        handler = ThreeSixtyTTIHandler()
        raw = "8=FIX.4.4|9=0|35=S|49=360T_TI|56=ACME|34=1|55=EUR/USD|10=000|"
        assert not handler.claims_message(_parse_raw(raw))


class TestTIDetection:
    """Auto-detection must distinguish TI from RFS."""

    def test_ti_message_autodetects_as_ti(self) -> None:
        assert _autodetect(THREE_SIXTY_T_TI_SWAP).venue == "360T TI"

    def test_rfs_message_still_autodetects_as_rfs(self) -> None:
        assert _autodetect(THREE_SIXTY_T_SWAP_EXEC).venue == "360T RFS"

    def test_ti_handler_registered(self) -> None:
        registry = VenueRegistry.default()
        assert registry.get("360T TI") is not None
        assert registry.get("360T RFS") is not None


class TestTICustomTags:
    def test_competing_quote_tags_decode(self) -> None:
        msg = _parse(THREE_SIXTY_T_TI_SPOT)
        assert msg.get_field(9516).name == "NoCompetingQuotes"
        assert msg.get_field(9517).name == "CompetingQuoteDealer"
        assert msg.get_field(9518).name == "CompetingQuote"

    def test_execution_venue_tags_decode(self) -> None:
        msg = _parse(THREE_SIXTY_T_TI_FORWARD)
        assert msg.get_field(7612).name == "ExecutionVenue"
        assert msg.get_field(7653).name == "UTIID"

    def test_execution_venue_type_mtf_enum(self) -> None:
        # TI ExecutionVenueType(7611) enum: 1=SEF, 2=OFF-FACILITY, 3=MTF.
        f = _parse(THREE_SIXTY_T_TI_FORWARD).get_field(7611)
        assert "MTF" in (f.value_description or "")

    def test_far_leg_uti_tags_decode(self) -> None:
        msg = _parse(THREE_SIXTY_T_TI_SWAP)
        assert msg.get_field(7659).name == "UTIIDNear"
        assert msg.get_field(7660).name == "UTIIDFar"


class TestTIProductDerivation:
    @pytest.mark.parametrize(
        "fixture, expected",
        [
            (THREE_SIXTY_T_TI_SPOT, "Spot"),
            (THREE_SIXTY_T_TI_FORWARD, "Forward"),
            (THREE_SIXTY_T_TI_SWAP, "Swap"),
            (THREE_SIXTY_T_TI_NDS, "NDS"),
            (THREE_SIXTY_T_TI_OPTION, "FX Option"),
            (THREE_SIXTY_T_TI_MONEY_MARKET, "Money Market"),
        ],
    )
    def test_product_type(self, fixture: str, expected: str) -> None:
        assert _parse(fixture).product_type == expected

    def test_ndf_product_type(self) -> None:
        raw = (
            "8=FIX.4.4|9=0|35=8|49=ACME_TI|56=360T_TI|34=1|52=20190731-10:40:36|"
            "37=1|17=1|150=F|39=2|54=1|55=USD/KRW|38=5000000|31=1320.5|194=1320.5|"
            "64=20190805|7071=FX-NDF|7543=20190801|7075=KFTC18|10=000|"
        )
        assert _parse(raw).product_type == "NDF"

    def test_time_option_product_type(self) -> None:
        raw = (
            "8=FIX.4.4|9=0|35=8|49=ACME_TI|56=360T_TI|34=1|52=20190731-10:40:36|"
            "37=1|17=1|150=F|39=2|54=1|55=EUR/USD|38=1000000|31=1.09|194=1.085|"
            "64=20190805|7071=FX-TIME-OPTION|9514=1M|9515=20190905|10=000|"
        )
        assert _parse(raw).product_type == "FX Time Option"


class TestTISwapEconomics:
    def test_swap_is_flagged(self) -> None:
        assert _parse(THREE_SIXTY_T_TI_SWAP).venue  # sanity: parsed
        trade = _trade(THREE_SIXTY_T_TI_SWAP)
        assert trade.is_swap is True

    def test_swap_near_and_far_prices(self) -> None:
        trade = _trade(THREE_SIXTY_T_TI_SWAP)
        assert trade.near_leg_price == pytest.approx(1.2168)
        assert trade.far_leg_price == pytest.approx(1.2270200)

    def test_swap_settlement_dates(self) -> None:
        trade = _trade(THREE_SIXTY_T_TI_SWAP)
        assert trade.settlement_date == "20190802"
        assert trade.far_settlement_date == "20200203"

    def test_swap_points_from_6160(self) -> None:
        trade = _trade(THREE_SIXTY_T_TI_SWAP)
        assert trade.swap_points == pytest.approx(0.01022)
        assert trade.swap_points_pips == pytest.approx(102.2)

    def test_swap_side_uses_360t_convention(self) -> None:
        trade = _trade(THREE_SIXTY_T_TI_SWAP)
        assert trade.swap_side_source == "360t"
        # Side(54)=2 relative to base GBP on the far leg; near is the opposite.
        assert trade.near_leg_action == "Buy GBP"
        assert trade.far_leg_action == "Sell GBP"

    def test_nds_is_swap(self) -> None:
        trade = _trade(THREE_SIXTY_T_TI_NDS)
        assert trade.is_swap is True
        assert trade.far_leg_price == pytest.approx(1325.00)


class TestTINonSwapNotFlagged:
    """Products carrying a stray 192/193 must not be mistaken for swaps."""

    def test_option_not_swap_despite_orderqty2(self) -> None:
        # Option premium rides in OrderQty2(192) — must not flag is_swap.
        trade = _trade(THREE_SIXTY_T_TI_OPTION)
        assert trade.is_swap is False

    def test_money_market_not_swap_despite_settldate2(self) -> None:
        # MM end date rides in SettlDate2(193) — must not flag is_swap.
        trade = _trade(THREE_SIXTY_T_TI_MONEY_MARKET)
        assert trade.is_swap is False

    def test_spot_not_swap(self) -> None:
        assert _trade(THREE_SIXTY_T_TI_SPOT).is_swap is False


class TestTITradeBasics:
    def test_spot_quantity_and_symbol(self) -> None:
        trade = _trade(THREE_SIXTY_T_TI_SPOT)
        assert trade.symbol == "EUR/USD"
        assert trade.quantity == pytest.approx(500000.0)

    def test_spot_is_not_quote(self) -> None:
        # TI is always a post-trade ExecutionReport, never a quote.
        assert _trade(THREE_SIXTY_T_TI_SPOT).is_quote is False


class TestTIGroupParsing:
    def test_competing_quotes_group(self) -> None:
        groups = _groups(THREE_SIXTY_T_TI_SPOT, count_tag=9516)
        assert groups is not None
        assert groups.count == 4
        assert len(groups.entries) == 4

    def test_regulatory_trade_id_group(self) -> None:
        groups = _groups(THREE_SIXTY_T_TI_SWAP, count_tag=1907)
        assert groups is not None
        assert len(groups.entries) == 3

    def test_security_alt_id_group(self) -> None:
        groups = _groups(THREE_SIXTY_T_TI_SWAP, count_tag=454)
        assert groups is not None
        assert len(groups.entries) == 2

    def test_party_group_with_role_qualifier(self) -> None:
        # The 453 party group must absorb PartyRoleQualifier(2376) without
        # splitting the entry early.
        groups = _groups(THREE_SIXTY_T_TI_FORWARD, count_tag=453)
        assert groups is not None
        assert groups.count == 5
        assert len(groups.entries) == 5


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _trade(raw: str):
    handler = ThreeSixtyTTIHandler()
    msg = _parse(raw)
    return handler.extract_trade(msg)


def _groups(raw: str, count_tag: int):
    msg = _parse(raw)
    for sf in msg.get_structured_fields():
        if sf.is_group and sf.group and sf.group.count_field.tag == count_tag:
            return sf.group
    return None
