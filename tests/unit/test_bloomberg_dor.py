"""Unit tests for Bloomberg DOR venue handler."""

import pytest

from fxfixparser.core.parser import FixParser, ParserConfig
from fxfixparser.venues.bloomberg_dor import BloombergDORHandler
from tests.fixtures.sample_messages import (
    BLOOMBERG_DOR_ALGO_EXEC,
    BLOOMBERG_DOR_FORWARD_EXEC,
    BLOOMBERG_DOR_SPOT_EXEC,
    BLOOMBERG_DOR_SPOT_QUOTE,
    BLOOMBERG_DOR_SPOT_RFQ,
    BLOOMBERG_DOR_SPOT_RFQ_REJECT,
    BLOOMBERG_DOR_SWAP_EXEC,
)


class TestBloombergDORBasic:
    """Tests for Bloomberg DOR handler basic properties."""

    def test_handler_name(self) -> None:
        """Handler name should be 'Bloomberg DOR'."""
        handler = BloombergDORHandler()
        assert handler.name == "Bloomberg DOR"

    def test_sender_comp_ids(self) -> None:
        """Handler should include key Bloomberg DOR sender IDs."""
        handler = BloombergDORHandler()
        ids = handler.sender_comp_ids

        assert "BLOOMBERG_DOR" in ids
        assert "BBGDOR" in ids
        assert "DOR" in ids
        assert "FXOM" in ids
        assert "ORP" in ids

    def test_matches_sender(self) -> None:
        """matches_sender should be case-insensitive and reject non-DOR IDs."""
        handler = BloombergDORHandler()

        # Positive cases — exact and case-insensitive
        assert handler.matches_sender("BLOOMBERG_DOR")
        assert handler.matches_sender("bloomberg_dor")
        assert handler.matches_sender("DOR")
        assert handler.matches_sender("dor")
        assert handler.matches_sender("FXOM")
        assert handler.matches_sender("fxom")
        assert handler.matches_sender("ORP")
        assert handler.matches_sender("orp")
        assert handler.matches_sender("BBGDOR")
        assert handler.matches_sender("bbgdor")

        # Negative cases
        assert not handler.matches_sender("FXGO")
        assert not handler.matches_sender("SMARTTRADE")
        assert not handler.matches_sender("360T")
        assert not handler.matches_sender("")
        assert not handler.matches_sender(None)


