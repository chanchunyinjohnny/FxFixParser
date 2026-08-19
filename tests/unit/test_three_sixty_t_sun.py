"""Unit tests for the 360T SUN (Swap User Network) venue handler."""

import pytest

from fxfixparser.core.message import FixMessage
from fxfixparser.core.parser import FixParser, ParserConfig
from fxfixparser.venues.registry import VenueRegistry
from fxfixparser.venues.three_sixty_t_sun import ThreeSixtyTSUNHandler

# THREE_SIXTY_T_SWAP_EXEC / THREE_SIXTY_T_TI_SWAP are the sibling 360T
# interfaces, imported for the detection regressions.
from tests.fixtures.sample_messages import (
    SUN_ALL_SAMPLES,
    SUN_EFP_ORDER_ACK,
    SUN_MARKET_DATA_SNAPSHOT,
    SUN_NDS_EXECUTION_FILL,
    SUN_NEW_ORDER_LIST,
    SUN_PARTY_RISK_LIMIT_CHECK_ACK,
    SUN_PARTY_RISK_LIMIT_CHECK_REQUEST,
    SUN_SECURITY_DEFINITION,
    SUN_SWAP_EXECUTION_FILL,
    SUN_SWAP_NEW_ORDER_SINGLE,
    SUN_SWAP_ORDER_ACK,
    SUN_TRADE_EXPORT_EXECUTION,
    THREE_SIXTY_T_SWAP_EXEC,
    THREE_SIXTY_T_TI_SWAP,
)


def _parse(raw: str) -> FixMessage:
    """Parse with the SUN venue explicitly selected."""
    parser = FixParser(config=ParserConfig(strict_checksum=False))
    return parser.parse(raw, venue="360T SUN")


def _parse_raw(raw: str) -> FixMessage:
    """Parse with no venue (for claims_message tests)."""
    parser = FixParser(config=ParserConfig(strict_checksum=False))
    return parser.parse(raw)


def _autodetect(raw: str) -> FixMessage:
    parser = FixParser(config=ParserConfig(strict_checksum=False))
    return parser.parse(raw, auto_detect_venue=True)


@pytest.fixture
def handler() -> ThreeSixtyTSUNHandler:
    return ThreeSixtyTSUNHandler()


class TestSUNHandlerProperties:
    def test_name(self, handler: ThreeSixtyTSUNHandler) -> None:
        assert handler.name == "360T SUN"

    def test_sender_comp_ids(self, handler: ThreeSixtyTSUNHandler) -> None:
        assert handler.matches_sender("360T_SUN")
        assert not handler.matches_sender("360T")  # RFS alias
        assert not handler.matches_sender("360T_TI")  # TradeImporter alias

    def test_registered_in_default_registry(self, venue_registry: VenueRegistry) -> None:
        assert "360T SUN" in [v.name for v in venue_registry.all_venues()]


class TestSUNClaimsMessage:
    """claims_message must claim SUN traffic and abstain on everything else."""

    def test_claims_on_sun_compid(self, handler: ThreeSixtyTSUNHandler) -> None:
        assert handler.claims_message(_parse_raw(SUN_SWAP_ORDER_ACK))

    def test_claims_on_client_compid_suffix(self, handler: ThreeSixtyTSUNHandler) -> None:
        raw = (
            "8=FIXT.1.1|9=0|35=D|34=1|49=ACME_SUN|56=SOMEGATEWAY|"
            "52=20260604-08:00:00.000|11=X|55=EUR/USD|54=1|10=000|"
        )
        assert handler.claims_message(_parse_raw(raw))

    def test_claims_on_sun_only_tag(self, handler: ThreeSixtyTSUNHandler) -> None:
        # LastNearLegPx(9630) is sent by no other supported venue.
        raw = (
            "8=FIXT.1.1|9=0|35=8|34=1|49=GATEWAY|56=CLIENT|52=20260604-08:00:00.000|"
            "37=1|17=1|150=F|39=2|55=EUR/USD|9630=1.0838|9631=1.085034|10=000|"
        )
        assert handler.claims_message(_parse_raw(raw))

    def test_claims_on_credit_check_msg_type(self, handler: ThreeSixtyTSUNHandler) -> None:
        assert handler.claims_message(_parse_raw(SUN_PARTY_RISK_LIMIT_CHECK_ACK))

    def test_claims_on_emso_fill_id(self, handler: ThreeSixtyTSUNHandler) -> None:
        raw = (
            "8=FIXT.1.1|9=0|35=8|34=1|49=GATEWAY|56=CLIENT|52=20260604-08:00:00.000|"
            "37=EMSO-1|17=1|150=F|39=2|55=EUR/USD|527=EMSO-6565116|10=000|"
        )
        assert handler.claims_message(_parse_raw(raw))

    def test_claims_on_nds_product_code(self, handler: ThreeSixtyTSUNHandler) -> None:
        raw = (
            "8=FIXT.1.1|9=0|35=8|34=1|49=GATEWAY|56=CLIENT|52=20260604-08:00:00.000|"
            "37=1|17=1|150=F|39=2|55=USD/KRW|7071=FX-NDS|10=000|"
        )
        assert handler.claims_message(_parse_raw(raw))

    def test_does_not_claim_rfs_message(self, handler: ThreeSixtyTSUNHandler) -> None:
        assert not handler.claims_message(_parse_raw(THREE_SIXTY_T_SWAP_EXEC))

    def test_does_not_claim_ti_message(self, handler: ThreeSixtyTSUNHandler) -> None:
        # A TI swap also carries ProductType=FX-SWAP — SUN must not take it.
        assert not handler.claims_message(_parse_raw(THREE_SIXTY_T_TI_SWAP))


