"""Unit tests for Bloomberg DOR venue handler."""

import pytest

from fxfixparser.core.parser import FixParser, ParserConfig
from fxfixparser.venues.bloomberg_dor import BloombergDORHandler
from tests.fixtures.sample_messages import (
    BLOOMBERG_DOR_ALGO_EXEC,
    BLOOMBERG_DOR_FORWARD_EXEC,
    BLOOMBERG_DOR_SPOT_EXEC,
    BLOOMBERG_DOR_SPOT_EXEC_FULL,
    BLOOMBERG_DOR_SPOT_QUOTE,
    BLOOMBERG_DOR_SPOT_RFQ,
    BLOOMBERG_DOR_SPOT_RFQ_REJECT,
    BLOOMBERG_DOR_SWAP_EXEC,
    BLOOMBERG_DOR_SWAP_EXEC_FULL,
    BLOOMBERG_DOR_SWAP_QUOTE_RESPONSE,
    BLOOMBERG_DOR_SWAP_QUOTE_STATUS,
    BLOOMBERG_DOR_SWAP_QUOTE_STATUS_PASS,
    BLOOMBERG_DOR_SWAP_QUOTE_TWO_SIDED,
    BLOOMBERG_MAP_SWAP_EXEC,
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


class TestBloombergDORRepeatingGroupCounts:
    """Tests that the repeating-group walker recognises all entries for
    Bloomberg DOR swap messages whose legs/parties carry FIX 5.0+ tags
    (607 LegProduct, 1068 LegOfferForwardPoints, 2346 LegMidPx, and the
    nested 802 NoPartySubIDs 523/803 leaves). Regression coverage for the
    bug where unregistered member tags terminated the group early."""

    @pytest.fixture
    def parser(self):
        return FixParser(config=ParserConfig(strict_checksum=False))

    def _group(self, message, count_tag: int):
        for sf in message.get_structured_fields():
            if sf.is_group and sf.group is not None and sf.group.count_field.tag == count_tag:
                return sf.group
        return None

    def test_swap_quote_status_yields_four_parties_and_two_legs(self, parser):
        """The AI message has 453=4 (one with a nested 802 NoPartySubIDs) and
        555=2 (each leg carrying 607 LegProduct). Both counts must match."""
        message = parser.parse(BLOOMBERG_DOR_SWAP_QUOTE_STATUS, venue="Bloomberg DOR")

        parties = self._group(message, 453)
        assert parties is not None, "Party IDs group not detected"
        assert parties.count == 4
        assert len(parties.entries) == 4, (
            f"Party count mismatch: declared {parties.count}, "
            f"got {len(parties.entries)} entries — nested 802/523/803 likely "
            f"terminating the walker."
        )

        legs = self._group(message, 555)
        assert legs is not None, "Legs group not detected"
        assert legs.count == 2
        assert len(legs.entries) == 2, (
            f"Leg count mismatch: declared {legs.count}, "
            f"got {len(legs.entries)} entries — 607 LegProduct likely "
            f"terminating the walker."
        )

    def test_swap_quote_yields_two_legs_with_fwd_points_and_mid(self, parser):
        """The Quote (S) carries 1068 LegOfferForwardPoints and 2346 LegMidPx
        per leg; both must register as leg members so the count stays 2."""
        message = parser.parse(BLOOMBERG_DOR_SWAP_QUOTE_RESPONSE, venue="Bloomberg DOR")
        legs = self._group(message, 555)
        assert legs is not None, "Legs group not detected"
        assert legs.count == 2
        assert len(legs.entries) == 2

        leg1, leg2 = legs.entries
        tags1 = {f.tag for f in leg1.fields}
        tags2 = {f.tag for f in leg2.fields}
        # Each leg should carry its 1068 forward points and 2346 mid price
        assert 1068 in tags1 and 1068 in tags2
        assert 2346 in tags1 and 2346 in tags2

    def test_party_sub_id_decodes_inside_nested_group(self, parser):
        """803=4025 in the nested NoPartySubIDs should still decode to the
        Bloomberg enum extension ('Legal Entity Identifier') after the
        repeating-group fix."""
        message = parser.parse(BLOOMBERG_DOR_SWAP_QUOTE_STATUS, venue="Bloomberg DOR")
        sub_type = next((f for f in message.fields if f.tag == 803), None)
        assert sub_type is not None
        assert sub_type.value_description == "Legal Entity Identifier"


class TestBloombergDORTwoSidedSwapQuote:
    """Two-sided FX swap Quote (35=S): per-leg all-in bid/offer rates
    (681/684) plus declared forward points (1067/1068) and flat spot rates
    (188/190). Swap points must be computed from the all-in leg rates per
    the ORP spec definition (far-minus-near differential per side) — the
    declared 1067/1068 values are pips on the wire despite the spec asking
    for unscaled decimals, so they must never feed the swap-point figure."""

    @pytest.fixture
    def parser(self):
        return FixParser(config=ParserConfig(strict_checksum=False))

    @pytest.fixture
    def trade(self, parser):
        handler = BloombergDORHandler()
        message = parser.parse(BLOOMBERG_DOR_SWAP_QUOTE_TWO_SIDED, venue="Bloomberg DOR")
        return handler.extract_trade(message)

    def test_legs_carry_bid_side_tags(self, parser):
        """681 LegBidPx / 1067 LegBidForwardPoints must be group members so
        the walker keeps both legs intact (regression: 681 was missing and
        terminated the first leg entry)."""
        message = parser.parse(BLOOMBERG_DOR_SWAP_QUOTE_TWO_SIDED, venue="Bloomberg DOR")
        legs = None
        for sf in message.get_structured_fields():
            if sf.is_group and sf.group is not None and sf.group.count_field.tag == 555:
                legs = sf.group
        assert legs is not None
        assert legs.count == 2
        assert len(legs.entries) == 2
        for entry in legs.entries:
            tags = {f.tag for f in entry.fields}
            assert {681, 684, 1067, 1068}.issubset(tags)

    def test_quote_swap_basics(self, trade):
        assert trade.is_quote is True
        assert trade.is_swap is True
        assert trade.symbol == "USD/JPY"
        assert trade.side == "Two-Way"
        assert trade.quantity == pytest.approx(1000000)
        assert trade.near_quantity == pytest.approx(1000000)
        assert trade.far_quantity == pytest.approx(1000000)
        assert trade.base_currency == "USD"
        assert trade.term_currency == "JPY"
        assert trade.pip_size == pytest.approx(0.01)

    def test_leg_all_in_rates_extracted(self, trade):
        assert trade.near_leg_bid_rate == pytest.approx(159.0938)
        assert trade.near_leg_offer_rate == pytest.approx(159.0945)
        assert trade.far_leg_bid_rate == pytest.approx(158.9688)
        assert trade.far_leg_offer_rate == pytest.approx(158.9680)
        assert trade.bid_spot_rate == pytest.approx(159.18)
        assert trade.offer_spot_rate == pytest.approx(159.18)

    def test_declared_leg_points_extracted_verbatim(self, trade):
        """1067/1068 are carried through untouched (units unverified)."""
        assert trade.bid_fwd_points == pytest.approx(-8.62)
        assert trade.offer_fwd_points == pytest.approx(-8.55)
        assert trade.far_bid_fwd_points == pytest.approx(-21.12)
        assert trade.far_offer_fwd_points == pytest.approx(-21.20)

    def test_swap_points_computed_from_all_in_legs(self, trade):
        """Spec definition: differential between the far leg's bid/offer and
        the near leg's bid/offer, from the all-in rates.

        bid  = 158.9688 - 159.0938 = -0.1250 (-12.50 pips)
        offer = 158.9680 - 159.0945 = -0.1265 (-12.65 pips)
        """
        assert trade.swap_points_source == "computed"
        assert trade.bid_swap_points == pytest.approx(-0.1250, abs=1e-9)
        assert trade.offer_swap_points == pytest.approx(-0.1265, abs=1e-9)
        assert trade.bid_swap_points / trade.pip_size == pytest.approx(-12.50, abs=1e-6)
        assert trade.offer_swap_points / trade.pip_size == pytest.approx(-12.65, abs=1e-6)

    def test_taker_direction_labels(self, trade):
        """Bid points (-12.50) sit above offer points (-12.65), so the Bid
        column is the taker sell-USD-near / buy-USD-far package — the
        venue's labels anchor to the NEAR leg. Forced by the maker's
        spread (the reverse assignment would hand the taker 0.15 pips
        both ways); the ORP spec itself never defines column direction."""
        from fxfixparser.core.fx_math import swap_quote_directions

        bid_dir, offer_dir = swap_quote_directions(
            trade.bid_swap_points, trade.offer_swap_points, trade.base_currency
        )
        assert bid_dir == "Sell USD near / buy USD far (S/B)"
        assert offer_dir == "Buy USD near / sell USD far (B/S)"

    def test_declared_points_classified_as_pips_convention(self, trade):
        """The wire values (-8.62 etc.) are pips, not the spec's decimals —
        classify_forward_points must detect that against the all-in/spot."""
        from fxfixparser.core.fx_math import classify_forward_points

        for declared, all_in, spot in (
            (trade.bid_fwd_points, trade.near_leg_bid_rate, trade.bid_spot_rate),
            (trade.offer_fwd_points, trade.near_leg_offer_rate, trade.offer_spot_rate),
            (trade.far_bid_fwd_points, trade.far_leg_bid_rate, trade.bid_spot_rate),
            (trade.far_offer_fwd_points, trade.far_leg_offer_rate, trade.offer_spot_rate),
        ):
            verdict = classify_forward_points(declared, all_in, spot, trade.pip_size)
            assert verdict is not None
            assert verdict[0] == "pips"
            assert verdict[1] == pytest.approx(declared)

    def test_one_sided_quote_still_extracts(self, parser):
        """The offer-only quote fixture (684/1068 only, no bid side) yields
        offer-side data and an offer-only swap-point figure."""
        handler = BloombergDORHandler()
        message = parser.parse(BLOOMBERG_DOR_SWAP_QUOTE_RESPONSE, venue="Bloomberg DOR")
        trade = handler.extract_trade(message)
        assert trade.is_quote is True
        assert trade.is_swap is True
        assert trade.side == "Offer Only"
        assert trade.near_leg_bid_rate is None
        assert trade.bid_swap_points is None
        assert trade.near_leg_offer_rate == pytest.approx(1.164551)
        assert trade.far_leg_offer_rate == pytest.approx(1.165588)
        assert trade.swap_points_source == "computed"
        # 1.165588 - 1.164551 = 0.001037 -> 10.37 pips
        assert trade.offer_swap_points == pytest.approx(0.001037, abs=1e-9)


class TestBloombergDORQuoteStatusPass:
    """Regression coverage for the QuoteStatusReport (35=AI) PASS message.

    Verifies enum decoding of 297 QuoteStatus (renamed from the incorrect
    QuoteAckStatus), 587 LegSettlType, and 607 LegProduct, plus that the two
    parties carrying a nested NoPartySubIDs (802) don't break the party count.
    """

    @pytest.fixture
    def parser(self):
        return FixParser(config=ParserConfig(strict_checksum=False))

    def _group(self, message, count_tag: int):
        for sf in message.get_structured_fields():
            if sf.is_group and sf.group is not None and sf.group.count_field.tag == count_tag:
                return sf.group
        return None

    def test_quote_status_field_named_and_decoded(self, parser):
        """Tag 297 must be named QuoteStatus (not QuoteAckStatus) and 11 decodes
        to 'Pass' — the spec and standard FIX both call this QuoteStatus."""
        message = parser.parse(BLOOMBERG_DOR_SWAP_QUOTE_STATUS_PASS, venue="Bloomberg DOR")
        status = next((f for f in message.fields if f.tag == 297), None)
        assert status is not None
        assert status.name == "QuoteStatus"
        assert status.raw_value == "11"
        assert status.value_description == "Pass"

    def test_three_parties_with_two_nested_sub_ids(self, parser):
        """453=3 with the first and third parties each carrying a nested
        NoPartySubIDs (802); all three entries must be detected."""
        message = parser.parse(BLOOMBERG_DOR_SWAP_QUOTE_STATUS_PASS, venue="Bloomberg DOR")
        parties = self._group(message, 453)
        assert parties is not None, "Party IDs group not detected"
        assert parties.count == 3
        assert len(parties.entries) == 3

    def test_leg_settl_type_and_product_decode(self, parser):
        """Per-leg 587 LegSettlType (1=Cash, B=BrokenDate) and 607 LegProduct
        (4=CURRENCY) must decode to their enum descriptions."""
        message = parser.parse(BLOOMBERG_DOR_SWAP_QUOTE_STATUS_PASS, venue="Bloomberg DOR")
        legs = self._group(message, 555)
        assert legs is not None, "Legs group not detected"
        assert len(legs.entries) == 2

        leg1, leg2 = legs.entries
        settl1 = next(f for f in leg1.fields if f.tag == 587)
        settl2 = next(f for f in leg2.fields if f.tag == 587)
        assert settl1.value_description == "Cash"
        assert settl2.value_description == "BrokenDate"

        for leg in (leg1, leg2):
            product = next(f for f in leg.fields if f.tag == 607)
            assert product.value_description == "CURRENCY"


class TestBloombergDORSpotExecFull:
    """Regression coverage for the full ORP spot execution report.

    A real DOR spot fill carries 195=0 (zero forward points), the Ccy1/Ccy2
    market-type tags (22159/22160), and a NoRegulatoryTradeIDs (1907) entry
    that includes 1904 RegulatoryTradeIDEvent.
    """

    @pytest.fixture
    def parser(self):
        return FixParser(config=ParserConfig(strict_checksum=False))

    def _group(self, message, count_tag: int):
        for sf in message.get_structured_fields():
            if sf.is_group and sf.group is not None and sf.group.count_field.tag == count_tag:
                return sf.group
        return None

    def test_ccy_market_type_tags_resolve(self, parser):
        """22159/22160 must resolve to Ccy1MarketType/Ccy2MarketType and
        decode value R per the ORP spec."""
        message = parser.parse(BLOOMBERG_DOR_SPOT_EXEC_FULL, auto_detect_venue=True)

        ccy1 = message.get_field(22159)
        ccy2 = message.get_field(22160)
        assert ccy1 is not None and ccy1.name == "Ccy1MarketType"
        assert ccy2 is not None and ccy2.name == "Ccy2MarketType"
        assert ccy1.value_description == "Regular / offshore"
        assert ccy2.value_description == "Regular / offshore"

    def test_no_unknown_tags(self, parser):
        """Every tag in the full spot exec must have a definition."""
        message = parser.parse(BLOOMBERG_DOR_SPOT_EXEC_FULL, auto_detect_venue=True)
        unknown = sorted({f.tag for f in message.fields if f.definition is None})
        assert unknown == [], f"Unexpected unknown tags: {unknown}"

    def test_regulatory_trade_id_entry_complete(self, parser):
        """The single 1907 entry must span all four fields — 1904
        RegulatoryTradeIDEvent must not terminate the group walker."""
        message = parser.parse(BLOOMBERG_DOR_SPOT_EXEC_FULL, venue="Bloomberg DOR")
        group = self._group(message, 1907)
        assert group is not None, "Regulatory Trade IDs group not detected"
        assert group.count == 1
        assert len(group.entries) == 1
        tags = {f.tag for f in group.entries[0].fields}
        assert tags == {1903, 1905, 1904, 1906}


class TestBloombergDORSwapExecFull:
    """Regression coverage for the full ORP swap execution report.

    Both legs carry executed-leg tags (1073 LegLastForwardPoints, 1074
    LegCalculatedCcyLastQty, 1418 LegLastQty) and the message has three
    NoRegulatoryTradeIDs entries (package UTI + per-leg UTIs via 2411).
    """

    @pytest.fixture
    def handler(self):
        return BloombergDORHandler()

    @pytest.fixture
    def parser(self):
        return FixParser(config=ParserConfig(strict_checksum=False))

    def _group(self, message, count_tag: int):
        for sf in message.get_structured_fields():
            if sf.is_group and sf.group is not None and sf.group.count_field.tag == count_tag:
                return sf.group
        return None

    def test_legs_group_parses_both_entries(self, parser):
        """555=2 with 1073/1074/1418 inside each leg must yield two complete
        entries — 1073 must not terminate the walker mid-leg."""
        message = parser.parse(BLOOMBERG_DOR_SWAP_EXEC_FULL, venue="Bloomberg DOR")
        legs = self._group(message, 555)
        assert legs is not None, "Legs group not detected"
        assert legs.count == 2
        assert len(legs.entries) == 2, (
            f"Leg count mismatch: declared {legs.count}, got "
            f"{len(legs.entries)} entries — 1073 LegLastForwardPoints likely "
            f"terminating the walker."
        )
        near, far = legs.entries
        for entry in (near, far):
            tags = {f.tag for f in entry.fields}
            assert {600, 609, 624, 556, 685, 587, 588, 637, 1073, 1074, 1418} <= tags

    def test_regulatory_trade_ids_group_parses_all_entries(self, parser):
        """1907=3 must yield three entries; the second and third carry the
        2411 RegulatoryLegRefID leg reference."""
        message = parser.parse(BLOOMBERG_DOR_SWAP_EXEC_FULL, venue="Bloomberg DOR")
        group = self._group(message, 1907)
        assert group is not None, "Regulatory Trade IDs group not detected"
        assert group.count == 3
        assert len(group.entries) == 3

        entry_tags = [{f.tag for f in e.fields} for e in group.entries]
        assert entry_tags[0] == {1903, 1905, 1904, 1906}
        assert entry_tags[1] == {1903, 1905, 1904, 1906, 2411}
        assert entry_tags[2] == {1903, 1905, 1904, 1906, 2411}

    def test_regulatory_trade_id_event_decodes(self, parser):
        """1904=0 decodes to the spec description (initial block trade)."""
        message = parser.parse(BLOOMBERG_DOR_SWAP_EXEC_FULL, venue="Bloomberg DOR")
        event = message.get_field(1904)
        assert event is not None
        assert event.name == "RegulatoryTradeIDEvent"
        assert event.value_description == "Initial block trade"

    def test_no_unknown_tags(self, parser):
        """Every tag in the full swap exec must have a definition."""
        message = parser.parse(BLOOMBERG_DOR_SWAP_EXEC_FULL, auto_detect_venue=True)
        unknown = sorted({f.tag for f in message.fields if f.definition is None})
        assert unknown == [], f"Unexpected unknown tags: {unknown}"

    def test_extract_trade_populates_both_legs(self, handler, parser):
        """extract_trade must surface both legs: dates, prices, quantities
        (from 1418 LegLastQty / 685 LegOrderQty), actions, and swap points."""
        message = parser.parse(BLOOMBERG_DOR_SWAP_EXEC_FULL, venue=handler)
        trade = handler.extract_trade(message)

        assert trade.is_swap is True
        assert trade.symbol == "EUR/USD"
        assert trade.settlement_date == "20260709"
        assert trade.far_settlement_date == "20260810"
        assert trade.near_leg_price == pytest.approx(1.14418)
        assert trade.far_leg_price == pytest.approx(1.145681)
        assert trade.near_quantity == pytest.approx(1000000.0)
        assert trade.far_quantity == pytest.approx(1000000.0)
        assert trade.swap_points == pytest.approx(0.001501)
        # Explicit per-leg sides: near 624=2 (Sell EUR), far 624=1 (Buy EUR)
        assert trade.near_leg_action == "Sell EUR"
        assert trade.far_leg_action == "Buy EUR"
        assert trade.swap_side_source == "legs"


class TestBloombergMAPSwapExec:
    """Coverage for the Bloomberg MAP gateway swap ER.

    MAP is the plain FIX 4.4 flavor of the ORP/DOR dialect: MAP_<party>
    CompIDs (Bloomberg side always MAP_BLP*), no FIXT / 115 / 128 markers,
    flat package-level regulatory ID fields before the 1907 count, and a
    CompDealerQuoteGrp (10009) holding reference-rate pseudo-dealers.
    """

    @pytest.fixture
    def handler(self):
        return BloombergDORHandler()

    @pytest.fixture
    def parser(self):
        # The fixture's BodyLength and CheckSum are byte-valid, so parse in
        # fully strict mode to guard against fixture rot.
        return FixParser(config=ParserConfig(strict_checksum=True, strict_body_length=True))

    def _group(self, message, count_tag: int):
        for sf in message.get_structured_fields():
            if sf.is_group and sf.group is not None and sf.group.count_field.tag == count_tag:
                return sf.group
        return None

    def test_autodetects_bloomberg_dor(self, parser):
        """MAP_BLP* CompIDs must resolve to the Bloomberg DOR handler even
        without FIXT / routing markers."""
        message = parser.parse(BLOOMBERG_MAP_SWAP_EXEC, auto_detect_venue=True)
        assert message.venue == "Bloomberg DOR"

    def test_claims_message_both_directions(self, handler):
        """The MAP_BLP CompID may sit on either side of the session."""
        from fxfixparser.core.field import FixField
        from fxfixparser.core.message import FixMessage

        bloomberg_sends = FixMessage(
            fields=[
                FixField(tag=49, raw_value="MAP_BLP_BETA"),
                FixField(tag=56, raw_value="MAP_CLIENT_BETA"),
            ]
        )
        client_sends = FixMessage(
            fields=[
                FixField(tag=49, raw_value="MAP_CLIENT_BETA"),
                FixField(tag=56, raw_value="MAP_BLP_BETA"),
            ]
        )
        no_bloomberg = FixMessage(
            fields=[
                FixField(tag=49, raw_value="MAP_CLIENT_BETA"),
                FixField(tag=56, raw_value="MAP_OTHERBANK"),
            ]
        )
        assert handler.claims_message(bloomberg_sends) is True
        assert handler.claims_message(client_sends) is True
        assert handler.claims_message(no_bloomberg) is False

    def test_regulatory_tags_resolve(self, parser):
        """1903/1905/1906/1907/2411 must resolve without an ApplVerID spec
        layer (MAP is plain FIX 4.4, so the venue overlay supplies them)."""
        message = parser.parse(BLOOMBERG_MAP_SWAP_EXEC, auto_detect_venue=True)

        assert message.get_field(1903).name == "RegulatoryTradeID"
        assert message.get_field(1905).name == "RegulatoryTradeIDSource"
        assert message.get_field(1907).name == "NoRegulatoryTradeIDs"
        reg_type = message.get_field(1906)
        assert reg_type.name == "RegulatoryTradeIDType"
        assert reg_type.value_description == "Current (default if not specified)"
        leg_ref = message.get_field(2411)
        assert leg_ref.name == "RegulatoryLegRefID"
        assert leg_ref.raw_value == "2"

    def test_exec_method_decodes(self, parser):
        """2405=2 must decode as Automated execution."""
        message = parser.parse(BLOOMBERG_MAP_SWAP_EXEC, auto_detect_venue=True)
        exec_method = message.get_field(2405)
        assert exec_method.name == "ExecMethod"
        assert exec_method.value_description == "Automated"

    def test_comp_dealer_quote_group_parses_both_entries(self, parser):
        """10009=2 must yield two complete entries — including the
        undocumented member 22545, which must not split the group."""
        message = parser.parse(BLOOMBERG_MAP_SWAP_EXEC, auto_detect_venue=True)
        group = self._group(message, 10009)
        assert group is not None, "Competing Dealer Quotes group not detected"
        assert group.count == 2
        assert len(group.entries) == 2

        expected_tags = {10010, 10011, 22161, 22162, 22163, 22276, 22485, 22486, 22545}
        for entry in group.entries:
            assert {f.tag for f in entry.fields} == expected_tags

        dealer_ids = [f.raw_value for e in group.entries for f in e.fields if f.tag == 10010]
        assert dealer_ids == ["MidRate", "RefRate"]

    def test_comp_dealer_tags_resolve_with_bloomberg_meanings(self, parser):
        """10011 must decode as CompDealerQuotePrice (not the LFX
        IsSEFTrade meaning) and 22276=0 as an indicative quote."""
        message = parser.parse(BLOOMBERG_MAP_SWAP_EXEC, auto_detect_venue=True)
        assert message.get_field(10011).name == "CompDealerQuotePrice"
        assert message.get_field(22163).name == "CompDealerQuoteSwapPoints"
        quote_type = message.get_field(22276)
        assert quote_type.name == "CompDealerQuoteType"
        assert quote_type.value_description == "Indicative (Bloomberg provided)"

    def test_liquidity_taker_sub_id_decodes(self, parser):
        """PartySubIDType 4047 must decode as Liquidity taker."""
        message = parser.parse(BLOOMBERG_MAP_SWAP_EXEC, auto_detect_venue=True)
        sub_id_types = [f for f in message.get_fields(803) if f.raw_value == "4047"]
        assert sub_id_types, "PartySubIDType 4047 not present in fixture"
        assert sub_id_types[0].value_description == "Liquidity taker"

    def test_only_undocumented_tags_stay_unknown(self, parser):
        """22078-22081 and 22277 are absent from the ORP 1.9.8 spec, so
        they must stay unknown (definitions are never invented) — and
        nothing else may be unknown."""
        message = parser.parse(BLOOMBERG_MAP_SWAP_EXEC, auto_detect_venue=True)
        unknown = sorted({f.tag for f in message.fields if f.definition is None})
        assert unknown == [22078, 22079, 22080, 22081, 22277]

    def test_extract_trade_swap_summary(self, handler, parser):
        """The USD/CAD swap summary must populate both legs from the 555
        group with per-leg sides."""
        message = parser.parse(BLOOMBERG_MAP_SWAP_EXEC, venue=handler)
        trade = handler.extract_trade(message)

        assert trade.is_swap is True
        assert trade.symbol == "USD/CAD"
        assert trade.settlement_date == "20260728"
        assert trade.far_settlement_date == "20270129"
        assert trade.near_leg_price == pytest.approx(1.411799)
        assert trade.far_leg_price == pytest.approx(1.399186)
        assert trade.near_quantity == pytest.approx(500000.0)
        assert trade.far_quantity == pytest.approx(500000.0)
        assert trade.swap_points == pytest.approx(-0.012613)
        # Explicit per-leg sides: near 624=2 (Sell USD), far 624=1 (Buy USD)
        assert trade.near_leg_action == "Sell USD"
        assert trade.far_leg_action == "Buy USD"
        assert trade.swap_side_source == "legs"


class TestBloombergDORQuoteResponseParsedReport:
    """A DOR swap quote acceptance as a vendor 'parsed report' export.

    This is the shape a captured RFS conversation gives for the messages
    the client *sent*: the report is a pretty-printed application view,
    tags are sorted numerically within each section, and the session
    layer's BodyLength (9) and CheckSum (10) are absent because they are
    stamped after the message is logged. The accepted rate lives in the
    side taken (681 LegBidPx / 188 BidSpotRate), not in a fill's 637/194.
    """

    QUOTE_RESPONSE_REPORT = (
        "(8)BeginString: FIXT.1.1\n"
        "(34)MsgSeqNum: 289\n"
        "(35)MsgType: QuoteResponse (AJ)\n"
        "(49)SenderCompID: ORP_BCQT_B\n"
        "(52)SendingTime: 20240115-10:31:27.233\n"
        "(56)TargetCompID: BLPORPBETA\n"
        "(115)OnBehalfOfCompID: DOR (DOR)\n"
        "(128)DeliverToCompID: DOR (DOR)\n"
        "(1128)ApplVerID: FIX50SP2 (9)\n"
        "(11)ClOrdID: CL200\n"
        "(54)Side: Sell (2)\n"
        "(55)Symbol: EUR/USD\n"
        "(117)QuoteID: Q200-DOR2-4\n"
        "(131)QuoteReqID: REQ200\n"
        "(167)SecurityType: FXSwap (FXSWAP)\n"
        "(188)BidSpotRate: 1.08500\n"
        "(453)NoPartyIDs: 1\n"
        "  (447)PartyIDSource: Proprietary (D)\n"
        "  (448)PartyID: DOR2\n"
        "  (452)PartyRole: ExecutingFirm (1)\n"
        "  (460)Product: CURRENCY (4)\n"
        "  (693)QuoteRespID: CL200\n"
        "  (694)QuoteRespType: Hit (1)\n"
        "(555)NoLegs: 2\n"
        "  (556)LegCurrency: EUR\n"
        "  (588)LegSettlDate: 20240117\n"
        "  (600)LegSymbol: EUR/USD\n"
        "  (609)LegSecurityType: FXForward (FXFWD)\n"
        "  (624)LegSide: Buy (1)\n"
        "  (681)LegBidPx: 1.08500\n"
        "  (685)LegOrderQty: 10000000\n"
        "    ----\n"
        "  (556)LegCurrency: EUR\n"
        "  (588)LegSettlDate: 20240415\n"
        "  (600)LegSymbol: EUR/USD\n"
        "  (609)LegSecurityType: FXForward (FXFWD)\n"
        "  (624)LegSide: Sell (2)\n"
        "  (681)LegBidPx: 1.09000\n"
        "  (685)LegOrderQty: 10000000\n"
    )

    def test_parses_without_body_length_or_checksum(self):
        message = FixParser().parse(self.QUOTE_RESPONSE_REPORT, auto_detect_venue=True)

        assert message.converted_from_report is True
        assert message.venue == "Bloomberg DOR"
        assert message.msg_type == "AJ"
        assert message.get_value(9) is None
        assert message.get_value(10) is None

    def test_message_level_tags_stay_out_of_the_party_group(self):
        """460/693/694 are indented under a party entry by the report's
        numeric sort, but they are message-level fields."""
        message = FixParser().parse(self.QUOTE_RESPONSE_REPORT, auto_detect_venue=True)

        top_level = {sf.field.tag for sf in message.get_structured_fields() if sf.field}
        assert {460, 693, 694} <= top_level

        parties = [
            sf.group
            for sf in message.get_structured_fields()
            if sf.is_group and sf.group and sf.group.count_field.tag == 453
        ]
        assert len(parties) == 1
        assert [f.tag for f in parties[0].entries[0].fields] == [447, 448, 452]

    def test_extract_trade_prices_the_accepted_side(self):
        handler = BloombergDORHandler()
        message = FixParser().parse(self.QUOTE_RESPONSE_REPORT, venue=handler)
        trade = handler.extract_trade(message)

        assert trade.is_swap is True
        assert trade.symbol == "EUR/USD"
        assert trade.settlement_date == "20240117"
        assert trade.far_settlement_date == "20240415"
        assert trade.spot_rate == pytest.approx(1.08500)
        assert trade.near_leg_price == pytest.approx(1.08500)
        assert trade.far_leg_price == pytest.approx(1.09000)
        assert trade.swap_points_pips == pytest.approx(50.0, abs=1e-6)
        assert trade.near_leg_action == "Buy EUR"
        assert trade.far_leg_action == "Sell EUR"
        assert trade.swap_side_source == "legs"
