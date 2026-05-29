"""Unit tests for the SGX Titan OTC venue handler."""

import pytest

from fxfixparser.core.field import FixField
from fxfixparser.core.message import FixMessage
from fxfixparser.core.parser import FixParser, ParserConfig
from fxfixparser.venues.sgx_titan_otc import SGXTitanOTCHandler, sgx_product_name


class TestHandlerIdentity:
    def test_name(self) -> None:
        assert SGXTitanOTCHandler().name == "SGX Titan OTC"

    def test_sender_comp_ids_includes_titanotc(self) -> None:
        # TITANOTC is the venue-side CompID confirmed from PDF samples.
        ids = SGXTitanOTCHandler().sender_comp_ids
        assert "TITANOTC" in ids

    def test_matches_sender_case_insensitive(self) -> None:
        handler = SGXTitanOTCHandler()
        assert handler.matches_sender("titanotc") is True
        assert handler.matches_sender("TITANOTC") is True
        assert handler.matches_sender("UNKNOWN") is False
        assert handler.matches_sender(None) is False

    def test_enhance_message_sets_venue(self) -> None:
        msg = FixMessage()
        enhanced = SGXTitanOTCHandler().enhance_message(msg)
        assert enhanced.venue == "SGX Titan OTC"


class TestProductCodeLookup:
    @pytest.mark.parametrize(
        "code,expected",
        [
            ("KU", "KRW/USD FX Futures"),
            ("UC", "USD/CNH FX Futures"),
            ("US", "USD/SGD FX Futures"),
            ("KUTM", "KRW/USD FlexC FX Futures"),
            ("UCTM", "USD/CNH FlexC FX Futures"),
            ("IDR", "IDR/USD FX Futures"),
        ],
    )
    def test_known_codes_resolve(self, code: str, expected: str) -> None:
        assert sgx_product_name(code) == expected

    def test_unknown_code_returns_none(self) -> None:
        assert sgx_product_name("ZZZ") is None
        assert sgx_product_name("") is None
        assert sgx_product_name(None) is None


class TestCustomTagDefinitions:
    def test_tag_1300_market_segment_id_includes_fx_value(self) -> None:
        handler = SGXTitanOTCHandler()
        defn = next(t for t in handler.custom_tags if t.tag == 1300)
        assert defn.name == "MarketSegmentID"
        assert defn.valid_values["FX"] == "FX asset class"

    def test_tag_1227_product_complex_defined(self) -> None:
        handler = SGXTitanOTCHandler()
        defn = next(t for t in handler.custom_tags if t.tag == 1227)
        assert defn.name == "ProductComplex"

    def test_tag_1306_price_limit_type_values(self) -> None:
        handler = SGXTitanOTCHandler()
        defn = next(t for t in handler.custom_tags if t.tag == 1306)
        assert defn.name == "PriceLimitType"
        assert defn.valid_values["0"] == "No limit"
        assert defn.valid_values["1"] == "Hard limit"
        assert defn.valid_values["2"] == "Soft limit"

    def test_tag_2343_risk_limit_check_status_values(self) -> None:
        handler = SGXTitanOTCHandler()
        defn = next(t for t in handler.custom_tags if t.tag == 2343)
        assert defn.valid_values["0"] == "Accepted"
        assert defn.valid_values["1"] == "Rejected"

    def test_tag_1057_aggressor_indicator_boolean(self) -> None:
        handler = SGXTitanOTCHandler()
        defn = next(t for t in handler.custom_tags if t.tag == 1057)
        assert defn.name == "AggressorIndicator"
        assert defn.field_type == "BOOLEAN"

    def test_all_required_tags_present(self) -> None:
        handler = SGXTitanOTCHandler()
        defined = {t.tag for t in handler.custom_tags}
        required = {
            1300,
            1227,
            1151,
            1306,
            1148,
            1149,
            1150,
            1057,
            1003,
            1005,
            1139,
            1310,
            2343,
            2344,
            1461,
            1462,
            1463,
            1464,
            1625,
            1626,
            1627,
            1418,
            1427,
            552,
        }
        missing = required - defined
        assert not missing, f"Missing tag definitions: {sorted(missing)}"


def _make_message(tag_values: dict[int, str]) -> FixMessage:
    """Build a FixMessage with the given raw tag/value pairs."""
    return FixMessage(fields=[FixField(tag=t, raw_value=v) for t, v in tag_values.items()])


class TestEnhanceMessage:
    def test_sets_venue_name(self) -> None:
        handler = SGXTitanOTCHandler()
        msg = _make_message({1300: "FX", 48: "KU"})
        enhanced = handler.enhance_message(msg)
        assert enhanced.venue == "SGX Titan OTC"

    def test_known_fx_product_code_populates_venue_extras(self) -> None:
        handler = SGXTitanOTCHandler()
        msg = _make_message({1300: "FX", 48: "KU"})
        enhanced = handler.enhance_message(msg)
        assert enhanced.venue_extras["product_name"] == "KRW/USD FX Futures"

    def test_flexc_product_code_populates_venue_extras(self) -> None:
        handler = SGXTitanOTCHandler()
        msg = _make_message({1300: "FX", 48: "KUTM"})
        enhanced = handler.enhance_message(msg)
        assert enhanced.venue_extras["product_name"] == "KRW/USD FlexC FX Futures"

    def test_unknown_code_leaves_venue_extras_empty(self) -> None:
        handler = SGXTitanOTCHandler()
        msg = _make_message({1300: "FX", 48: "ZZZ"})
        enhanced = handler.enhance_message(msg)
        assert "product_name" not in enhanced.venue_extras

    def test_non_fx_market_segment_skips_enrichment(self) -> None:
        # Even if 48=KU coincidentally matches an FX code, we only enrich
        # when 1300=FX so we don't shadow other asset classes.
        handler = SGXTitanOTCHandler()
        msg = _make_message({1300: "CO", 48: "KU"})
        enhanced = handler.enhance_message(msg)
        assert "product_name" not in enhanced.venue_extras

    def test_no_security_id_skips_enrichment(self) -> None:
        handler = SGXTitanOTCHandler()
        msg = _make_message({1300: "FX"})
        enhanced = handler.enhance_message(msg)
        assert "product_name" not in enhanced.venue_extras


