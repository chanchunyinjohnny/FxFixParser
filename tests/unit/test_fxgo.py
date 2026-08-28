"""Unit tests for the Bloomberg FXGO venue handler.

Covers the three plain-FIX 4.4 FXGO interfaces described by the Bloomberg
specs: FIXBOOK for Liquidity Providers (streaming / RFS quoting), FXGO Algo
(FXOM) and FXGO STP (drop copy), which share the ``BLP`` CompID and one
Bloomberg tag space.
"""

import pytest

from fxfixparser.core.parser import FixParser, ParserConfig
from fxfixparser.venues.fxgo import FXGOHandler
from fxfixparser.venues.registry import VenueRegistry
from tests.fixtures.sample_messages import (
    BLOOMBERG_MAP_SWAP_EXEC,
    FXGO_ALGO_EXEC,
    FXGO_BATCH_MASS_QUOTE,
    FXGO_RFS_SWAP_QUOTE,
    FXGO_STP_OPTION_EXEC,
    FXGO_SWAP_EXEC,
)


@pytest.fixture
def handler():
    return FXGOHandler()


@pytest.fixture
def parser():
    return FixParser(config=ParserConfig(strict_checksum=False))


def _group(message, count_tag):
    for sf in message.get_structured_fields():
        if sf.is_group and sf.group and sf.group.count_field.tag == count_tag:
            return sf.group
    return None


class TestFXGODetection:
    """Venue detection for the BLP CompID and its separation from DOR."""

    def test_blp_comp_id_listed(self, handler) -> None:
        """BLP — the Bloomberg-side CompID fixed by the FIXBOOK and Algo
        specs — must identify the FXGO venue."""
        assert "BLP" in handler.sender_comp_ids
        assert handler.matches_sender("BLP")
        assert handler.matches_sender("blp")

    def test_message_from_bloomberg_detects_fxgo(self, parser) -> None:
        """49=BLP (Bloomberg-originated Algo/STP message) resolves to FXGO."""
        message = parser.parse(FXGO_ALGO_EXEC, auto_detect_venue=True)
        assert message.venue == "Bloomberg FXGO"

    def test_message_to_bloomberg_detects_fxgo(self, parser) -> None:
        """56=BLP (LP-originated FIXBOOK message) resolves to FXGO via the
        TargetCompID fallback."""
        message = parser.parse(FXGO_RFS_SWAP_QUOTE, auto_detect_venue=True)
        assert message.venue == "Bloomberg FXGO"

    def test_map_traffic_still_detects_as_dor(self, parser) -> None:
        """MAP_BLP* CompIDs stay with the Bloomberg DOR venue — the BLP
        CompID must not pull the ORP/DOR dialect onto FXGO."""
        message = parser.parse(BLOOMBERG_MAP_SWAP_EXEC, auto_detect_venue=True)
        assert message.venue == "Bloomberg DOR"

    def test_registry_resolves_blp(self, parser) -> None:
        registry = VenueRegistry.default()
        message = parser.parse(FXGO_SWAP_EXEC)
        detected = registry.detect_from_message(message)
        assert detected is not None
        assert detected.name == "Bloomberg FXGO"


