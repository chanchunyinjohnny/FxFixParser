"""Unit tests for the LSEG / Refinitiv FX Matching (MAPI) venue handler."""

import pytest

from fxfixparser.core.field import FixField
from fxfixparser.core.message import FixMessage
from fxfixparser.core.parser import FixParser, ParserConfig
from fxfixparser.venues.lseg_fx_matching import LSEGFXMatchingHandler
from fxfixparser.venues.registry import VenueRegistry
from tests.fixtures.sample_messages import (
    LSEG_FXM_QUOTE,
    LSEG_FXM_SPOT_EXECUTION,
    LSEG_FXM_SPOT_TRADE_CAPTURE,
    LSEG_FXM_SWAP_EXECUTION,
    LSEG_FXM_SWAP_TRADE_CAPTURE,
)


def _msg(tag_values: dict[int, str]) -> FixMessage:
    return FixMessage(fields=[FixField(tag=t, raw_value=v) for t, v in tag_values.items()])


def _parser() -> FixParser:
    return FixParser(config=ParserConfig(strict_checksum=False, strict_body_length=False))


class TestHandlerIdentity:
    def test_name(self) -> None:
        assert LSEGFXMatchingHandler().name == "LSEG FX Matching"

    def test_sender_ids_include_tr_matching(self) -> None:
        assert "TR MATCHING" in LSEGFXMatchingHandler().sender_comp_ids

    def test_matches_sender_case_insensitive(self) -> None:
        h = LSEGFXMatchingHandler()
        assert h.matches_sender("tr matching") is True
        assert h.matches_sender("TR MATCHING") is True
        assert h.matches_sender("UNKNOWN") is False
        assert h.matches_sender(None) is False

    def test_enhance_message_sets_venue(self) -> None:
        enhanced = LSEGFXMatchingHandler().enhance_message(FixMessage())
        assert enhanced.venue == "LSEG FX Matching"


class TestVenueDetection:
    def test_detect_by_target_comp_id(self) -> None:
        # client -> MAPI: TargetCompID(56) carries the venue CompID
        reg = VenueRegistry.default()
        h = reg.detect_from_message(_msg({49: "AAAA017752", 56: "TR MATCHING"}))
        assert h is not None and h.name == "LSEG FX Matching"

    def test_detect_by_sender_comp_id(self) -> None:
        # MAPI -> client: SenderCompID(49) carries the venue CompID
        reg = VenueRegistry.default()
        h = reg.detect_from_message(_msg({49: "TR MATCHING", 56: "AAAA017752"}))
        assert h is not None and h.name == "LSEG FX Matching"

    def test_unknown_comp_id_no_match(self) -> None:
        reg = VenueRegistry.default()
        assert reg.detect_from_message(_msg({49: "NOPE", 56: "NADA"})) is None

    def test_registry_contains_lseg(self) -> None:
        assert VenueRegistry.default().get("LSEG FX Matching") is not None


class TestCustomTags:
    def test_trade_udfs_defined(self) -> None:
        d = {t.tag: t for t in LSEGFXMatchingHandler().custom_tags}
        assert d[5007].name == "LockedStatus"
        assert d[5007].valid_values["Y"] == "Locked"
        assert d[20020].name == "OrdersLockFilter"
        assert d[31344].name == "TR_TradingCapacity"
        assert d[31344].valid_values["1"].startswith("DEAL")
        assert d[31345].name == "TR_Npft"

    def test_venue_scoped_override_defined(self) -> None:
        d = {t.tag: t for t in LSEGFXMatchingHandler().custom_tags}
        assert d[1056].name == "CalculatedCcyLastQty"

    def test_no_fabricated_credit_or_leg_overrides(self) -> None:
        """MAPI carries credit in NoLimitAmts(1630) as 1632/1633 and the leg
        calculated quantity as 1074. Tags 1097/1149/1418 appear nowhere in the
        FIX Interface User Guide, so this venue must not shadow them."""
        tags = {t.tag for t in LSEGFXMatchingHandler().custom_tags}
        assert tags.isdisjoint({1097, 1149, 1418})

    def test_admin_udfs_labelled(self) -> None:
        d = {t.tag: t for t in LSEGFXMatchingHandler().custom_tags}
        assert d[20005].valid_values["0"] == "Success"
        assert d[20010].valid_values["1"] == "Enabled"