class TestExtractTrade:
    def test_trade_capture_report_uses_sgx_trade_identifiers(self) -> None:
        msg = _make_message(
            {
                35: "AE",
                55: "[N/A]",
                48: "KU",
                571: "TR0001",
                1003: "TID0001",
                1005: "SIDE0001",
                54: "1",
                32: "10",
                31: "1234.56",
                75: "20170828",
            }
        )

        trade = SGXTitanOTCHandler().extract_trade(msg)

        assert trade.order_id == "TR0001"
        assert trade.exec_id == "TID0001"

    def test_trade_capture_report_falls_back_to_side_trade_report_id(self) -> None:
        msg = _make_message(
            {
                35: "AE",
                55: "[N/A]",
                48: "KU",
                571: "TR0001",
                1005: "SIDE0001",
                54: "1",
                32: "10",
                31: "1234.56",
            }
        )

        trade = SGXTitanOTCHandler().extract_trade(msg)

        assert trade.order_id == "TR0001"
        assert trade.exec_id == "SIDE0001"


class TestNoSidesRepeatingGroup:
    def test_two_sided_trade_capture_report_is_structured(self) -> None:
        raw = (
            "8=FIXT.1.1|9=300|35=AE|34=42|49=TITANOTC|52=20170828-09:14:37.226|"
            "56=S020|571=TR0001|487=0|"
            "55=[N/A]|48=KU|22=M|107=KRW_USD FX Futures|167=FUT|200=202506|"
            "1300=FX|1227=SGX KRW/USD FX FUTURES|"
            "552=2|54=1|1005=BUY_SIDE|32=10|31=1234.56|"
            "54=2|1005=SELL_SIDE|32=10|31=1234.56|"
            "75=20170828|10=000|"
        )
        parser = FixParser(config=ParserConfig(strict_checksum=False))

        msg = parser.parse(raw, auto_detect_venue=True)
        groups = [
            sf.group
            for sf in msg.get_structured_fields()
            if sf.group is not None and sf.group.count_field.tag == 552
        ]

        assert len(groups) == 1
        group = groups[0]
        assert group.count == 2
        assert len(group.entries) == 2
        assert [field.tag for field in group.entries[0].fields] == [54, 1005, 32, 31]
        assert [field.tag for field in group.entries[1].fields] == [54, 1005, 32, 31]


class TestRegistryIntegration:
    def test_default_registry_contains_sgx(self) -> None:
        from fxfixparser.venues.registry import VenueRegistry

        registry = VenueRegistry.default()
        assert registry.get("SGX Titan OTC") is not None

    def test_detect_by_target_comp_id_titanotc(self) -> None:
        from fxfixparser.venues.registry import VenueRegistry

        registry = VenueRegistry.default()
        msg = _make_message({49: "S020", 56: "TITANOTC"})
        handler = registry.detect_from_message(msg)
        assert handler is not None
        assert handler.name == "SGX Titan OTC"

    def test_detect_by_sender_comp_id_titanotc(self) -> None:
        from fxfixparser.venues.registry import VenueRegistry

        registry = VenueRegistry.default()
        msg = _make_message({49: "TITANOTC", 56: "S020"})
        handler = registry.detect_from_message(msg)
        assert handler is not None
        assert handler.name == "SGX Titan OTC"


class TestTag1300VenueIsolation:
    """Tag 1300 must decode per-venue, not globally.

    SGX defines 1300=FX (asset class). Bloomberg DOR defines 1300 with
    its own venue codes (BETP/BMTF/BSEF/...). Parsing the same wire
    value under different venue handlers must yield different
    descriptions, proving the per-venue dictionary overlay in
    parser.py::_get_dictionary_for_venue isolates them.
    """

    def test_1300_FX_decodes_under_sgx(self) -> None:
        body = (
            "8=FIXT.1.1\x019=00\x0135=AE\x0149=TITANOTC\x0156=S020\x01"
            "1300=FX\x0148=KU\x0110=000\x01"
        )
        parser = FixParser(config=ParserConfig(strict_checksum=False, strict_body_length=False))
        msg = parser.parse(body, venue="SGX Titan OTC")
        field = msg.get_field(1300)
        assert field is not None
        assert field.value_description == "FX asset class"

    def test_1300_BETP_decodes_under_bloomberg(self) -> None:
        body = (
            "8=FIX.4.4\x019=00\x0135=AE\x0149=BLOOMBERG_DOR\x0156=CLIENT\x01"
            "1300=BETP\x0110=000\x01"
        )
        parser = FixParser(config=ParserConfig(strict_checksum=False, strict_body_length=False))
        msg = parser.parse(body, venue="Bloomberg DOR")
        field = msg.get_field(1300)
        assert field is not None
        assert field.value_description == "Electronic Trading Platform"