class TestFXGOFieldExplanations:
    """FXGO custom tags must decode with the spec names and descriptions."""

    def test_fixbook_quote_tags(self, parser, handler) -> None:
        message = parser.parse(FXGO_RFS_SWAP_QUOTE, venue=handler)
        quote_type = message.get_field(5082)
        assert quote_type.name == "QuoteType"
        assert quote_type.value_description == "Manual pricing (RFS)"
        assert message.get_field(6050).name == "BidPx2"
        assert message.get_field(6051).name == "OfferPx2"
        assert message.get_field(9518).name == "MidRateNear"
        assert message.get_field(9520).name == "MidRateFar"
        assert message.get_field(6216).name == "Tenor2"
        # 6215 comes from the shared Bloomberg core
        assert message.get_field(6215).name == "Tenor"

    def test_fixbook_exec_tags(self, parser, handler) -> None:
        message = parser.parse(FXGO_SWAP_EXEC, venue=handler)
        assert message.get_field(6160).name == "LastPx2"
        assert message.get_field(5177).name == "Source"
        assert message.get_field(9170).name == "CLExecID"

    def test_algo_tags(self, parser, handler) -> None:
        message = parser.parse(FXGO_ALGO_EXEC, venue=handler)
        assert message.get_field(22213).name == "AlgoStrategyName"
        assert message.get_field(10006).name == "DayNetAvgSpot"
        assert message.get_field(10119).name == "DayNetContraCumQty"
        assert message.get_field(11026).name == "DayBaseAvgSpot"
        assert message.get_field(11027).name == "DayAvgPoints"
        assert message.get_field(22828).name == "LastAllInPx"
        # Shared Bloomberg core applies to FXGO messages too
        assert message.get_field(22858).name == "AlgoStrategyID"
        assert message.get_field(22159).name == "Ccy1MarketType"

    def test_stp_option_tags(self, parser, handler) -> None:
        message = parser.parse(FXGO_STP_OPTION_EXEC, venue=handler)
        style = message.get_field(1194)
        assert style.name == "ExerciseStyle"
        assert style.value_description == "European"
        assert message.get_field(1193).value_description == "Physical settlement required"
        assert message.get_field(2141).name == "StrategyType"
        assert message.get_field(5844).name == "NetPremiumAmount"
        assert message.get_field(5830).name == "PremiumCurrency"
        assert message.get_field(22052).name == "LastMidPrice"
        assert message.get_field(9657).name == "HedgeRate"
        # Bloomberg reuses 9123 as HedgeAmount on FXGO STP (venue override
        # of the standard MDEntryOrigDate meaning).
        assert message.get_field(9123).name == "HedgeAmount"
        assert message.get_field(9112).name == "SymbolCcyRefID"
        rate_source = message.get_field(1446)
        assert rate_source.name == "RateSource"
        assert rate_source.value_description == "Reuters (WMR)"

    def test_misc_fee_markup_enum_extension(self, parser, handler) -> None:
        """MiscFeeType(139)=8 must decode via the FXGO enum extension."""
        message = parser.parse(FXGO_STP_OPTION_EXEC, venue=handler)
        fee_type = message.get_field(139)
        assert "Markup" in (fee_type.value_description or "")
        fee_desc = message.get_field(2713)
        assert fee_desc.value_description == "Markup to option premium"


class TestFXGOGroups:
    """Repeating groups from the STP / FIXBOOK specs must parse intact."""

    def test_ref_price_group(self, parser, handler) -> None:
        message = parser.parse(FXGO_STP_OPTION_EXEC, venue=handler)
        group = _group(message, 22078)
        assert group is not None, "RefPriceGrp not detected"
        assert group.count == 2
        assert len(group.entries) == 2
        first = {f.tag: f.raw_value for f in group.entries[0].fields}
        assert first[22079] == "0.0125"
        assert first[22085] == "QREF-1"
        second = {f.tag: f.raw_value for f in group.entries[1].fields}
        assert second[22081] == "9"

    def test_comp_dealer_group_with_stp_members(self, parser, handler) -> None:
        """The STP CompDealerQuoteGrp additions (first/last quote data and
        the transaction fee) must stay inside the single entry."""
        message = parser.parse(FXGO_STP_OPTION_EXEC, venue=handler)
        group = _group(message, 10009)
        assert group is not None
        assert len(group.entries) == 1
        tags = {f.tag for f in group.entries[0].fields}
        assert {10010, 10011, 10012, 22276, 22868, 22880, 22881, 22545} <= tags

    def test_reference_id_group(self, parser, handler) -> None:
        message = parser.parse(FXGO_STP_OPTION_EXEC, venue=handler)
        group = _group(message, 22215)
        assert group is not None
        assert len(group.entries) == 1
        entry = {f.tag: f for f in group.entries[0].fields}
        assert entry[22216].value_description.startswith("Deal ID")

    def test_misc_fees_group(self, parser, handler) -> None:
        message = parser.parse(FXGO_STP_OPTION_EXEC, venue=handler)
        group = _group(message, 136)
        assert group is not None
        assert len(group.entries) == 1
        tags = {f.tag for f in group.entries[0].fields}
        assert {137, 138, 139, 2216, 2713} <= tags

    def test_mass_quote_set_flattens_entries(self, parser, handler) -> None:
        """The MassQuote QuoteSet (296=1) must hold both flattened
        NoQuoteEntries legs without phantom entry splits."""
        message = parser.parse(FXGO_BATCH_MASS_QUOTE, venue=handler)
        group = _group(message, 296)
        assert group is not None
        assert group.count == 1
        assert len(group.entries) == 1
        entry_ids = [f.raw_value for f in group.entries[0].fields if f.tag == 299]
        assert entry_ids == ["E1", "E2"]