class TestBloombergDORCustomTags:
    """Tests for Bloomberg DOR custom tag definitions."""

    def test_custom_tags_returns_definitions(self) -> None:
        """Handler should return custom tag definitions."""
        handler = BloombergDORHandler()
        tags = handler.custom_tags
        assert len(tags) > 0

    def test_custom_tags_include_bloomberg_specific(self) -> None:
        """Bloomberg-specific tags should be present."""
        handler = BloombergDORHandler()
        tags_by_number = {t.tag: t for t in handler.custom_tags}

        # Tag 22913 — LastMktSpotRate
        assert 22913 in tags_by_number
        assert tags_by_number[22913].name == "LastMktSpotRate"

        # Tag 22858 — AlgoStrategyID
        assert 22858 in tags_by_number
        assert tags_by_number[22858].name == "AlgoStrategyID"

        # Tag 6215 — Tenor
        assert 6215 in tags_by_number
        assert tags_by_number[6215].name == "Tenor"

    def test_custom_tags_have_descriptions(self) -> None:
        """Custom tags should have meaningful descriptions."""
        handler = BloombergDORHandler()
        tags_by_number = {t.tag: t for t in handler.custom_tags}

        tag_22913 = tags_by_number[22913]
        assert "spot rate" in tag_22913.description.lower()

    def test_custom_tags_have_enumerations(self) -> None:
        """Tags with valid_values should have correct enumerations."""
        handler = BloombergDORHandler()
        tags_by_number = {t.tag: t for t in handler.custom_tags}

        # ManualTicket (22923) has valid_values
        assert 22923 in tags_by_number
        manual_ticket = tags_by_number[22923]
        assert "0" in manual_ticket.valid_values
        assert "1" in manual_ticket.valid_values

        # OffshoreIndicator (2795) has valid_values
        assert 2795 in tags_by_number
        offshore = tags_by_number[2795]
        assert "0" in offshore.valid_values
        assert "1" in offshore.valid_values

        # MarketSegmentID (1300) — Bloomberg ORP execution-facility enums
        assert 1300 in tags_by_number
        market_segment = tags_by_number[1300]
        assert market_segment.name == "MarketSegmentID"
        assert market_segment.valid_values["BTBS"] == "Bloomberg Trade Book Singapore"
        assert "BSEF" in market_segment.valid_values
        assert "XOFF" in market_segment.valid_values

    def test_fixt_session_tags_resolve(self) -> None:
        """FIXT 1.1 session tags 1128/1129/1156 resolve via the shared dictionary."""
        message_str = (
            "8=FIXT.1.1|9=301|35=R|34=4|49=ORP_BCQT_B|52=20260522-08:53:49.606|"
            "56=BLPORPBETA|115=DOR|128=DOR|1128=9|1129=1.0|1156=20|"
            "131=1507426270445703168|146=1|55=EUR/USD|460=4|167=FXSPOT|38=1000000|"
            "64=20260522|15=EUR|60=20260522-16:53:49.500|453=3|448=DOR1|447=D|452=1|"
            "448=DOR2|447=D|452=1|448=29618590|447=D|452=11|1300=BTBS|10=174|"
        )
        parser = FixParser(config=ParserConfig(strict_checksum=False))
        message = parser.parse(message_str, venue="Bloomberg DOR")

        appl_ver = message.get_field(1128)
        assert appl_ver is not None
        assert appl_ver.name == "ApplVerID"
        assert appl_ver.value_description == "FIX 5.0 SP2"

        cstm = message.get_field(1129)
        assert cstm is not None
        assert cstm.name == "CstmApplVerID"

        ext = message.get_field(1156)
        assert ext is not None
        assert ext.name == "ApplExtID"

    def test_tag_1300_resolves_in_bloomberg_dor_message(self) -> None:
        """Tag 1300 in a Bloomberg ORP message resolves to MarketSegmentID with enum description."""
        message_str = (
            "8=FIXT.1.1|9=301|35=R|34=4|49=ORP_BCQT_B|52=20260522-08:53:49.606|"
            "56=BLPORPBETA|115=DOR|128=DOR|1128=9|1129=1.0|1156=20|"
            "131=1507426270445703168|146=1|55=EUR/USD|460=4|167=FXSPOT|38=1000000|"
            "64=20260522|15=EUR|60=20260522-16:53:49.500|453=3|448=DOR1|447=D|452=1|"
            "448=DOR2|447=D|452=1|448=29618590|447=D|452=11|1300=BTBS|10=174|"
        )
        parser = FixParser(config=ParserConfig(strict_checksum=False))
        message = parser.parse(message_str, venue="Bloomberg DOR")
        field = message.get_field(1300)
        assert field is not None
        assert field.name == "MarketSegmentID"
        assert field.raw_value == "BTBS"
        assert field.value_description == "Bloomberg Trade Book Singapore"


