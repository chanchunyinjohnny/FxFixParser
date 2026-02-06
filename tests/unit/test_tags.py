"""Unit tests for tag dictionary."""

import pytest

from fxfixparser.core.field import FixFieldDefinition
from fxfixparser.tags.dictionary import TagDictionary
from fxfixparser.tags.fix44 import FIX44_TAGS
from fxfixparser.tags.fx_tags import FX_CUSTOM_TAGS


class TestTagDictionary:
    """Tests for TagDictionary class."""

    def test_empty_dictionary(self) -> None:
        """Test empty dictionary."""
        d = TagDictionary()

        assert d.get(8) is None
        assert d.get_name(8) == "Unknown(8)"
        assert not d.has_tag(8)

    def test_add_and_get(self) -> None:
        """Test adding and retrieving definitions."""
        d = TagDictionary()
        defn = FixFieldDefinition(tag=55, name="Symbol", field_type="STRING")
        d.add(defn)

        assert d.has_tag(55)
        assert d.get(55) == defn
        assert d.get_name(55) == "Symbol"

    def test_all_tags(self) -> None:
        """Test getting all tag numbers."""
        d = TagDictionary()
        d.add(FixFieldDefinition(tag=8, name="BeginString"))
        d.add(FixFieldDefinition(tag=35, name="MsgType"))

        tags = d.all_tags()
        assert 8 in tags
        assert 35 in tags

    def test_merge_dictionaries(self) -> None:
        """Test merging two dictionaries."""
        d1 = TagDictionary()
        d1.add(FixFieldDefinition(tag=8, name="BeginString"))

        d2 = TagDictionary()
        d2.add(FixFieldDefinition(tag=35, name="MsgType"))

        d1.merge(d2)

        assert d1.has_tag(8)
        assert d1.has_tag(35)

    def test_default_dictionary(self, tag_dictionary: TagDictionary) -> None:
        """Test default dictionary contains standard tags."""
        # Check common FIX 4.4 tags
        assert tag_dictionary.has_tag(8)  # BeginString
        assert tag_dictionary.has_tag(9)  # BodyLength
        assert tag_dictionary.has_tag(35)  # MsgType
        assert tag_dictionary.has_tag(10)  # CheckSum
        assert tag_dictionary.has_tag(55)  # Symbol
        assert tag_dictionary.has_tag(54)  # Side

    def test_tag_names(self, tag_dictionary: TagDictionary) -> None:
        """Test tag name resolution."""
        assert tag_dictionary.get_name(8) == "BeginString"
        assert tag_dictionary.get_name(35) == "MsgType"
        assert tag_dictionary.get_name(55) == "Symbol"

    def test_enumerated_values(self, tag_dictionary: TagDictionary) -> None:
        """Test enumerated value descriptions."""
        side_defn = tag_dictionary.get(54)
        assert side_defn is not None
        assert side_defn.get_value_description("1") == "Buy"
        assert side_defn.get_value_description("2") == "Sell"

        msg_type_defn = tag_dictionary.get(35)
        assert msg_type_defn is not None
        assert msg_type_defn.get_value_description("8") == "ExecutionReport"
        assert msg_type_defn.get_value_description("D") == "NewOrderSingle"


class TestFIX44Tags:
    """Tests for FIX 4.4 tag definitions."""

    def test_fix44_tags_not_empty(self) -> None:
        """Test FIX 4.4 tags list is not empty."""
        assert len(FIX44_TAGS) > 0

    def test_required_header_tags(self) -> None:
        """Test required header tags are defined."""
        tag_numbers = {t.tag for t in FIX44_TAGS}

        assert 8 in tag_numbers  # BeginString
        assert 9 in tag_numbers  # BodyLength
        assert 35 in tag_numbers  # MsgType
        assert 49 in tag_numbers  # SenderCompID
        assert 56 in tag_numbers  # TargetCompID

    def test_trailer_tag(self) -> None:
        """Test trailer tag is defined."""
        tag_numbers = {t.tag for t in FIX44_TAGS}
        assert 10 in tag_numbers  # CheckSum