class TestSUNVenueDetection:
    def test_all_samples_detect_as_sun(self) -> None:
        for raw in SUN_ALL_SAMPLES:
            assert _autodetect(raw).venue == "360T SUN"

    def test_sibling_360t_interfaces_still_detected(self) -> None:
        """Registering SUN ahead of TI must not divert RFS or TI traffic."""
        assert _autodetect(THREE_SIXTY_T_SWAP_EXEC).venue == "360T RFS"
        assert _autodetect(THREE_SIXTY_T_TI_SWAP).venue == "360T TI"


class TestSUNTagDecoding:
    def test_no_unknown_tags_in_any_sample(self) -> None:
        """Every tag SUN sends is defined — nothing falls through as Unknown."""
        for raw in SUN_ALL_SAMPLES:
            message = _autodetect(raw)
            unknown = sorted({f.tag for f in message.fields if f.definition is None})
            assert unknown == [], f"undefined tags {unknown} in {message.msg_type}"

    def test_proprietary_tags_named(self) -> None:
        message = _parse(SUN_SWAP_EXECUTION_FILL)
        names = {f.tag: f.name for f in message.fields}
        assert names[9630] == "LastNearLegPx"
        assert names[9631] == "LastFarLegPx"
        assert names[9617] == "LastQty2"
        assert names[6164] == "LeavesQty2"
        assert names[6165] == "CumQty2"
        assert names[9752] == "StreamID"

    def test_side_decodes_with_far_leg_convention(self) -> None:
        message = _parse(SUN_SWAP_EXECUTION_FILL)
        side = message.get_field(54)
        assert side is not None
        assert side.value_description == "Buy (base currency of the far leg)"

    def test_order_flags_decode(self) -> None:
        message = _parse(SUN_SWAP_NEW_ORDER_SINGLE)
        assert message.get_field(40).value_description == "Limit"
        assert message.get_field(59).value_description == "Day (or session)"
        assert message.get_field(1822).value_description == "Multiple (applies to every execution)"
        assert message.get_field(9822) is not None  # UnevenSwapAllowed

    def test_credit_check_enums_decode(self) -> None:
        message = _parse(SUN_PARTY_RISK_LIMIT_CHECK_ACK)
        assert message.get_field(2325).value_description == "Approved"
        assert message.get_field(2326).value_description == "Successful"

    def test_clearing_state_decodes(self) -> None:
        message = _parse(SUN_TRADE_EXPORT_EXECUTION)
        assert message.get_field(7626).value_description == "Novated"

    def test_fix50_tags_decode_without_appl_ver_id(self) -> None:
        """SUN marks ApplVerID(1128) optional, so the FIX 5.0 tags it uses are
        also defined in the venue overlay — a message without 1128 must still
        decode them rather than falling back to Unknown."""
        raw = (
            "8=FIXT.1.1|9=0|35=DF|34=1|49=360T_SUN|56=ACME_SUN|"
            "52=20260604-08:00:00.000|2318=RLC-1|2320=0|2321=0|2323=0|"
            "2324=4000000|15=EUR|55=EUR/USD|54=1|10=000|"
        )
        message = _autodetect(raw)
        assert message.get_field(2318).name == "RiskLimitCheckRequestID"
        assert message.get_field(2324).name == "RiskLimitCheckAmount"
        assert [f.tag for f in message.fields if f.definition is None] == []