class TestCustomTagsDecode:
    def test_credit_group_decodes_with_standard_names(self) -> None:
        body = (
            "8=FIXT.1.1|9=0|35=AE|49=TR MATCHING|56=AAAA017752|1128=9|"
            "167=FXSPOT|1630=1|1631=0|1632=5|1633=49|1634=USD|10=000|"
        )
        msg = _parser().parse(body, venue="LSEG FX Matching")
        assert msg.get_field(1632).name == "LastLimitAmt"
        assert msg.get_field(1633).name == "LimitAmtRemaining"
        assert msg.get_field(1631).value_description.startswith("Credit Limit")

    def test_locked_status_decodes(self) -> None:
        body = "8=FIXT.1.1|9=0|35=D|49=TR MATCHING|5007=Y|10=000|"
        msg = _parser().parse(body, venue="LSEG FX Matching")
        assert msg.get_field(5007).value_description == "Locked"


class TestEnumExtensions:
    def _field(self, body: str, tag: int):
        return _parser().parse(body, venue="LSEG FX Matching").get_field(tag)

    def test_security_type_forward_swap(self) -> None:
        f = self._field("8=FIXT.1.1|9=0|35=8|49=TR MATCHING|167=FXSWAP|10=000|", 167)
        assert f.value_description == "FX Forward Swap (Near/Far two-leg)"

    def test_exec_type_hard_and_soft_match(self) -> None:
        assert (
            "Trade"
            in self._field(
                "8=FIXT.1.1|9=0|35=8|49=TR MATCHING|150=F|10=000|", 150
            ).value_description
        )
        assert (
            "soft match"
            in self._field(
                "8=FIXT.1.1|9=0|35=8|49=TR MATCHING|150=I|10=000|", 150
            ).value_description
        )

    def test_pricetype_inverse(self) -> None:
        f = self._field("8=FIXT.1.1|9=0|35=8|49=TR MATCHING|423=21|10=000|", 423)
        assert f.value_description.startswith("Inverse")

    def test_partysubidtype_location_desk(self) -> None:
        f = self._field("8=FIXT.1.1|9=0|35=AE|49=TR MATCHING|803=25|10=000|", 803)
        assert "Location Desk" in f.value_description

    def test_partyrole_acceptable_counterparty(self) -> None:
        f = self._field("8=FIXT.1.1|9=0|35=8|49=TR MATCHING|452=56|10=000|", 452)
        assert f.value_description == "Acceptable Counterparty"

    def test_quote_status_cancelled_no_deal(self) -> None:
        f = self._field("8=FIXT.1.1|9=0|35=S|49=TR MATCHING|297=17|10=000|", 297)
        assert "No-Deal" in f.value_description

    def test_legref_is_near_far_only(self) -> None:
        near = self._field("8=FIXT.1.1|9=0|35=8|49=TR MATCHING|654=Near|10=000|", 654)
        far = self._field("8=FIXT.1.1|9=0|35=AE|49=TR MATCHING|654=Far|10=000|", 654)
        assert "Near" in near.value_description
        assert "Far" in far.value_description

    def test_nosides_two_means_swap_legs_not_counterparties(self) -> None:
        f = self._field("8=FIXT.1.1|9=0|35=AE|49=TR MATCHING|552=2|10=000|", 552)
        assert "near and far legs" in f.value_description

    def test_custom_msgtype_u3_labelled(self) -> None:
        f = self._field("8=FIXT.1.1|9=0|35=U3|49=TR MATCHING|10=000|", 35)
        assert f.value_description is not None
        assert "PBC" in f.value_description


