"""Streamlit UI application for FxFixParser."""

from typing import Any

import streamlit as st

from fxfixparser.core.exceptions import ChecksumError, ParseError, ValidationError
from fxfixparser.core.fx_math import pip_size
from fxfixparser.core.parser import FixParser, ParserConfig
from fxfixparser.products.base import ProductRegistry
from fxfixparser.venues.registry import VenueRegistry

SAMPLE_MESSAGES = {
    "FX Spot (Execution Report)": (
        "8=FIX.4.4|9=200|35=8|49=FXGO|56=CLIENT|34=1|52=20240115-10:30:00|"
        "37=ORD001|17=EXEC001|150=F|39=2|55=EUR/USD|54=1|32=1000000|31=1.0850|"
        "15=EUR|64=20240117|60=20240115-10:30:00|10=123|"
    ),
    "FX Forward": (
        "8=FIX.4.4|9=220|35=8|49=360T|56=CLIENT|34=1|52=20240115-10:30:00|"
        "37=ORD002|17=EXEC002|150=F|39=2|55=EUR/USD|167=FXFWD|54=1|32=5000000|"
        "31=1.0900|15=EUR|64=20240415|194=1.0850|195=0.0050|60=20240115-10:30:00|10=045|"
    ),
    "FX Swap": (
        "8=FIX.4.4|9=250|35=8|49=SMARTTRADE|56=CLIENT|34=1|52=20240115-10:30:00|"
        "37=ORD003|17=EXEC003|150=F|39=2|55=USD/JPY|167=FXSWAP|54=1|32=10000000|"
        "31=148.50|15=USD|64=20240117|193=20240415|192=10000000|194=148.50|"
        "195=0.50|60=20240115-10:30:00|10=178|"
    ),
    "FX NDF": (
        "8=FIX.4.4|9=230|35=8|49=FXGO|56=CLIENT|34=1|52=20240115-10:30:00|"
        "37=ORD004|17=EXEC004|150=F|39=2|55=USD/KRW|167=FXNDF|54=1|32=5000000|"
        "31=1320.50|15=USD|64=20240415|120=USD|60=20240115-10:30:00|10=092|"
    ),
    "Market Data Snapshot (4 entries)": (
        "8=FIX.4.4|9=350|35=W|49=LFX|56=CLIENT|34=100|52=20240115-10:30:00|"
        "262=MD001|55=EUR/USD|268=4|"
        "269=0|270=1.08500|271=5000000|272=20240115|273=10:30:00|278=BID001|"
        "269=0|270=1.08490|271=3000000|272=20240115|273=10:30:00|278=BID002|"
        "269=1|270=1.08510|271=4000000|272=20240115|273=10:30:00|278=ASK001|"
        "269=1|270=1.08520|271=2000000|272=20240115|273=10:30:00|278=ASK002|"
        "10=045|"
    ),
    "Market Data Incremental (7 entries)": (
        "8=FIX.4.4|9=0853|35=X|49=LFX|56=CLIENT|34=3|52=20190307-15:20:20.427|"
        "262=MDReqID_1|55=GBP/USD|64=20190311|268=7|"
        "279=1|269=0|278=b-47005814236839174-3|280=2BNP51|270=1.31013|"
        "272=20190307|273=15:20:20.307|290=2|"
        "279=1|269=0|278=b-47005814236839174-4|280=2BNP52|270=1.3101|"
        "272=20190307|273=15:20:20.307|290=3|"
        "279=1|269=0|278=b-47005814236839174-8|280=2BNP53|270=1.31006|"
        "272=20190307|273=15:20:20.307|290=7|"
        "279=1|269=1|278=o-47005814236839174-1|280=2BNP51|270=1.31026|"
        "272=20190307|273=15:20:20.307|290=0|"
        "279=1|269=1|278=o-47005814236839174-2|280=2BNP52|270=1.31029|"
        "272=20190307|273=15:20:20.307|290=1|"
        "279=0|269=1|278=o-47005814236839174-6|280=2BNP53|270=1.31035|"
        "271=10000000|15=GBP|272=20190307|273=15:20:20.307|276=A|282=QPU08|290=5|"
        "279=2|269=1|280=7COBA0O3|10=028|"
    ),
    "Quote Request (Multiple Symbols)": (
        "8=FIX.4.4|9=200|35=R|49=CLIENT|56=FXGO|34=1|52=20240115-10:30:00|"
        "131=QR001|146=2|"
        "55=EUR/USD|38=1000000|64=20240117|"
        "55=GBP/USD|38=2000000|64=20240118|"
        "10=123|"
    ),
    "FX Swap Quote (TOD/TOM)": (
        "8=FIX.4.4|9=417|35=S|34=12580|49=LFX_CORE|52=20260123-01:19:02.336|"
        "56=UAT.ATP.RFS.MKT|55=AUD/USD|63=TOD|64=20260123|117=4gDjtXF7bvj|"
        "131=REQ_714044745123106816|132=0.6845|133=0.684565|134=1000000|135=1000000|"
        "188=0.68449|189=0.00001|190=0.68459|191=-0.000025|193=20260127|"
        "642=0.000001|643=-0.000003|1065=-0.000009|1066=0.000022|8004=TOM|"
        "8011=0.68449|8012=0.68459|8013=1000000|8014=1000000|"
        "8019=0.684491|8020=0.684587|8021=AUD|8022=USD|10=208|"
    ),
    "Bloomberg DOR: FX Spot Execution": (
        "8=FIXT.1.1|9=300|35=8|49=BLOOMBERG_DOR|56=CLIENT|34=1|"
        "52=20240115-10:30:00|115=DOR|"
        "37=ORD100|11=CL100|17=EXEC100|150=F|39=2|"
        "55=EUR/USD|167=FXSPOT|460=4|54=1|15=EUR|"
        "32=1000000|31=1.08500|194=1.08500|"
        "64=20240117|75=20240115|120=USD|"
        "1056=1085000|22262=USD|"
        "60=20240115-10:30:00|10=000|"
    ),
    "Bloomberg DOR: FX Forward Execution": (
        "8=FIXT.1.1|9=320|35=8|49=BLOOMBERG_DOR|56=CLIENT|34=2|"
        "52=20240115-10:31:00|115=DOR|"
        "37=ORD101|11=CL101|17=EXEC101|150=F|39=2|"
        "55=EUR/USD|167=FXFWD|460=4|54=1|15=EUR|"
        "32=5000000|31=1.09000|194=1.08500|195=0.00500|"
        "64=20240715|63=6M|75=20240115|120=USD|"
        "6215=M6|1056=5450000|22262=USD|"
        "60=20240115-10:31:00|10=000|"
    ),
    "Bloomberg DOR: FX Swap Execution": (
        "8=FIXT.1.1|9=500|35=8|49=BLOOMBERG_DOR|56=CLIENT|34=3|"
        "52=20240115-10:32:00|115=DOR|"
        "37=ORD102|11=CL102|17=EXEC102|150=F|39=2|"
        "55=EUR/USD|167=FXSWAP|460=4|40=G|54=1|15=EUR|"
        "32=10000000|31=1.08500|194=1.08500|1071=0.00500|"
        "75=20240115|120=USD|"
        "555=2|"
        "600=EUR/USD|609=FXSPOT|624=1|556=EUR|"
        "587=0|588=20240117|637=1.08500|1788=1|"
        "600=EUR/USD|609=FXFWD|624=2|556=EUR|"
        "587=M3|588=20240415|637=1.09000|1788=2|"
        "60=20240115-10:32:00|10=000|"
    ),
    "360T RFS: Spot Quote Request": (
        "8=FIX.4.4|9=0|35=R|49=CLIENT|56=360T|34=1|52=20240115-10:30:00|"
        "131=QR-SPOT-1|7070=20240117|7071=FX-STD|7611=3|146=1|55=EUR/USD|537=1|"
        "54=1|38=1000000|64=20240117|15=EUR|1=ACME|126=20240115-12:13:55|10=000|"
    ),
    "360T RFS: Swap Quote (Two-Way)": (
        "8=FIX.4.4|9=0|35=S|49=360T|56=CLIENT|34=3|52=20240115-10:30:05|"
        "1=ACME|15=EUR|38=1000000|55=EUR/USD|106=BANKA|117=Q-1|131=QR-SWAP-1|"
        "132=1.08490|133=1.08510|188=1.08480|190=1.08520|192=1000000|"
        "6050=1.08560|6051=1.08590|7070=20240117|7071=FX-STD|10=000|"
    ),
    "360T RFS: Forward Execution": (
        "8=FIX.4.4|9=0|35=8|49=360T|56=CLIENT|34=5|52=20240115-10:31:00|"
        "1=ACME|6=0|11=CL-FWD-1|14=5000000|15=EUR|17=EX-FWD-1|31=1.09000|32=5000000|"
        "37=ORD-FWD-1|38=5000000|39=2|40=D|44=1.09000|54=1|55=EUR/USD|"
        "60=20240115-10:31:00|64=20240415|106=BANKA|117=Q-9|150=F|151=0|"
        "194=1.08500|7070=20240115|7071=FX-STD|10=000|"
    ),
    "360T RFS: Swap Execution": (
        "8=FIX.4.4|9=0|35=8|49=360T|56=CLIENT|34=6|52=20240115-10:32:00|"
        "1=ACME|6=0|11=CL-SWAP-1|14=10000000|15=EUR|17=EX-SWAP-1|31=1.08400|32=10000000|"
        "37=ORD-SWAP-1|38=10000000|39=2|40=D|44=1.08400|54=1|55=EUR/USD|"
        "60=20240115-10:32:00|64=20240117|117=Q-10|150=F|151=0|"
        "192=10000000|193=20240417|194=1.08380|640=1.08490|6160=1.08500|"
        "7070=20240115|7071=FX-STD|10=000|"
    ),
    "360T RFS: NDF Execution": (
        "8=FIX.4.4|9=0|35=8|49=360T|56=CLIENT|34=7|52=20240115-10:33:00|"
        "1=ACME|6=0|11=CL-NDF-1|14=5000000|15=USD|17=EX-NDF-1|31=1320.50|32=5000000|"
        "37=ORD-NDF-1|38=5000000|39=2|40=D|44=1320.50|54=1|55=USD/KRW|"
        "60=20240115-10:33:00|541=20240413|64=20240417|117=Q-11|150=F|151=0|"
        "194=1320.50|7070=20240115|7071=FX-STD|10=000|"
    ),
    # 360T TradeImporter (TI) — post-trade STP ExecutionReports. These are
    # synthetic/sanitized samples: CompIDs use the _TI suffix, ProductType(7071)
    # carries the product directly, and competing-dealer quotes ride in
    # NoCompetingQuotes(9516).
    "360T TI: Spot Execution": (
        "8=FIX.4.4|9=0|35=8|34=541|49=CLIENT_TI|52=20190731-10:40:36|56=360T_TI|"
        "6=1.11455|14=0|15=EUR|17=TI-SPOT-EXEC|31=1.11455|32=0|37=TI-SPOT-ORD|"
        "38=500000.00|39=2|54=2|55=EUR/USD|60=20190731-10:40:36.300|64=20190802|"
        "75=20190731|150=F|151=0|194=1.11455|7071=FX-SPOT|"
        "453=3|448=CLIENTCO|447=D|452=1|802=2|523=CLIENT.TRADER1|803=2|"
        "523=CLIENTCO|803=1|"
        "448=BANKA.TI|447=D|452=35|802=1|523=BANKA.AUTO|803=2|"
        "448=CLIENTCO|447=D|452=33|"
        "9516=2|9517=BANKA.TI|9518=1.11455|9522=1.11455|9526=0.00|"
        "9517=BANKC.TI|9518=1.11445|9522=1.11445|9526=44.86|10=185|"
    ),
    "360T TI: Forward Execution": (
        "8=FIX.4.4|9=0|35=8|34=545|49=CLIENT_TI|52=20190731-10:42:32|56=360T_TI|"
        "6=0.91572|14=0|15=EUR|17=TI-FWD-EXEC|22=4|29=4|31=0.9166215|32=0|"
        "37=TI-FWD-ORD|38=250000.00|39=2|48=SYNFWD000001|54=2|55=EUR/GBP|"
        "60=20190731-10:42:31.782|"
        "64=20190902|75=20190731|150=F|151=0|194=0.91572|7071=FX-FWD|7611=3|"
        "7612=360T|7653=UTI-FWD-001|"
        "453=3|448=360T|447=G|452=64|448=CLIENTCO|447=D|452=1|"
        "448=BANKA.TI|447=D|452=35|"
        "1907=1|1903=UTI-FWD-001|1906=5|"
        "2668=2|2669=0|2670=4|2669=1|2670=4|10=204|"
    ),
    "360T TI: Swap Execution": (
        "8=FIX.4.4|9=0|35=8|34=563|49=360T_TI|52=20190731-10:51:03.893|56=CLIENT_TI|"
        "37=TI-SWAP-ORD|17=TI-SWAP-EXEC|150=F|39=2|64=20190802|55=GBP/USD|"
        "48=SYNSWP000001|22=4|454=2|455=SYNSWPLEG001|456=4|455=SYNSWPLEG002|"
        "456=4|54=2|38=22121.00|"
        "15=GBP|32=0|31=1.2168000|194=1.21680|29=4|151=0|14=0|6=1.21680|75=20190731|"
        "60=20190731-10:48:08.630|828=65|193=20200203|192=22121.00|6160=1.2270200|"
        "7071=FX-SWAP|7653=UTI-SWAP-001|7659=UTI-SWAP-001-N|"
        "7660=UTI-SWAP-001-F|7611=3|7612=360T|"
        "9516=2|9517=BANKA.TI|9518=1.2168000|9520=1.2270200|9522=1.21680|"
        "9524=1.2170500|9525=1.2273050|9526=0.00|9517=BANKB.TI|"
        "9518=1.2168000|9520=1.2270200|9526=0.00|10=006|"
    ),
    "360T TI: Money Market (Deposit)": (
        "8=FIX.4.4|9=0|35=8|34=2|49=CLIENT_TI|52=20190731-11:28:10|56=360T_TI|"
        "6=-0.3900000000|14=0|15=EUR|17=TI-MM-EXEC|31=-0.3900000000|32=0|"
        "37=TI-MM-ORD|"
        "38=1000000.00|39=2|54=F|55=EUR|60=20190731-11:28:07.017|64=20190802|"
        "75=20190731|150=F|151=0|193=20190902|7071=MM|"
        "453=2|448=CLIENTCO|447=D|452=1|448=BANKA.TI|447=D|452=35|10=052|"
    ),
    "360T TI: Option Execution": (
        "8=FIX.4.4|9=0|35=8|34=7|49=CLIENT_TI|52=20190731-11:30:39|56=360T_TI|"
        "6=0.00000|14=0|15=EUR|17=TI-OPT-EXEC|22=4|29=4|32=0|37=TI-OPT-ORD|"
        "38=100000.00|39=2|48=SYNOPT000001|54=1|55=EUR/USD|"
        "60=20190731-11:30:38.610|64=20190802|"
        "75=20190731|150=F|151=0|192=160.00|194=0.00000|6160=0.00|7071=FX-OPTION|"
        "201=1|202=1.12000|541=20190830|947=USD|697=8.5|7611=3|7612=360T|"
        "7653=UTI-OPT-001|"
        "453=2|448=CLIENTCO|447=D|452=1|448=BANKA.TI|447=D|452=35|10=003|"
    ),
}