class TestSUNProductDetection:
    def test_absent_product_type_is_fx_swap(self) -> None:
        assert _autodetect(SUN_SWAP_EXECUTION_FILL).product_type == "Swap"

    def test_nds(self) -> None:
        assert _autodetect(SUN_NDS_EXECUTION_FILL).product_type == "NDS"

    def test_efp(self) -> None:
        assert _autodetect(SUN_EFP_ORDER_ACK).product_type == "EFP"

    def test_strip_order_list(self) -> None:
        assert _autodetect(SUN_NEW_ORDER_LIST).product_type == "Swap"

    def test_security_definition_is_not_economic(self) -> None:
        assert _autodetect(SUN_SECURITY_DEFINITION).product_type is None

    def test_market_data_book_is_labelled_with_the_sun_product(
        self, handler: ThreeSixtyTSUNHandler
    ) -> None:
        """A swap-points book names its instrument — otherwise the generic
        product registry would fall back to labelling it Spot — but it carries
        no trade, so no swap economics are invented for it."""
        message = _autodetect(SUN_MARKET_DATA_SNAPSHOT)
        assert message.product_type == "Swap"
        trade = handler.extract_trade(message)
        assert trade.is_swap is False
        assert trade.swap_points is None

    def test_credit_check_request_names_the_instrument(self) -> None:
        assert _autodetect(SUN_PARTY_RISK_LIMIT_CHECK_REQUEST).product_type == "Swap"

    def test_credit_check_ack_without_symbol_is_not_economic(self) -> None:
        assert _autodetect(SUN_PARTY_RISK_LIMIT_CHECK_ACK).product_type is None


class TestSUNSwapExecution:
    """The standard fill ExecutionReport — all-in rates in 9630/9631."""

    def test_swap_economics(self, handler: ThreeSixtyTSUNHandler) -> None:
        trade = handler.extract_trade(_parse(SUN_SWAP_EXECUTION_FILL))

        assert trade.is_swap is True
        assert trade.symbol == "EUR/USD"
        assert trade.settlement_date == "20260608"
        assert trade.far_settlement_date == "20260708"
        assert trade.near_leg_price == pytest.approx(1.083800)
        assert trade.far_leg_price == pytest.approx(1.085034)
        assert trade.spot_rate == pytest.approx(1.08380)
        assert trade.swap_points == pytest.approx(0.001234)
        assert trade.swap_points_pips == pytest.approx(12.34)

    def test_executed_quantities(self, handler: ThreeSixtyTSUNHandler) -> None:
        """A partial fill reports the executed amount (32 / 9617), not the full
        order quantity (38)."""
        trade = handler.extract_trade(_parse(SUN_SWAP_EXECUTION_FILL))
        assert trade.quantity == pytest.approx(4_000_000.0)
        assert trade.near_quantity == pytest.approx(4_000_000.0)
        assert trade.far_quantity == pytest.approx(4_000_000.0)

    def test_side_applies_to_far_leg_base_currency(self, handler: ThreeSixtyTSUNHandler) -> None:
        trade = handler.extract_trade(_parse(SUN_SWAP_EXECUTION_FILL))
        assert trade.near_leg_action == "Sell EUR"
        assert trade.far_leg_action == "Buy EUR"
        assert trade.swap_side_source == "360t"

    def test_price_is_the_far_leg_rate_not_the_swap_points(
        self, handler: ThreeSixtyTSUNHandler
    ) -> None:
        """LastPx(31) carries swap points on SUN; it must never surface as a
        rate in trade.price."""
        trade = handler.extract_trade(_parse(SUN_SWAP_EXECUTION_FILL))
        assert trade.price == pytest.approx(1.085034)

    def test_venue_extras(self) -> None:
        message = _autodetect(SUN_SWAP_EXECUTION_FILL)
        assert message.venue_extras["fill_id"] == "EMSO-6565116"
        assert message.venue_extras["stream_id"] == "7"
        assert message.venue_extras["near_opposite_qty"] == "4335200"
        assert message.venue_extras["far_opposite_qty"] == "4340136"