class TestBloombergDORTradeExtraction:
    """Tests for Bloomberg DOR trade extraction from parsed messages."""

    @pytest.fixture
    def handler(self):
        return BloombergDORHandler()

    @pytest.fixture
    def parser(self):
        return FixParser(config=ParserConfig(strict_checksum=False))

    def test_extract_spot_execution(self, handler, parser):
        """Spot execution should extract symbol, side, qty, price, currency, settlement date."""
        message = parser.parse(BLOOMBERG_DOR_SPOT_EXEC, venue=handler)
        trade = handler.extract_trade(message)
        assert trade.venue == "Bloomberg DOR"
        assert trade.symbol == "EUR/USD"
        assert trade.side == "Buy"
        assert trade.quantity == 1000000.0
        assert trade.price == 1.08500
        assert trade.currency == "EUR"
        assert trade.settlement_date == "20240117"

    def test_extract_forward_execution(self, handler, parser):
        """Forward execution should extract symbol, qty, price, settlement date."""
        message = parser.parse(BLOOMBERG_DOR_FORWARD_EXEC, venue=handler)
        trade = handler.extract_trade(message)
        assert trade.venue == "Bloomberg DOR"
        assert trade.symbol == "EUR/USD"
        assert trade.quantity == 5000000.0
        assert trade.price == 1.09000
        assert trade.settlement_date == "20240715"

    def test_extract_swap_execution(self, handler, parser):
        """Swap execution should extract symbol, qty, currency."""
        message = parser.parse(BLOOMBERG_DOR_SWAP_EXEC, venue=handler)
        trade = handler.extract_trade(message)
        assert trade.venue == "Bloomberg DOR"
        assert trade.symbol == "EUR/USD"
        assert trade.quantity == 10000000.0
        assert trade.currency == "EUR"

    def test_extract_algo_execution(self, handler, parser):
        """Algo execution should extract symbol, qty, price, currency."""
        message = parser.parse(BLOOMBERG_DOR_ALGO_EXEC, venue=handler)
        trade = handler.extract_trade(message)
        assert trade.venue == "Bloomberg DOR"
        assert trade.symbol == "EUR/USD"
        assert trade.quantity == 2000000.0
        assert trade.price == 1.08520
        assert trade.currency == "EUR"

    def test_extract_spot_quote(self, handler, parser):
        """Spot quote should extract symbol, bid/offer prices."""
        message = parser.parse(BLOOMBERG_DOR_SPOT_QUOTE, venue=handler)
        trade = handler.extract_trade(message)
        assert trade.venue == "Bloomberg DOR"
        assert trade.symbol == "EUR/USD"
        assert trade.bid_price == 1.08490
        assert trade.offer_price == 1.08510

    def test_extract_spot_rfq(self, handler, parser):
        """Spot RFQ should extract symbol and quantity."""
        message = parser.parse(BLOOMBERG_DOR_SPOT_RFQ, venue=handler)
        trade = handler.extract_trade(message)
        assert trade.venue == "Bloomberg DOR"
        assert trade.symbol == "EUR/USD"
        assert trade.quantity == 1000000.0


class TestBloombergDORSwapLegs:
    """Tests for Bloomberg DOR swap leg repeating-group parsing."""

    @pytest.fixture
    def parser(self):
        return FixParser(config=ParserConfig(strict_checksum=False))

    def test_swap_legs_grouped_into_two_entries(self, parser):
        """The NoLegs (555) group in a DOR swap yields both leg entries.

        The sample declares 555=2; tag 1788 (LegID) appears inside each
        leg, so it must be a recognised group member or the second leg is
        dropped.
        """
        message = parser.parse(BLOOMBERG_DOR_SWAP_EXEC, venue="Bloomberg DOR")
        structured = message.get_structured_fields()
        legs = [
            sf.group
            for sf in structured
            if sf.is_group and sf.group is not None and sf.group.count_field.tag == 555
        ]
        assert len(legs) == 1
        legs_group = legs[0]
        assert legs_group.count == 2
        assert len(legs_group.entries) == 2

    def test_leg_id_tag_resolves_to_named_field(self, parser):
        """Tag 1788 (LegID) resolves to a named field under Bloomberg DOR."""
        message = parser.parse(BLOOMBERG_DOR_SWAP_EXEC, venue="Bloomberg DOR")
        field = message.get_field(1788)
        assert field is not None
        assert field.name == "LegID"


