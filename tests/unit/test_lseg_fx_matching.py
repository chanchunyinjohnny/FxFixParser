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

    def test_venue_scoped_overrides_defined(self) -> None:
        d = {t.tag: t for t in LSEGFXMatchingHandler().custom_tags}
        assert d[1097].name == "LastLimitAmt"
        assert d[1149].name == "LimitRemainingAmt"
        assert d[1418].name == "LegCalculatedCcyLastQty"
        assert d[1056].name == "CalculatedCcyLastQty"

    def test_admin_udfs_labelled(self) -> None:
        d = {t.tag: t for t in LSEGFXMatchingHandler().custom_tags}
        assert d[20005].valid_values["0"] == "Success"
        assert d[20010].valid_values["1"] == "Enabled"


class TestCustomTagsDecode:
    def test_overrides_decode_under_lseg_venue(self) -> None:
        body = (
            "8=FIXT.1.1|9=0|35=AE|49=TR MATCHING|56=AAAA017752|1128=9|"
            "167=FXSPOT|1097=5|1149=49|10=000|"
        )
        msg = _parser().parse(body, venue="LSEG FX Matching")
        assert msg.get_field(1097).name == "LastLimitAmt"
        assert msg.get_field(1149).name == "LimitRemainingAmt"

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

    def test_legref_accepts_positional_and_string(self) -> None:
        near_str = self._field("8=FIXT.1.1|9=0|35=8|49=TR MATCHING|654=Near|10=000|", 654)
        near_pos = self._field("8=FIXT.1.1|9=0|35=AE|49=TR MATCHING|654=1|10=000|", 654)
        assert "Near" in near_str.value_description
        assert "Near" in near_pos.value_description

    def test_custom_msgtype_u3_labelled(self) -> None:
        f = self._field("8=FIXT.1.1|9=0|35=U3|49=TR MATCHING|10=000|", 35)
        assert f.value_description is not None
        assert "PBC" in f.value_description


class TestTagOverrideVenueIsolation:
    """The 1097/1149/1418 reuse must be venue-scoped, not global."""

    def _name(self, raw: str, venue, tag: int) -> str:
        return _parser().parse(raw, venue=venue).get_field(tag).name

    def test_1149_lseg_vs_default(self) -> None:
        raw = "8=FIXT.1.1|9=0|35=AE|49=TR MATCHING|56=AAAA017752|1128=9|1149=49|10=000|"
        # Under LSEG the tag is the MAPI credit field...
        assert self._name(raw, "LSEG FX Matching", 1149) == "LimitRemainingAmt"
        # ...but under no venue it keeps its standard FIX 5.0 SP2 meaning.
        assert self._name(raw, None, 1149) == "HighLimitPrice"

    def test_1418_lseg_vs_default(self) -> None:
        raw = "8=FIXT.1.1|9=0|35=AE|49=TR MATCHING|56=AAAA017752|1128=9|1418=1|10=000|"
        assert self._name(raw, "LSEG FX Matching", 1418) == "LegCalculatedCcyLastQty"
        assert self._name(raw, None, 1418) == "LegLastQty"


class TestExtractTrade:
    def test_spot_execution(self) -> None:
        msg = _parser().parse(LSEG_FXM_SPOT_EXECUTION, venue="LSEG FX Matching")
        trade = LSEGFXMatchingHandler().extract_trade(msg)
        assert trade.symbol == "EUR/USD"
        assert trade.price == pytest.approx(1.085)
        assert trade.is_swap is False
        assert trade.exec_id == "SX1"

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
        msg = _parser().parse(LSEG_FXM_SWAP_EXECUTION, venue="LSEG FX Matching")
        trade = LSEGFXMatchingHandler().extract_trade(msg)
        assert trade.is_swap is True
        assert trade.symbol == "EUR/USD"
        assert trade.settlement_date == "20260606"
        assert trade.far_settlement_date == "20260908"
        assert trade.near_leg_price == pytest.approx(1.084)
        assert trade.far_leg_price == pytest.approx(1.085)
        assert trade.swap_points == pytest.approx(0.001)

    def test_swap_spot_rate_falls_back_to_1056(self) -> None:
        # LSEG_FXM_SWAP_EXECUTION has no LastSpotRate(194); 1056=1.08380.
        msg = _parser().parse(LSEG_FXM_SWAP_EXECUTION, venue="LSEG FX Matching")
        trade = LSEGFXMatchingHandler().extract_trade(msg)
        assert trade.spot_rate == pytest.approx(1.0838)

    def test_swap_tcr_prefers_explicit_194(self) -> None:
        # LSEG_FXM_SWAP_TRADE_CAPTURE carries explicit 194; 1056 must not shadow.
        msg = _parser().parse(LSEG_FXM_SWAP_TRADE_CAPTURE, venue="LSEG FX Matching")
        trade = LSEGFXMatchingHandler().extract_trade(msg)
        assert trade.spot_rate == pytest.approx(1.0838)


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
    def test_root_parties_group_structured(self) -> None:
        msg = _parser().parse(LSEG_FXM_SPOT_TRADE_CAPTURE, venue="LSEG FX Matching")
        groups = [
            sf.group
            for sf in msg.get_structured_fields()
            if sf.group is not None and sf.group.count_field.tag == 1116
        ]
        assert len(groups) == 1
        assert groups[0].count == 2
        assert len(groups[0].entries) == 2

    def test_settl_details_group_structured(self) -> None:
        msg = _parser().parse(LSEG_FXM_SPOT_TRADE_CAPTURE, venue="LSEG FX Matching")
        groups = [
            sf.group
            for sf in msg.get_structured_fields()
            if sf.group is not None and sf.group.count_field.tag == 1158
        ]
        assert len(groups) == 1
        assert groups[0].count == 1

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