class TestTagOverrideVenueIsolation:
    """The 1056 reuse must be venue-scoped, not global."""

    def _name(self, raw: str, venue, tag: int) -> str:
        return _parser().parse(raw, venue=venue).get_field(tag).name

    def test_1056_description_is_venue_scoped(self) -> None:
        raw = "8=FIXT.1.1|9=0|35=AE|49=TR MATCHING|56=AAAA017752|1128=9|1056=1.08|10=000|"
        lseg = _parser().parse(raw, venue="LSEG FX Matching").get_field(1056)
        plain = _parser().parse(raw, venue=None).get_field(1056)
        assert "LastSpotRate" in lseg.description
        assert "LastSpotRate" not in (plain.description or "")

    def test_standard_tags_keep_standard_meaning_under_lseg(self) -> None:
        """Tags the venue used to shadow must now decode as standard FIX."""
        raw = (
            "8=FIXT.1.1|9=0|35=AE|49=TR MATCHING|56=AAAA017752|1128=9|"
            "1149=49|1418=1|1097=X|10=000|"
        )
        assert self._name(raw, "LSEG FX Matching", 1149) == "HighLimitPrice"
        assert self._name(raw, "LSEG FX Matching", 1418) == "LegLastQty"
        assert self._name(raw, "LSEG FX Matching", 1097) == "PegSecurityID"


class TestExtractTrade:
    def test_spot_execution(self) -> None:
        msg = _parser().parse(LSEG_FXM_SPOT_EXECUTION, venue="LSEG FX Matching")
        trade = LSEGFXMatchingHandler().extract_trade(msg)
        assert trade.symbol == "EUR/USD"
        assert trade.price == pytest.approx(1.085)
        assert trade.is_swap is False
        assert trade.exec_id == "SX1"
        # OrderQty(38)=1 is one *contract* of ContractMultiplier(231)=1,000,000.
        assert trade.quantity == pytest.approx(1_000_000.0)

    def test_contract_multiplier_scales_quantities(self) -> None:
        m = _msg(
            {35: "8", 167: "FXSPOT", 55: "EUR/USD", 54: "1", 32: "5", 31: "1.08", 231: "1000000"}
        )
        assert LSEGFXMatchingHandler().extract_trade(m).quantity == pytest.approx(5_000_000.0)

    def test_contract_multiplier_defaults_when_tag_absent(self) -> None:
        # 231 is conditional on Pending Cancel / Pending Replace reports.
        m = _msg({35: "8", 167: "FXSPOT", 55: "EUR/USD", 54: "1", 38: "0.25", 31: "1.08"})
        assert LSEGFXMatchingHandler().extract_trade(m).quantity == pytest.approx(250_000.0)

    def test_exec_id_prefers_secondary_when_primary_is_present(self) -> None:
        m = _msg(
            {
                35: "8",
                167: "FXSPOT",
                55: "EUR/USD",
                54: "1",
                32: "1",
                31: "1.08",
                17: "NON_UNIQUE",
                527: "UNIQUE_EVENT",
            }
        )
        assert LSEGFXMatchingHandler().extract_trade(m).exec_id == "UNIQUE_EVENT"

    def test_exec_id_falls_back_to_secondary_then_trade_id(self) -> None:
        # No tag 17 -> SecondaryExecID(527); then TradeID(1003).
        m1 = _msg({35: "8", 167: "FXSPOT", 55: "EUR/USD", 54: "1", 32: "1", 31: "1.08", 527: "SX"})
        assert LSEGFXMatchingHandler().extract_trade(m1).exec_id == "SX"
        m2 = _msg(
            {35: "AE", 167: "FXSPOT", 55: "EUR/USD", 54: "1", 32: "1", 31: "1.08", 1003: "TID"}
        )
        assert LSEGFXMatchingHandler().extract_trade(m2).exec_id == "TID"

    def test_order_id_none_is_dropped(self) -> None:
        m = _msg({35: "8", 167: "FXSPOT", 55: "EUR/USD", 54: "1", 32: "1", 31: "1.08", 37: "NONE"})
        assert LSEGFXMatchingHandler().extract_trade(m).order_id is None

    def test_swap_execution_legs_and_points(self) -> None:
        # The ExecutionReport carries no value dates at all — the legs have no
        # LegSettlDate(588) and the message has no SettlDate(64).
        msg = _parser().parse(LSEG_FXM_SWAP_EXECUTION, venue="LSEG FX Matching")
        trade = LSEGFXMatchingHandler().extract_trade(msg)
        assert trade.is_swap is True
        assert trade.symbol == "EUR/USD"
        assert trade.near_leg_price == pytest.approx(1.084)
        assert trade.far_leg_price == pytest.approx(1.085)
        assert trade.swap_points == pytest.approx(0.001)
        # LegOrderQty(685)=1 on each leg, scaled by ContractMultiplier(231).
        assert trade.near_quantity == pytest.approx(1_000_000.0)
        assert trade.far_quantity == pytest.approx(1_000_000.0)

    def test_swap_execution_spot_rate_from_194(self) -> None:
        # The ExecutionReport uses the standard LastSpotRate(194).
        msg = _parser().parse(LSEG_FXM_SWAP_EXECUTION, venue="LSEG FX Matching")
        trade = LSEGFXMatchingHandler().extract_trade(msg)
        assert trade.spot_rate == pytest.approx(1.0838)

    def test_swap_tcr_value_dates_and_overloaded_1056_spot(self) -> None:
        # The TradeCaptureReport carries LegSettlDate(588) and puts the swap
        # spot reference in the overloaded tag 1056 (no 194 anywhere).
        msg = _parser().parse(LSEG_FXM_SWAP_TRADE_CAPTURE, venue="LSEG FX Matching")
        trade = LSEGFXMatchingHandler().extract_trade(msg)
        assert trade.settlement_date == "20260606"
        assert trade.far_settlement_date == "20260908"
        assert trade.spot_rate == pytest.approx(1.0838)
        # LastPx(31) on a swap TCR is the all-in price of the far leg.
        assert trade.price == pytest.approx(1.085)

    def test_explicit_194_wins_over_1056(self) -> None:
        m = _msg(
            {
                35: "AE",
                167: "FXSWAP",
                55: "EUR/USD",
                54: "1",
                193: "20260908",
                194: "1.09000",
                1056: "1.08380",
                31: "1.08500",
            }
        )
        assert LSEGFXMatchingHandler().extract_trade(m).spot_rate == pytest.approx(1.09)

    def test_swap_order_price_44_is_swap_points_not_a_rate(self) -> None:
        """NewOrderSingle: 'For FX Swap orders it specifies the swap points not
        the all-in rate.' The message has no legs, so nothing else marks it as
        a swap either."""
        m = _msg({35: "D", 167: "FXSWAP", 55: "EUR/USD", 54: "1", 38: "5", 44: "0.001"})
        trade = LSEGFXMatchingHandler().extract_trade(m)
        assert trade.is_swap is True
        assert trade.swap_points == pytest.approx(0.001)
        assert trade.swap_points_pips == pytest.approx(10.0)
        assert trade.price is None
        assert trade.quantity == pytest.approx(5_000_000.0)

    def test_quote_negotiation_quantities(self) -> None:
        """Quote(35=S) carries the negotiated amounts in OrderQty(38) and the
        per-leg LegOrderQty(685); it has no SecurityType(167) to key off."""
        msg = _parser().parse(LSEG_FXM_QUOTE, venue="LSEG FX Matching")
        trade = LSEGFXMatchingHandler().extract_trade(msg)
        assert trade.is_swap is True
        assert trade.quantity == pytest.approx(5_000_000.0)
        assert trade.near_quantity == pytest.approx(5_000_000.0)
        assert trade.far_quantity == pytest.approx(5_000_000.0)