class TestBloombergDORQuoteRequestReject:
    """Tests for Bloomberg DOR QuoteRequestReject (35=AG) — a FIX 5.0 message
    type that only resolves once the SP2 spec is layered onto the FIX 4.4 base
    via the message's ApplVerID (tag 1128=9)."""

    @pytest.fixture
    def parser(self):
        return FixParser(config=ParserConfig(strict_checksum=False))

    def test_message_parses_and_detects_venue(self, parser):
        """AG message parses end-to-end and auto-detects as Bloomberg DOR."""
        message = parser.parse(BLOOMBERG_DOR_SPOT_RFQ_REJECT, auto_detect_venue=True)
        assert message.msg_type == "AG"
        assert message.venue == "Bloomberg DOR"

    def test_msg_type_ag_decodes_via_auto_loaded_sp2_spec(self, parser):
        """Tag 35=AG decodes to 'QUOTE_REQUEST_REJECT' because the SP2 spec
        is layered automatically when ApplVerID=9 is seen."""
        message = parser.parse(BLOOMBERG_DOR_SPOT_RFQ_REJECT, auto_detect_venue=True)
        msg_type_field = message.get_field(35)
        assert msg_type_field is not None
        assert msg_type_field.value_description == "QUOTE_REQUEST_REJECT"

    def test_appl_ver_id_resolves(self, parser):
        """ApplVerID=9 decodes to 'FIX 5.0 SP2' so the spec auto-load can fire."""
        message = parser.parse(BLOOMBERG_DOR_SPOT_RFQ_REJECT, auto_detect_venue=True)
        appl_ver = message.get_field(1128)
        assert appl_ver is not None
        assert appl_ver.value_description == "FIX 5.0 SP2"

    def test_reject_reason_decodes(self, parser):
        """Tag 658 (QuoteRequestRejectReason) carries 99=Other for this reject."""
        message = parser.parse(BLOOMBERG_DOR_SPOT_RFQ_REJECT, auto_detect_venue=True)
        reason = message.get_field(658)
        assert reason is not None
        assert reason.name == "QuoteRequestRejectReason"
        assert reason.raw_value == "99"
        assert reason.value_description == "Other"

    def test_text_field_carries_reason_detail(self, parser):
        """Tag 58 (Text) carries the free-text reject detail verbatim."""
        message = parser.parse(BLOOMBERG_DOR_SPOT_RFQ_REJECT, auto_detect_venue=True)
        text = message.get_field(58)
        assert text is not None
        assert text.name == "Text"
        assert "Customer Number [4928]" in text.raw_value

    def test_quote_req_id_links_back_to_request(self, parser):
        """Tag 131 (QuoteReqID) echoes the originating QuoteRequest's ID."""
        message = parser.parse(BLOOMBERG_DOR_SPOT_RFQ_REJECT, auto_detect_venue=True)
        qid = message.get_field(131)
        assert qid is not None
        assert qid.raw_value == "1511314052507373568"

    def test_market_segment_id_decodes(self, parser):
        """Tag 1300=BTBS decodes via the Bloomberg DOR venue's enum override."""
        message = parser.parse(BLOOMBERG_DOR_SPOT_RFQ_REJECT, auto_detect_venue=True)
        seg = message.get_field(1300)
        assert seg is not None
        assert seg.value_description == "Bloomberg Trade Book Singapore"

    def test_related_sym_group_carries_one_entry(self, parser):
        """The NoRelatedSym (146) group is recognised with exactly one entry."""
        message = parser.parse(BLOOMBERG_DOR_SPOT_RFQ_REJECT, auto_detect_venue=True)
        related_sym_groups = [
            sf.group
            for sf in message.get_structured_fields()
            if sf.is_group and sf.group is not None and sf.group.count_field.tag == 146
        ]
        assert len(related_sym_groups) == 1
        group = related_sym_groups[0]
        assert group.count == 1
        assert len(group.entries) == 1

    def test_all_message_tags_have_definitions(self, parser):
        """No tag in this AG should fall through as Unknown — the SP2 auto-load
        plus venue overlay should cover every field present."""
        message = parser.parse(BLOOMBERG_DOR_SPOT_RFQ_REJECT, auto_detect_venue=True)
        unknown = sorted({f.tag for f in message.fields if f.definition is None})
        assert unknown == [], f"Unexpected unknown tags: {unknown}"