class TestSUNPointsOnlyMessages:
    """Orders and acknowledgements quote swap points and no all-in rates."""

    def test_order_has_points_but_no_leg_rates(self, handler: ThreeSixtyTSUNHandler) -> None:
        trade = handler.extract_trade(_parse(SUN_SWAP_NEW_ORDER_SINGLE))
        assert trade.is_swap is True
        assert trade.swap_points_pips == pytest.approx(12.34)
        assert trade.swap_points == pytest.approx(0.001234)
        # Price(44) is swap points — it must not masquerade as a leg rate.
        assert trade.near_leg_price is None
        assert trade.far_leg_price is None
        assert trade.price is None
        assert trade.spot_rate is None

    def test_order_quantities_and_dates(self, handler: ThreeSixtyTSUNHandler) -> None:
        trade = handler.extract_trade(_parse(SUN_SWAP_NEW_ORDER_SINGLE))
        assert trade.quantity == pytest.approx(10_000_000.0)
        assert trade.settlement_date == "20260608"
        assert trade.far_settlement_date == "20260708"

    def test_order_ack(self, handler: ThreeSixtyTSUNHandler) -> None:
        message = _parse(SUN_SWAP_ORDER_ACK)
        trade = handler.extract_trade(message)
        # LastQty(32) is absent on an ack: the notional is OrderQty(38).
        assert trade.quantity == pytest.approx(10_000_000.0)
        assert trade.swap_points_pips == pytest.approx(12.34)
        assert message.get_field(150).value_description == "New"


class TestSUNNDSExecution:
    def test_nds_fixing_fields(self) -> None:
        message = _parse(SUN_NDS_EXECUTION_FILL)
        assert message.get_value(7075) == "KFTC-USDKRW"
        assert message.get_value(7543) == "20260604"
        assert message.get_value(7545) == "20260804"

    def test_nds_economics_use_two_decimal_pips(self, handler: ThreeSixtyTSUNHandler) -> None:
        """USD/KRW is quoted to two decimals, so a pip is 0.01: -1.50 in rate
        terms is -150 swap pips."""
        trade = handler.extract_trade(_parse(SUN_NDS_EXECUTION_FILL))
        assert trade.near_leg_price == pytest.approx(1320.50)
        assert trade.far_leg_price == pytest.approx(1319.00)
        assert trade.swap_points == pytest.approx(-1.50)
        assert trade.swap_points_pips == pytest.approx(-150.0)
        assert trade.near_leg_action == "Buy USD"
        assert trade.far_leg_action == "Sell USD"


class TestSUNTradeExportExecution:
    """The regulatory-complete report prices the legs in 31 / 6160."""

    def test_leg_rates_come_from_last_px_and_last_px2(self, handler: ThreeSixtyTSUNHandler) -> None:
        trade = handler.extract_trade(_parse(SUN_TRADE_EXPORT_EXECUTION))
        assert trade.near_leg_price == pytest.approx(1.083800)
        assert trade.far_leg_price == pytest.approx(1.085034)
        assert trade.swap_points_pips == pytest.approx(12.34)

    def test_quantity_falls_back_to_order_qty(self, handler: ThreeSixtyTSUNHandler) -> None:
        """LastQty(32) is always 0 on this report, so the notional is 38."""
        trade = handler.extract_trade(_parse(SUN_TRADE_EXPORT_EXECUTION))
        assert trade.quantity == pytest.approx(4_000_000.0)
        assert trade.far_quantity == pytest.approx(4_000_000.0)

    def test_regulatory_groups(self) -> None:
        message = _parse(SUN_TRADE_EXPORT_EXECUTION)
        groups = {
            sf.group.count_field.tag: sf.group
            for sf in message.get_structured_fields()
            if sf.is_group
        }
        # Product-level, near-leg and far-leg TVTICs.
        assert len(groups[1907].entries) == 3
        # Per-leg ISINs and the MiFID waiver + deferral.
        assert len(groups[454].entries) == 2
        assert len(groups[2668].entries) == 2

    def test_upis_and_clearing_in_venue_extras(self) -> None:
        message = _autodetect(SUN_TRADE_EXPORT_EXECUTION)
        assert message.venue_extras["upi"] == "QZ0000000001"
        assert message.venue_extras["upi_far"] == "QZ0000000002"
        assert message.venue_extras["clearing_state"] == "1"