class TestFXCustomTags:
    """Tests for FX-specific custom tags."""

    def test_fx_tags_not_empty(self) -> None:
        """Test FX custom tags list is not empty."""
        assert len(FX_CUSTOM_TAGS) > 0

    def test_options_tags(self) -> None:
        """Test options-related tags are defined."""
        tag_numbers = {t.tag for t in FX_CUSTOM_TAGS}

        assert 201 in tag_numbers  # PutOrCall
        assert 202 in tag_numbers  # StrikePrice

    def test_forward_md_entry_tags(self) -> None:
        """Test forward market data entry tags 1026/1027 are defined."""
        tag_numbers = {t.tag: t for t in FX_CUSTOM_TAGS}

        assert 1026 in tag_numbers
        assert tag_numbers[1026].name == "MDEntrySpotRate"
        assert tag_numbers[1026].field_type == "PRICE"

        assert 1027 in tag_numbers
        assert tag_numbers[1027].name == "MDEntryForwardPoints"
        assert tag_numbers[1027].field_type == "PRICEOFFSET"


class TestSmartTradeVendorTags:
    """Tests for Smart Trade (LiquidityFX) vendor-specific tags."""

    def test_smart_trade_custom_tags_not_empty(self) -> None:
        """Test Smart Trade handler has custom tags defined."""
        from fxfixparser.venues.smart_trade import SmartTradeHandler

        handler = SmartTradeHandler()
        assert len(handler.custom_tags) > 0

    def test_8xxx_mass_quote_entry_ids(self) -> None:
        """Test 8000-8001 MassQuote entry ID tags per LFX spec."""
        from fxfixparser.venues.smart_trade import SmartTradeHandler

        handler = SmartTradeHandler()
        tags_by_number = {t.tag: t for t in handler.custom_tags}

        # 8000 - BidEntryID
        assert 8000 in tags_by_number
        assert tags_by_number[8000].name == "BidEntryID"
        assert tags_by_number[8000].field_type == "STRING"

        # 8001 - OfferEntryID
        assert 8001 in tags_by_number
        assert tags_by_number[8001].name == "OfferEntryID"
        assert tags_by_number[8001].field_type == "STRING"

    def test_8004_far_leg_tenor(self) -> None:
        """Test 8004 SettlType2 (Far Leg Tenor) tag per LFX spec."""
        from fxfixparser.venues.smart_trade import SmartTradeHandler
        from fxfixparser.tags.fx_tags import LFX_TENOR_VALUES

        handler = SmartTradeHandler()
        tags_by_number = {t.tag: t for t in handler.custom_tags}

        assert 8004 in tags_by_number
        tag = tags_by_number[8004]
        assert tag.name == "SettlType2"
        assert tag.field_type == "STRING"

        # Verify tenor values are from LFX_TENOR_VALUES
        assert tag.valid_values is not None
        assert "SPOT" in tag.valid_values
        assert "TOM" in tag.valid_values
        assert "M1" in tag.valid_values  # 1 Month
        assert "Y1" in tag.valid_values  # 1 Year

    def test_8xxx_spot_rates(self) -> None:
        """Test 8011-8012 spot rate tags for far leg per LFX spec."""
        from fxfixparser.venues.smart_trade import SmartTradeHandler

        handler = SmartTradeHandler()
        tags_by_number = {t.tag: t for t in handler.custom_tags}

        # 8011 - BidSpotRate2 (far leg bid spot rate)
        assert 8011 in tags_by_number
        assert tags_by_number[8011].name == "BidSpotRate2"
        assert tags_by_number[8011].field_type == "PRICE"

        # 8012 - OfferSpotRate2 (far leg offer spot rate)
        assert 8012 in tags_by_number
        assert tags_by_number[8012].name == "OfferSpotRate2"
        assert tags_by_number[8012].field_type == "PRICE"

    def test_8xxx_sizes(self) -> None:
        """Test 8013-8014 size tags for far leg per LFX spec."""
        from fxfixparser.venues.smart_trade import SmartTradeHandler

        handler = SmartTradeHandler()
        tags_by_number = {t.tag: t for t in handler.custom_tags}

        # 8013 - BidSize2
        assert 8013 in tags_by_number
        assert tags_by_number[8013].name == "BidSize2"
        assert tags_by_number[8013].field_type == "QTY"

        # 8014 - OfferSize2
        assert 8014 in tags_by_number
        assert tags_by_number[8014].name == "OfferSize2"
        assert tags_by_number[8014].field_type == "QTY"

    def test_8xxx_settlement_dates(self) -> None:
        """Test 8015-8018 settlement date tags per LFX spec."""
        from fxfixparser.venues.smart_trade import SmartTradeHandler

        handler = SmartTradeHandler()
        tags_by_number = {t.tag: t for t in handler.custom_tags}

        # 8015 - BidSettlDate (near leg)
        assert 8015 in tags_by_number
        assert tags_by_number[8015].name == "BidSettlDate"
        assert tags_by_number[8015].field_type == "LOCALMKTDATE"

        # 8016 - BidSettlDate2 (far leg)
        assert 8016 in tags_by_number
        assert tags_by_number[8016].name == "BidSettlDate2"
        assert tags_by_number[8016].field_type == "LOCALMKTDATE"

        # 8017 - OfferSettlDate (near leg)
        assert 8017 in tags_by_number
        assert tags_by_number[8017].name == "OfferSettlDate"
        assert tags_by_number[8017].field_type == "LOCALMKTDATE"

        # 8018 - OfferSettlDate2 (far leg)
        assert 8018 in tags_by_number
        assert tags_by_number[8018].name == "OfferSettlDate2"
        assert tags_by_number[8018].field_type == "LOCALMKTDATE"

    def test_8xxx_all_in_prices(self) -> None:
        """Test 8019-8020 all-in price tags for far leg per LFX spec."""
        from fxfixparser.venues.smart_trade import SmartTradeHandler

        handler = SmartTradeHandler()
        tags_by_number = {t.tag: t for t in handler.custom_tags}

        # 8019 - BidPx2 (far leg all-in bid price)
        assert 8019 in tags_by_number
        assert tags_by_number[8019].name == "BidPx2"
        assert tags_by_number[8019].field_type == "PRICE"

        # 8020 - OfferPx2 (far leg all-in offer price)
        assert 8020 in tags_by_number
        assert tags_by_number[8020].name == "OfferPx2"
        assert tags_by_number[8020].field_type == "PRICE"

    def test_8xxx_currencies(self) -> None:
        """Test 8021-8022 currency tags per LFX spec."""
        from fxfixparser.venues.smart_trade import SmartTradeHandler

        handler = SmartTradeHandler()
        tags_by_number = {t.tag: t for t in handler.custom_tags}

        # 8021 - BidCurrency
        assert 8021 in tags_by_number
        assert tags_by_number[8021].name == "BidCurrency"
        assert tags_by_number[8021].field_type == "CURRENCY"

        # 8022 - OfferCurrency
        assert 8022 in tags_by_number
        assert tags_by_number[8022].name == "OfferCurrency"
        assert tags_by_number[8022].field_type == "CURRENCY"

    def test_swap_points_tags(self) -> None:
        """Test 1065-1066 swap points tags per LFX spec."""
        from fxfixparser.venues.smart_trade import SmartTradeHandler

        handler = SmartTradeHandler()
        tags_by_number = {t.tag: t for t in handler.custom_tags}

        # 1065 - BidSwapPoints
        assert 1065 in tags_by_number
        assert tags_by_number[1065].name == "BidSwapPoints"
        assert tags_by_number[1065].field_type == "PRICEOFFSET"

        # 1066 - OfferSwapPoints
        assert 1066 in tags_by_number
        assert tags_by_number[1066].name == "OfferSwapPoints"
        assert tags_by_number[1066].field_type == "PRICEOFFSET"

    def test_9xxx_market_data_tags(self) -> None:
        """Test 9xxx range market data tags per LFX spec."""
        from fxfixparser.venues.smart_trade import SmartTradeHandler

        handler = SmartTradeHandler()
        tags_by_number = {t.tag: t for t in handler.custom_tags}

        # 9000 - NoRequestedSize
        assert 9000 in tags_by_number
        assert tags_by_number[9000].name == "NoRequestedSize"
        assert tags_by_number[9000].field_type == "NUMINGROUP"

        # 9001 - RequestedSize
        assert 9001 in tags_by_number
        assert tags_by_number[9001].name == "RequestedSize"
        assert tags_by_number[9001].field_type == "QTY"

        # 9122 - MDEntryOrigTime
        assert 9122 in tags_by_number
        assert tags_by_number[9122].name == "MDEntryOrigTime"
        assert tags_by_number[9122].field_type == "UTCTIMEONLY"

    def test_9xxx_execution_report_tags(self) -> None:
        """Test 9xxx execution report tags for swaps per LFX spec."""
        from fxfixparser.venues.smart_trade import SmartTradeHandler

        handler = SmartTradeHandler()
        tags_by_number = {t.tag: t for t in handler.custom_tags}

        # 9044 - MaturityDate2 (NDS far leg fixing date)
        assert 9044 in tags_by_number
        assert tags_by_number[9044].name == "MaturityDate2"

        # 9091 - LastPx2 (swap far leg fill price)
        assert 9091 in tags_by_number
        assert tags_by_number[9091].name == "LastPx2"
        assert tags_by_number[9091].field_type == "PRICE"

        # 9092 - LastQty2 (swap far leg fill quantity)
        assert 9092 in tags_by_number
        assert tags_by_number[9092].name == "LastQty2"
        assert tags_by_number[9092].field_type == "QTY"

        # 9093 - LeavesQty2 (swap far leg open quantity)
        assert 9093 in tags_by_number
        assert tags_by_number[9093].name == "LeavesQty2"

        # 9094 - CumQty2 (swap far leg cumulative filled)
        assert 9094 in tags_by_number
        assert tags_by_number[9094].name == "CumQty2"

        # 9095 - LastSpotRate2 (swap far leg spot rate)
        assert 9095 in tags_by_number
        assert tags_by_number[9095].name == "LastSpotRate2"

    def test_9xxx_fixing_tags(self) -> None:
        """Test 9300-9301 fixing order tags per LFX spec."""
        from fxfixparser.venues.smart_trade import SmartTradeHandler

        handler = SmartTradeHandler()
        tags_by_number = {t.tag: t for t in handler.custom_tags}

        # 9300 - FixingSourceID
        assert 9300 in tags_by_number
        assert tags_by_number[9300].name == "FixingSourceID"
        assert tags_by_number[9300].field_type == "STRING"

        # 9301 - FixingTime
        assert 9301 in tags_by_number
        assert tags_by_number[9301].name == "FixingTime"
        assert tags_by_number[9301].field_type == "UTCTIMESTAMP"

    def test_9400_regulation_type(self) -> None:
        """Test 9400 RegulationType tag with enumerated values per LFX spec."""
        from fxfixparser.venues.smart_trade import SmartTradeHandler

        handler = SmartTradeHandler()
        tags_by_number = {t.tag: t for t in handler.custom_tags}

        assert 9400 in tags_by_number
        tag = tags_by_number[9400]
        assert tag.name == "RegulationType"
        assert tag.field_type == "STRING"

        # Check enumerated values
        assert tag.valid_values is not None
        assert "SEF" in tag.valid_values
        assert "MTF" in tag.valid_values
        assert "XOFF" in tag.valid_values

        # Check value descriptions
        assert "Swap Execution Facility" in tag.get_value_description("SEF")
        assert "Multilateral Trading Facility" in tag.get_value_description("MTF")

    def test_10xxx_uti_tags(self) -> None:
        """Test 10xxx UTI (Unique Trade Identifier) tags per LFX spec."""
        from fxfixparser.venues.smart_trade import SmartTradeHandler

        handler = SmartTradeHandler()
        tags_by_number = {t.tag: t for t in handler.custom_tags}

        # 10002 - UTIPrefix
        assert 10002 in tags_by_number
        assert tags_by_number[10002].name == "UTIPrefix"

        # 10003 - UTI
        assert 10003 in tags_by_number
        assert tags_by_number[10003].name == "UTI"

        # 10011 - IsSEFTrade
        assert 10011 in tags_by_number
        assert tags_by_number[10011].name == "IsSEFTrade"
        assert tags_by_number[10011].field_type == "BOOLEAN"

    def test_11xxx_allocation_tags(self) -> None:
        """Test 11xxx allocation tags per LFX spec."""
        from fxfixparser.venues.smart_trade import SmartTradeHandler

        handler = SmartTradeHandler()
        tags_by_number = {t.tag: t for t in handler.custom_tags}

        # 11001 - RequestType
        assert 11001 in tags_by_number
        assert tags_by_number[11001].name == "RequestType"
        assert tags_by_number[11001].valid_values is not None
        assert "M" in tags_by_number[11001].valid_values

        # 11003 - AllocationID
        assert 11003 in tags_by_number
        assert tags_by_number[11003].name == "AllocationID"

        # 11078 - C_NoAllocs
        assert 11078 in tags_by_number
        assert tags_by_number[11078].name == "C_NoAllocs"
        assert tags_by_number[11078].field_type == "NUMINGROUP"

        # 11079 - C_AllocAccount
        assert 11079 in tags_by_number
        assert tags_by_number[11079].name == "C_AllocAccount"

        # 11080 - C_AllocQty
        assert 11080 in tags_by_number
        assert tags_by_number[11080].name == "C_AllocQty"
        assert tags_by_number[11080].field_type == "QTY"

    def test_11054_alloc_side_enumerated_values(self) -> None:
        """Test 11054 C_AllocSide enumerated values per LFX spec."""
        from fxfixparser.venues.smart_trade import SmartTradeHandler

        handler = SmartTradeHandler()
        tags_by_number = {t.tag: t for t in handler.custom_tags}

        assert 11054 in tags_by_number
        tag = tags_by_number[11054]
        assert tag.name == "C_AllocSide"

        assert tag.valid_values is not None
        assert "B" in tag.valid_values  # AS_DEFINED
        assert "C" in tag.valid_values  # OPPOSITE
        assert "U" in tag.valid_values  # UNDISCLOSED

    def test_lfx_tenor_values_complete(self) -> None:
        """Test LFX_TENOR_VALUES dictionary has all required tenors."""
        from fxfixparser.tags.fx_tags import LFX_TENOR_VALUES

        # Standard tenors from section 11.9 of LFX spec
        # Format: SPOT, TOD, TOM, ONI (overnight), SNX (spot next), TNX (tom next)
        # Weeks: W1, W2, W3
        # Months: M1-M11, M15, M18, M21
        # Years: Y1-Y10, Y15, Y20, Y25, Y30
        required_tenors = [
            "SPOT", "TOM", "TOD", "SNX", "ONI", "TNX",
            "W1", "W2", "W3",
            "M1", "M2", "M3", "M4", "M5", "M6",
            "M7", "M8", "M9", "M10", "M11", "M18",
            "Y1", "Y2", "Y3",
        ]

        for tenor in required_tenors:
            assert tenor in LFX_TENOR_VALUES, f"Missing tenor: {tenor}"

    def test_forward_roll_tag(self) -> None:
        """Test 9011 ClRootOrderID for forward rolls per LFX spec."""
        from fxfixparser.venues.smart_trade import SmartTradeHandler

        handler = SmartTradeHandler()
        tags_by_number = {t.tag: t for t in handler.custom_tags}

        assert 9011 in tags_by_number
        assert tags_by_number[9011].name == "ClRootOrderID"
        assert tags_by_number[9011].field_type == "STRING"