class TestFXGOSwapExtraction:
    """Swap economics from the FXGO flat-tag shapes."""

    def test_rfs_swap_quote_summary(self, parser, handler) -> None:
        """Two-way RFS swap quote: near all-in from 132/133, far all-in
        from BidPx2/OfferPx2, swap points computed far - near."""
        message = parser.parse(FXGO_RFS_SWAP_QUOTE, venue=handler)
        trade = handler.extract_trade(message)

        assert trade.is_quote is True
        assert trade.is_swap is True
        assert trade.side == "Two-Way"
        assert trade.symbol == "EUR/USD"
        assert trade.settlement_date == "20260928"
        assert trade.far_settlement_date == "20261028"
        assert trade.near_leg_bid_rate == pytest.approx(1.08500)
        assert trade.near_leg_offer_rate == pytest.approx(1.08520)
        assert trade.far_leg_bid_rate == pytest.approx(1.08652)
        assert trade.far_leg_offer_rate == pytest.approx(1.08675)
        assert trade.bid_swap_points == pytest.approx(0.00152)
        assert trade.offer_swap_points == pytest.approx(0.00155)
        assert trade.swap_points_source == "computed"

    def test_swap_exec_far_leg_from_lastpx2(self, parser, handler) -> None:
        """Executed swap: far leg all-in comes from LastPx2 (6160), swap
        points derived from the two all-in rates."""
        message = parser.parse(FXGO_SWAP_EXEC, venue=handler)
        trade = handler.extract_trade(message)

        assert trade.is_swap is True
        assert trade.symbol == "USD/JPY"
        assert trade.near_leg_price == pytest.approx(147.25)
        assert trade.far_leg_price == pytest.approx(146.80)
        assert trade.swap_points == pytest.approx(-0.45)
        assert trade.spot_rate == pytest.approx(147.20)
        assert trade.settlement_date == "20260901"
        assert trade.far_settlement_date == "20261201"
        assert trade.near_quantity == pytest.approx(1000000.0)
        assert trade.far_quantity == pytest.approx(1000000.0)

    def test_non_swap_quote_untouched(self, parser, handler) -> None:
        """A spot-only quote must not grow swap fields from the override."""
        spot_quote = (
            "8=FIX.4.4|9=0120|35=S|34=7|49=LPBANK|56=BLP|52=20260828-08:00:00|"
            "131=RFQ-1|117=Q-1|5082=4|55=EUR/USD|15=EUR|132=1.08450|"
            "133=1.08470|134=1000000|135=1000000|64=20260901|6215=SP|"
            "60=20260828-08:00:00|10=000|"
        )
        message = parser.parse(spot_quote, venue=handler)
        trade = handler.extract_trade(message)
        assert trade.is_swap is False
        assert trade.near_leg_bid_rate is None
        assert trade.bid_swap_points is None