class TestSUNCreditCheck:
    def test_legs_group_parsed(self) -> None:
        message = _parse(SUN_PARTY_RISK_LIMIT_CHECK_REQUEST)
        legs = next(
            sf.group
            for sf in message.get_structured_fields()
            if sf.is_group and sf.group.count_field.tag == 555
        )
        assert len(legs.entries) == 2
        # The per-leg opposite amount (9622) must stay inside its leg.
        assert [f.tag for f in legs.entries[0].fields] == [685, 9622, 588, 566]

    def test_economics_from_legs(self, handler: ThreeSixtyTSUNHandler) -> None:
        trade = handler.extract_trade(_parse(SUN_PARTY_RISK_LIMIT_CHECK_REQUEST))
        assert trade.is_swap is True
        assert trade.settlement_date == "20260608"
        assert trade.far_settlement_date == "20260708"
        assert trade.near_leg_price == pytest.approx(1.083800)
        assert trade.far_leg_price == pytest.approx(1.085034)
        assert trade.near_quantity == pytest.approx(4_000_000.0)
        assert trade.far_quantity == pytest.approx(4_000_000.0)
        # No order quantity on a credit check — the amount under check is 2324.
        assert trade.quantity == pytest.approx(4_000_000.0)

    def test_links_to_the_fill(self) -> None:
        message = _autodetect(SUN_PARTY_RISK_LIMIT_CHECK_REQUEST)
        assert message.venue_extras["credit_check_fill_id"] == "EMSO-6565116"
        assert message.venue_extras["risk_limit_check_request_id"] == "RLC-0000001"


class TestSUNSecurityDefinition:
    def test_calendar_entries(self) -> None:
        message = _parse(SUN_SECURITY_DEFINITION)
        underlyings = next(
            sf.group
            for sf in message.get_structured_fields()
            if sf.is_group and sf.group.count_field.tag == 711
        )
        assert len(underlyings.entries) == 3
        first = {f.tag: f.raw_value for f in underlyings.entries[0].fields}
        assert first[309] == "SP-1W"
        assert first[542] == "20260608"  # near-leg value date
        assert first[9612] == "20260615"  # far-leg value date


class TestSUNMarketData:
    def test_book_entries(self) -> None:
        message = _parse(SUN_MARKET_DATA_SNAPSHOT)
        entries = next(
            sf.group
            for sf in message.get_structured_fields()
            if sf.is_group and sf.group.count_field.tag == 268
        )
        assert len(entries.entries) == 3
        types = [
            f.value_description for entry in entries.entries for f in entry.fields if f.tag == 269
        ]
        assert types == ["Bid", "Offer", "Mid-price"]

    def test_quote_type_decodes(self) -> None:
        message = _parse(SUN_MARKET_DATA_SNAPSHOT)
        quote_types = [f.value_description for f in message.fields if f.tag == 1070]
        assert (
            quote_types[0] == "Tradable (mid entries: active interest with a credit relationship)"
        )
        assert quote_types[-1] == "Indicative"


class TestSUNStripOrder:
    def test_orders_group_splits_per_order(self) -> None:
        message = _parse(SUN_NEW_ORDER_LIST)
        orders = next(
            sf.group
            for sf in message.get_structured_fields()
            if sf.is_group and sf.group.count_field.tag == 73
        )
        assert len(orders.entries) == 2
        by_entry = [{f.tag: f.raw_value for f in entry.fields} for entry in orders.entries]
        assert [e[11] for e in by_entry] == ["CL-SUN-S1", "CL-SUN-S2"]
        assert [e[193] for e in by_entry] == ["20260708", "20260908"]
        assert [e[44] for e in by_entry] == ["12.34", "24.10"]
        # The nested party group stays inside its order.
        assert by_entry[0][448] == "ACMEUSER1"


class TestSUNEFP:
    def test_futures_leg_fields(self) -> None:
        message = _parse(SUN_EFP_ORDER_ACK)
        assert message.get_value(48) == "ECM6"
        assert message.get_field(22).value_description == "Exchange symbol"
        assert message.get_value(5241) == "20260613"

    def test_far_quantity_is_contract_count(self, handler: ThreeSixtyTSUNHandler) -> None:
        trade = handler.extract_trade(_parse(SUN_EFP_ORDER_ACK))
        assert trade.quantity == pytest.approx(5_000_000.0)
        assert trade.far_quantity == pytest.approx(40.0)