class TestVendorTagParsing:
    """Tests for parsing messages with vendor-specific tags."""

    def test_parse_message_with_8xxx_tags(self) -> None:
        """Test parsing a FIX message containing Smart Trade 8xxx tags."""
        from fxfixparser.core.parser import FixParser, ParserConfig
        from fxfixparser.venues.registry import VenueRegistry

        msg = (
            "8=FIX.4.4|9=250|35=S|49=LFX|56=CLIENT|55=EUR/USD|"
            "8000=BID123|8001=OFF456|8004=M1|"
            "8011=1.0850|8012=1.0855|8013=1000000|8014=1000000|"
            "8015=20240117|8016=20240217|8017=20240117|8018=20240217|"
            "8019=1.0900|8020=1.0905|8021=EUR|8022=EUR|10=123|"
        )

        parser = FixParser(config=ParserConfig(strict_checksum=False))
        message = parser.parse(msg)

        venue_registry = VenueRegistry.default()
        handler = venue_registry.get_by_sender_id("LFX")
        assert handler is not None
        message = handler.enhance_message(message)

        # Verify 8xxx tags are parsed with correct names
        assert message.get_field(8000).name == "BidEntryID"
        assert message.get_field(8000).raw_value == "BID123"

        assert message.get_field(8001).name == "OfferEntryID"
        assert message.get_field(8001).raw_value == "OFF456"

        assert message.get_field(8004).name == "SettlType2"
        assert message.get_field(8004).raw_value == "M1"

        assert message.get_field(8011).name == "BidSpotRate2"
        assert message.get_field(8019).name == "BidPx2"
        assert message.get_field(8021).name == "BidCurrency"

    def test_parse_message_with_9xxx_tags(self) -> None:
        """Test parsing a FIX message containing Smart Trade 9xxx tags."""
        from fxfixparser.core.parser import FixParser, ParserConfig
        from fxfixparser.venues.registry import VenueRegistry

        msg = (
            "8=FIX.4.4|9=200|35=8|49=LFX_CORE|56=CLIENT|55=EUR/USD|"
            "9091=1.0900|9092=500000|9093=500000|9094=500000|9095=1.0850|"
            "9300=WMR|9301=20240115-16:00:00.000|9400=MTF|10=123|"
        )

        parser = FixParser(config=ParserConfig(strict_checksum=False))
        message = parser.parse(msg)

        venue_registry = VenueRegistry.default()
        handler = venue_registry.get_by_sender_id("LFX_CORE")
        assert handler is not None
        message = handler.enhance_message(message)

        # Verify 9xxx tags are parsed with correct names
        assert message.get_field(9091).name == "LastPx2"
        assert message.get_field(9092).name == "LastQty2"
        assert message.get_field(9300).name == "FixingSourceID"
        assert message.get_field(9301).name == "FixingTime"
        assert message.get_field(9400).name == "RegulationType"
        assert message.get_field(9400).raw_value == "MTF"

    def test_parse_message_with_allocation_tags(self) -> None:
        """Test parsing a FIX message containing Smart Trade 11xxx allocation tags."""
        from fxfixparser.core.parser import FixParser, ParserConfig
        from fxfixparser.venues.registry import VenueRegistry

        msg = (
            "8=FIX.4.4|9=200|35=R|49=SMARTTRADE|56=CLIENT|55=EUR/USD|"
            "11001=M|11003=ALLOC001|11078=2|"
            "11079=ACCT1|11080=500000|11054=B|"
            "11079=ACCT2|11080=500000|11054=C|10=123|"
        )

        parser = FixParser(config=ParserConfig(strict_checksum=False))
        message = parser.parse(msg)

        venue_registry = VenueRegistry.default()
        handler = venue_registry.get_by_sender_id("SMARTTRADE")
        assert handler is not None
        message = handler.enhance_message(message)

        # Verify 11xxx tags are parsed with correct names
        assert message.get_field(11001).name == "RequestType"
        assert message.get_field(11001).raw_value == "M"
        assert message.get_field(11003).name == "AllocationID"
        assert message.get_field(11078).name == "C_NoAllocs"

    def test_vendor_tag_to_human_readable(self) -> None:
        """Test vendor-specific tags render correctly in human readable format."""
        from fxfixparser.core.parser import FixParser, ParserConfig
        from fxfixparser.venues.registry import VenueRegistry

        msg = (
            "8=FIX.4.4|9=100|35=S|49=LFX|56=CLIENT|55=EUR/USD|"
            "8004=SPOT|8021=EUR|9400=SEF|10=123|"
        )

        parser = FixParser(config=ParserConfig(strict_checksum=False))
        message = parser.parse(msg)

        venue_registry = VenueRegistry.default()
        handler = venue_registry.get_by_sender_id("LFX")
        message = handler.enhance_message(message)

        output = message.to_human_readable()

        # Check vendor tags appear with proper names
        assert "SettlType2 (8004)" in output
        assert "BidCurrency (8021)" in output
        assert "RegulationType (9400)" in output

    def test_vendor_tag_to_dict(self) -> None:
        """Test vendor-specific tags are included in dict output."""
        from fxfixparser.core.parser import FixParser, ParserConfig
        from fxfixparser.venues.registry import VenueRegistry

        msg = (
            "8=FIX.4.4|9=100|35=S|49=LFX|56=CLIENT|55=EUR/USD|"
            "8000=BID123|8004=M1|10=123|"
        )

        parser = FixParser(config=ParserConfig(strict_checksum=False))
        message = parser.parse(msg)

        venue_registry = VenueRegistry.default()
        handler = venue_registry.get_by_sender_id("LFX")
        message = handler.enhance_message(message)

        d = message.to_dict()

        # Find vendor-specific tags in the output
        tag_8000 = next((f for f in d["fields"] if f["tag"] == 8000), None)
        assert tag_8000 is not None
        assert tag_8000["name"] == "BidEntryID"
        assert tag_8000["value"] == "BID123"

        tag_8004 = next((f for f in d["fields"] if f["tag"] == 8004), None)
        assert tag_8004 is not None
        assert tag_8004["name"] == "SettlType2"
        assert tag_8004["value"] == "M1"