def _render_swap_trade_summary(trade: Any, message: Any) -> None:
    """Render the swap-specific Trade Summary block.

    Shows side interpretation, spot rate, swap points (with pips), and a
    side-by-side near/far leg breakdown.
    """
    st.subheader("Trade Summary — FX Swap")

    # Headline metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Symbol", trade.symbol or "N/A")
    with col2:
        st.metric("Trade Currency", trade.trade_currency or "N/A")
    with col3:
        st.metric("Side", trade.side or "N/A")
    with col4:
        st.metric("Venue", trade.venue or "N/A")

    # Side interpretation — explains what Buy/Sell means in terms of legs
    if trade.near_leg_action and trade.far_leg_action:
        st.markdown(
            f"**Interpretation:** Near leg → *{trade.near_leg_action}*"
            f" &nbsp;·&nbsp; Far leg → *{trade.far_leg_action}*"
        )
        if trade.swap_side_source == "legs":
            st.caption("Source: explicit per-leg LegSide (tag 624) in the NoLegs (555) group.")
        elif trade.swap_side_source == "parent":
            st.caption(
                "Convention: order Side (54) describes the action on the far leg"
                " in the trade currency; the near leg is the opposite."
            )
        elif trade.swap_side_source == "360t":
            st.caption(
                "Convention (360T): Side (54) is relative to the base currency"
                " on the far leg; the near leg is the opposite."
            )

    # Pricing — spot rate, swap points (with pips), price precision
    px_fmt = "{:.5f}"
    pts_fmt = "{:+.6f}"
    pips_fmt = "{:+.2f}"

    pricing_cols = st.columns(3)
    with pricing_cols[0]:
        st.metric(
            "Spot Rate",
            px_fmt.format(trade.spot_rate) if trade.spot_rate is not None else "N/A",
        )
    with pricing_cols[1]:
        # FX convention quotes swap points in pips (e.g. +15.01), so pips
        # lead; the raw far-minus-near rate differential goes on the
        # secondary line. Falls back to rate terms when the pip size is
        # unknown for the symbol.
        if trade.swap_points_pips is not None:
            pts_value = f"{pips_fmt.format(trade.swap_points_pips)} pips"
            pts_delta = (
                f"{pts_fmt.format(trade.swap_points)} rate terms"
                if trade.swap_points is not None
                else None
            )
        else:
            pts_value = (
                pts_fmt.format(trade.swap_points) if trade.swap_points is not None else "N/A"
            )
            pts_delta = None
        # ``delta_color="off"`` keeps the secondary line neutral grey
        # rather than colouring positive points green / negative red —
        # swap points have no intrinsic good/bad direction.
        st.metric("Swap Points", pts_value, delta=pts_delta, delta_color="off")
    with pricing_cols[2]:
        st.metric("Product", message.product_type or "N/A")

    # Near vs Far leg breakdown
    st.markdown("#### Legs")

    def _fmt_qty(q: float | None) -> str:
        return f"{q:,.2f}" if q is not None else "N/A"

    def _fmt_px(p: float | None) -> str:
        return px_fmt.format(p) if p is not None else "N/A"

    legs_data = {
        "": ["Settlement Date", "Quantity", "Price (All-in)", "Action"],
        "Near Leg": [
            trade.settlement_date or "N/A",
            _fmt_qty(trade.near_quantity),
            _fmt_px(trade.near_leg_price),
            trade.near_leg_action or "N/A",
        ],
        "Far Leg": [
            trade.far_settlement_date or "N/A",
            _fmt_qty(trade.far_quantity),
            _fmt_px(trade.far_leg_price),
            trade.far_leg_action or "N/A",
        ],
    }
    st.dataframe(legs_data, use_container_width=True, hide_index=True)