class TestEnhanceMessage:
    def test_match_id_and_counterparty_from_tcr(self) -> None:
        msg = _parser().parse(LSEG_FXM_SPOT_TRADE_CAPTURE, venue="LSEG FX Matching")
        enhanced = LSEGFXMatchingHandler().enhance_message(msg)
        assert enhanced.venue_extras.get("match_id") == "MATCH1"
        assert enhanced.venue_extras.get("counterparty") == "CP_BANK"

    def test_counterparty_from_party_group_role_56(self) -> None:
        m = _msg({35: "8", 453: "1", 448: "CP_BANK", 452: "56"})
        enhanced = LSEGFXMatchingHandler().enhance_message(m)
        assert enhanced.venue_extras.get("counterparty") == "CP_BANK"

    def test_no_counterparty_when_role_absent(self) -> None:
        m = _msg({35: "8", 453: "1", 448: "ME_BANK", 452: "13"})
        enhanced = LSEGFXMatchingHandler().enhance_message(m)
        assert "counterparty" not in enhanced.venue_extras


class TestRepeatingGroups:
    @staticmethod
    def _groups(msg, count_tag: int):
        return [
            sf.group
            for sf in msg.get_structured_fields()
            if sf.group is not None and sf.group.count_field.tag == count_tag
        ]

    def test_root_parties_group_structured(self) -> None:
        """The report owner's block carries two RootPartySubIDs (TCID then
        trader login); the repeated 1121/1122 must not split the party."""
        msg = _parser().parse(LSEG_FXM_SPOT_TRADE_CAPTURE, venue="LSEG FX Matching")
        groups = self._groups(msg, 1116)
        assert len(groups) == 1
        assert groups[0].count == 2
        assert len(groups[0].entries) == 2
        assert [f.raw_value for f in groups[0].entries[0].fields if f.tag == 1121] == [
            "MEDESK",
            "metrader",
        ]

    def test_party_ids_group_keeps_multiple_sub_ids_in_one_entry(self) -> None:
        """A MAPI ExecutionReport party carries 2-3 PartySubIDs."""
        msg = _parser().parse(LSEG_FXM_SPOT_EXECUTION, venue="LSEG FX Matching")
        groups = self._groups(msg, 453)
        assert len(groups) == 1
        assert groups[0].count == 2
        assert len(groups[0].entries) == 2
        assert [f.raw_value for f in groups[0].entries[0].fields if f.tag == 523] == [
            "MEDESK",
            "metrader",
        ]
        assert any(f.tag == 452 and f.raw_value == "56" for f in groups[0].entries[1].fields)

    def test_spot_tcr_side_contains_credit_and_settlement_blocks(self) -> None:
        """MAPI nests NoLimitAmts(1630) and NoSettlDetails(1158) inside the
        side, so neither may terminate the NoSides walk."""
        msg = _parser().parse(LSEG_FXM_SPOT_TRADE_CAPTURE, venue="LSEG FX Matching")
        groups = self._groups(msg, 552)
        assert len(groups) == 1
        assert len(groups[0].entries) == 1
        tags = [f.tag for f in groups[0].entries[0].fields]
        # Credit block, both settlement-detail instances, and the side tail.
        assert {1630, 1631, 1632, 1633, 1634, 1158, 1164, 781, 784, 801, 786} <= set(tags)
        assert tags.count(1164) == 2
        assert tags[-4:] == [1057, 37, 11, 38]

    def test_swap_tcr_reports_both_sides(self) -> None:
        msg = _parser().parse(LSEG_FXM_SWAP_TRADE_CAPTURE, venue="LSEG FX Matching")
        groups = self._groups(msg, 552)
        assert len(groups) == 1
        assert groups[0].count == 2
        assert len(groups[0].entries) == 2
        sides = [
            next(f.raw_value for f in entry.fields if f.tag == 54) for entry in groups[0].entries
        ]
        assert sides == ["1", "2"]

    def test_stipulations_group_in_quote(self) -> None:
        msg = _parser().parse(LSEG_FXM_QUOTE, venue="LSEG FX Matching")
        groups = [
            sf.group
            for sf in msg.get_structured_fields()
            if sf.group is not None and sf.group.count_field.tag == 232
        ]
        assert len(groups) == 1
        assert groups[0].count == 1

    def test_mifid_side_fields_do_not_end_sides_group(self) -> None:
        raw = (
            "8=FIXT.1.1|9=000|35=AE|49=TR MATCHING|56=AAAA017752|1128=9|"
            "55=EUR/USD|167=FXSWAP|552=1|54=1|1154=EUR|31=1.08500|"
            "31344=1|31345=N|32=1|1057=Y|75=20260604|10=000|"
        )

        msg = _parser().parse(raw, venue="LSEG FX Matching")
        groups = [
            sf.group
            for sf in msg.get_structured_fields()
            if sf.group is not None and sf.group.count_field.tag == 552
        ]

        assert len(groups) == 1
        assert [field.tag for field in groups[0].entries[0].fields] == [
            54,
            1154,
            31,
            31344,
            31345,
            32,
            1057,
        ]


class TestAutoDetectIntegration:
    def test_auto_detect_swap_execution(self) -> None:
        msg = _parser().parse(LSEG_FXM_SWAP_EXECUTION, auto_detect_venue=True)
        assert msg.venue == "LSEG FX Matching"
        # FIX 5.0 SP2 standard tags decode via the auto-loaded spec.
        assert msg.get_field(167).value_description == "FX Forward Swap (Near/Far two-leg)"