def main() -> None:
    """Main entry point for the Streamlit application."""
    st.set_page_config(
        page_title="FX FIX Parser",
        page_icon="",
        layout="wide",
    )

    st.title("FX FIX Message Parser")
    st.markdown("Parse FIX protocol messages for FX trading")

    # Get available venues
    venue_registry = VenueRegistry.default()
    venue_names = ["Auto-detect"] + [v.name for v in venue_registry.all_venues()]

    # Sidebar configuration
    with st.sidebar:
        st.header("Settings")
        strict_checksum = st.checkbox("Strict Checksum Validation", value=False)
        strict_body_length = st.checkbox("Strict Body Length Validation", value=False)

        st.divider()
        st.header("Venue")
        selected_venue = st.selectbox(
            "Select Venue (optional)",
            options=venue_names,
            index=0,
            help=(
                "Select a venue to use venue-specific tag definitions. "
                "Different venues may define custom tags differently."
            ),
        )

        st.divider()
        st.header("Table Columns")
        show_tag = st.checkbox("Tag", value=True)
        show_field = st.checkbox("Field", value=True)
        show_field_desc = st.checkbox("Field Description", value=True)
        show_value = st.checkbox("Value", value=True)
        show_value_desc = st.checkbox("Value Description", value=True)

        st.divider()
        st.header("Sample Messages")
        with st.expander("Load a sample message"):
            for name, msg in SAMPLE_MESSAGES.items():
                if st.button(name, key=f"sample_{name}"):
                    st.session_state["fix_message"] = msg

    # Main input area
    fix_input = st.text_area(
        "Paste your FIX message here:",
        value=st.session_state.get("fix_message", ""),
        height=150,
        placeholder="8=FIX.4.4|9=...|35=8|...|10=XXX|",
    )

    col1, col2 = st.columns([1, 5])
    with col1:
        parse_button = st.button("Parse Message", type="primary")

    if parse_button and fix_input:
        config = ParserConfig(
            strict_checksum=strict_checksum,
            strict_body_length=strict_body_length,
        )
        parser = FixParser(config=config)
        product_registry = ProductRegistry.default()

        # Determine venue to use
        venue_to_use = None if selected_venue == "Auto-detect" else selected_venue

        try:
            message = parser.parse(fix_input, venue=venue_to_use, auto_detect_venue=True)

            # Resolve the venue handler. The parser sets message.venue for
            # both an explicit venue and one auto-detected from the comp IDs.
            venue_handler = venue_registry.get(message.venue) if message.venue else None

            # Detect product type. Prefer a venue-derived product_type (set by
            # the venue handler's enhance_message, e.g. 360T which sends no
            # SecurityType) over the generic registry; fall back otherwise.
            product_handler = product_registry.detect(message)
            if product_handler and not message.product_type:
                message.product_type = product_handler.product_type

            st.success("Message parsed successfully!")

            # Display tabs for different output formats
            tab1, tab2, tab3 = st.tabs(["Table View", "Human Readable", "JSON"])

            with tab1:
                st.subheader("Parsed Fields")

                # Get structured fields with repeating groups
                structured_fields = message.get_structured_fields()

                # Display standard (non-group) fields first at the top
                table_data = []
                for sf in structured_fields:
                    if not sf.is_group and sf.field:
                        field = sf.field
                        row: dict[str, Any] = {}
                        if show_tag:
                            row["Tag"] = field.tag
                        if show_field:
                            row["Field"] = field.name
                        if show_field_desc:
                            row["Field Description"] = field.description or ""
                        if show_value:
                            row["Value"] = field.raw_value
                        if show_value_desc:
                            row["Value Description"] = field.value_description or ""
                        table_data.append(row)

                if table_data:
                    st.dataframe(
                        table_data,
                        use_container_width=True,
                        hide_index=True,
                    )

                # Display repeating groups below the standard fields
                for sf in structured_fields:
                    if sf.is_group and sf.group:
                        group = sf.group
                        st.markdown(
                            f"### {group.count_field.name} ({group.count_field.tag}): "
                            f"{group.count} entries"
                        )

                        for entry in group.entries:
                            with st.expander(f"Entry {entry.index}", expanded=True):
                                entry_data = []
                                for field in entry.fields:
                                    entry_row: dict[str, Any] = {}
                                    if show_tag:
                                        entry_row["Tag"] = field.tag
                                    if show_field:
                                        entry_row["Field"] = field.name
                                    if show_field_desc:
                                        entry_row["Field Description"] = field.description or ""
                                    if show_value:
                                        entry_row["Value"] = field.raw_value
                                    if show_value_desc:
                                        entry_row["Value Description"] = (
                                            field.value_description or ""
                                        )
                                    entry_data.append(entry_row)

                                if entry_data:
                                    st.dataframe(
                                        entry_data,
                                        use_container_width=True,
                                        hide_index=True,
                                    )

            with tab2:
                st.subheader("Human Readable Format")
                st.code(message.to_human_readable(), language=None)

            with tab3:
                st.subheader("JSON Output")
                st.json(message.to_dict())

            # Trade / Quote summary — only rendered for economic messages.
            # Administrative messages (SecurityDefinition 35=d,
            # SecurityDefinitionRequest 35=c, QuoteCancel 35=Z, QuoteRequestReject
            # 35=AG, News, BusinessMessageReject) carry no product_type; a trade
            # panel for them is a wall of N/A that reads as a parse failure, so we
            # surface a short note instead. This gate is venue-universal: across
            # every supported venue product_type is set for economic messages
            # (quotes / RFQs / executions / trade captures) and is None only for
            # these non-economic types.
            if venue_handler and message.product_type is None:
                st.divider()
                msg_type_field = message.get_field(35)
                type_label = (
                    msg_type_field.value_description
                    if msg_type_field and msg_type_field.value_description
                    else f"MsgType {message.msg_type}"
                )
                st.info(
                    f"**{type_label}** is a non-economic message — no trade "
                    "summary. See the parsed tags above for its contents."
                )
            elif venue_handler:
                st.divider()
                trade = venue_handler.extract_trade(message)

                if trade.is_quote:
                    # Display quote information in industry-standard format
                    st.subheader("Quote Summary")

                    # Basic info
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Symbol", trade.symbol or "N/A")
                    with col2:
                        st.metric("Currency", trade.currency or "N/A")
                    with col3:
                        st.metric("Quantity", f"{trade.quantity:,.0f}" if trade.quantity else "N/A")
                    with col4:
                        st.metric("Product", message.product_type or "N/A")

                    # Pricing table - industry standard format
                    st.markdown("#### Pricing")

                    # Explain bid/offer from both perspectives
                    if trade.symbol:
                        base_ccy = (
                            trade.symbol.split("/")[0] if "/" in trade.symbol else trade.symbol[:3]
                        )
                        quote_ccy = (
                            trade.symbol.split("/")[1] if "/" in trade.symbol else trade.symbol[3:]
                        )
                        st.caption(
                            f"**Bid**: Market maker buys {base_ccy}, sells {quote_ccy}"
                            f" (Client sells {base_ccy})"
                        )
                        st.caption(
                            f"**Offer**: Market maker sells {base_ccy}, buys {quote_ccy}"
                            f" (Client buys {base_ccy})"
                        )

                    if trade.is_swap:
                        # Swap quote display
                        # Get tenors from message (display tenor only, not settlement dates)
                        near_tenor = message.get_value(63) or "Near"  # SettlType
                        far_tenor = (
                            message.get_value(8004) or message.get_value(8005) or "Far"
                        )  # FarLegSettlType

                        st.markdown(f"##### {near_tenor} Leg")
                        near_data = {
                            "": ["Bid", "Offer"],
                            "Spot Rate": [
                                f"{trade.bid_spot_rate:.5f}" if trade.bid_spot_rate else "N/A",
                                f"{trade.offer_spot_rate:.5f}" if trade.offer_spot_rate else "N/A",
                            ],
                            "Fwd Points": [
                                f"{trade.bid_fwd_points:+.6f}"
                                if trade.bid_fwd_points is not None
                                else "N/A",
                                f"{trade.offer_fwd_points:+.6f}"
                                if trade.offer_fwd_points is not None
                                else "N/A",
                            ],
                            "All-in Rate": [
                                f"{trade.near_leg_bid_rate:.6f}"
                                if trade.near_leg_bid_rate
                                else (f"{trade.bid_price:.6f}" if trade.bid_price else "N/A"),
                                f"{trade.near_leg_offer_rate:.6f}"
                                if trade.near_leg_offer_rate
                                else (f"{trade.offer_price:.6f}" if trade.offer_price else "N/A"),
                            ],
                        }
                        st.dataframe(near_data, use_container_width=True, hide_index=True)

                        st.markdown(f"##### {far_tenor} Leg")
                        far_data = {
                            "": ["Bid", "Offer"],
                            "Fwd Points": [
                                f"{trade.far_bid_fwd_points:+.6f}"
                                if trade.far_bid_fwd_points is not None
                                else "N/A",
                                f"{trade.far_offer_fwd_points:+.6f}"
                                if trade.far_offer_fwd_points is not None
                                else "N/A",
                            ],
                            "All-in Rate": [
                                f"{trade.far_leg_bid_rate:.6f}"
                                if trade.far_leg_bid_rate
                                else "N/A",
                                f"{trade.far_leg_offer_rate:.6f}"
                                if trade.far_leg_offer_rate
                                else "N/A",
                            ],
                        }
                        st.dataframe(far_data, use_container_width=True, hide_index=True)

                        st.markdown("##### Swap Points")
                        # FX convention quotes swap points in pips; keep the
                        # raw rate differential alongside. Falls back to rate
                        # terms only when the pip size is unknown.
                        ps = pip_size(trade.symbol)
                        bid_pts = trade.bid_swap_points
                        offer_pts = trade.offer_swap_points
                        if ps:
                            swap_data = {
                                "": ["Bid", "Offer"],
                                "Swap Points (pips)": [
                                    f"{bid_pts / ps:+.2f}" if bid_pts is not None else "N/A",
                                    f"{offer_pts / ps:+.2f}" if offer_pts is not None else "N/A",
                                ],
                                "Rate Terms": [
                                    f"{bid_pts:+.6f}" if bid_pts is not None else "N/A",
                                    f"{offer_pts:+.6f}" if offer_pts is not None else "N/A",
                                ],
                            }
                        else:
                            swap_data = {
                                "": ["Bid", "Offer"],
                                "Swap Points": [
                                    f"{bid_pts:+.6f}" if bid_pts is not None else "N/A",
                                    f"{offer_pts:+.6f}" if offer_pts is not None else "N/A",
                                ],
                            }
                        st.dataframe(swap_data, use_container_width=True, hide_index=True)

                    else:
                        # Non-swap quote (spot/forward)
                        quote_data = {
                            "": ["Bid", "Offer"],
                            "Price": [
                                f"{trade.bid_price:.5f}" if trade.bid_price else "N/A",
                                f"{trade.offer_price:.5f}" if trade.offer_price else "N/A",
                            ],
                            "Size": [
                                f"{trade.bid_size:,.0f}" if trade.bid_size else "N/A",
                                f"{trade.offer_size:,.0f}" if trade.offer_size else "N/A",
                            ],
                        }
                        if trade.bid_spot_rate or trade.offer_spot_rate:
                            quote_data["Spot Rate"] = [
                                f"{trade.bid_spot_rate:.5f}" if trade.bid_spot_rate else "N/A",
                                f"{trade.offer_spot_rate:.5f}" if trade.offer_spot_rate else "N/A",
                            ]
                        if trade.bid_fwd_points is not None or trade.offer_fwd_points is not None:
                            quote_data["Fwd Points"] = [
                                f"{trade.bid_fwd_points:+.6f}"
                                if trade.bid_fwd_points is not None
                                else "N/A",
                                f"{trade.offer_fwd_points:+.6f}"
                                if trade.offer_fwd_points is not None
                                else "N/A",
                            ]
                        st.dataframe(quote_data, use_container_width=True, hide_index=True)

                elif trade.is_swap:
                    _render_swap_trade_summary(trade, message)
                else:
                    # Regular trade summary (Execution Report, etc.)
                    st.subheader("Trade Summary")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Symbol", trade.symbol or "N/A")
                        st.metric("Side", trade.side or "N/A")
                    with col2:
                        st.metric("Quantity", f"{trade.quantity:,.2f}" if trade.quantity else "N/A")
                        st.metric("Price", f"{trade.price:.5f}" if trade.price else "N/A")
                    with col3:
                        st.metric("Venue", trade.venue or "N/A")
                        st.metric("Product", message.product_type or "N/A")

                    # Surface FX futures product detail (product_code/name)
                    # when the product handler can supply them. This is
                    # what makes SGX FX futures messages legible — without
                    # this, a KU/KUTM/UC code stays opaque in the UI.
                    if product_handler is not None:
                        details = product_handler.extract_details(message)
                        product_code = details.get("product_code")
                        product_name = details.get("product_name")
                        if product_code or product_name:
                            parts = []
                            if product_code:
                                parts.append(f"**Product Code:** `{product_code}`")
                            if product_name:
                                parts.append(f"**Product Name:** {product_name}")
                            st.caption(" &nbsp;·&nbsp; ".join(parts))

        except ChecksumError as e:
            st.error(f"Checksum Error: {e}")
        except ValidationError as e:
            st.error(f"Validation Error: {e}")
        except ParseError as e:
            st.error(f"Parse Error: {e}")

    elif parse_button:
        st.warning("Please enter a FIX message to parse.")

    # Footer
    st.divider()
    st.markdown("*FxFixParser - MIT License - Author: Chan Chun Yin Johnny*")


if __name__ == "__main__":
    main()
