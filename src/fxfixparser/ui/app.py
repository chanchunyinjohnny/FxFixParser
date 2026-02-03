"""Streamlit UI application for FxFixParser."""

import json

import streamlit as st

from fxfixparser.core.exceptions import ChecksumError, ParseError, ValidationError
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
        "279=1|269=0|278=b-47005814236839174-3|280=2BNP51|270=1.31013|272=20190307|273=15:20:20.307|290=2|"
        "279=1|269=0|278=b-47005814236839174-4|280=2BNP52|270=1.3101|272=20190307|273=15:20:20.307|290=3|"
        "279=1|269=0|278=b-47005814236839174-8|280=2BNP53|270=1.31006|272=20190307|273=15:20:20.307|290=7|"
        "279=1|269=1|278=o-47005814236839174-1|280=2BNP51|270=1.31026|272=20190307|273=15:20:20.307|290=0|"
        "279=1|269=1|278=o-47005814236839174-2|280=2BNP52|270=1.31029|272=20190307|273=15:20:20.307|290=1|"
        "279=0|269=1|278=o-47005814236839174-6|280=2BNP53|270=1.31035|271=10000000|15=GBP|272=20190307|273=15:20:20.307|276=A|282=QPU08|290=5|"
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
}


def main() -> None:
    """Main entry point for the Streamlit application."""
    st.set_page_config(
        page_title="FX FIX Parser",
        page_icon="",
        layout="wide",
    )

    st.title("FX FIX Message Parser")
    st.markdown("Parse FIX 4.4 protocol messages for FX trading")

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
            help="Select a venue to use venue-specific tag definitions. Different venues may define custom tags differently.",
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
            message = parser.parse(fix_input, venue=venue_to_use)

            # If no venue was specified, try to detect from SenderCompID
            if venue_to_use is None:
                venue_handler = venue_registry.get_by_sender_id(message.sender_comp_id)
                if venue_handler:
                    message = venue_handler.enhance_message(message)
            else:
                venue_handler = venue_registry.get(venue_to_use)

            # Detect product type
            product_handler = product_registry.detect(message)
            if product_handler:
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
                        row = {}
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
                    column_config = {}
                    if show_tag:
                        column_config["Tag"] = st.column_config.NumberColumn("Tag", width="small")
                    if show_field:
                        column_config["Field"] = st.column_config.TextColumn("Field", width="medium")
                    if show_field_desc:
                        column_config["Field Description"] = st.column_config.TextColumn("Field Description", width="large")
                    if show_value:
                        column_config["Value"] = st.column_config.TextColumn("Value", width="medium")
                    if show_value_desc:
                        column_config["Value Description"] = st.column_config.TextColumn("Value Description", width="medium")

                    st.dataframe(
                        table_data,
                        use_container_width=True,
                        column_config=column_config,
                        hide_index=True,
                    )

                # Display repeating groups below the standard fields
                for sf in structured_fields:
                    if sf.is_group and sf.group:
                        group = sf.group
                        st.markdown(f"### {group.count_field.name} ({group.count_field.tag}): {group.count} entries")

                        for entry in group.entries:
                            with st.expander(f"Entry {entry.index}", expanded=True):
                                entry_data = []
                                for field in entry.fields:
                                    row = {}
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
                                    entry_data.append(row)

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

            # Trade summary
            if venue_handler:
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
                        base_ccy = trade.symbol.split("/")[0] if "/" in trade.symbol else trade.symbol[:3]
                        quote_ccy = trade.symbol.split("/")[1] if "/" in trade.symbol else trade.symbol[3:]
                        st.caption(f"**Bid**: Market maker buys {base_ccy}, sells {quote_ccy} (Client sells {base_ccy})")
                        st.caption(f"**Offer**: Market maker sells {base_ccy}, buys {quote_ccy} (Client buys {base_ccy})")

                    if trade.is_swap:
                        # Swap quote display
                        # Get tenors from message (display tenor only, not settlement dates)
                        near_tenor = message.get_value(63) or "Near"  # SettlType
                        far_tenor = message.get_value(8004) or message.get_value(8005) or "Far"  # FarLegSettlType

                        st.markdown(f"##### {near_tenor} Leg")
                        near_data = {
                            "": ["Bid", "Offer"],
                            "Spot Rate": [
                                f"{trade.bid_spot_rate:.5f}" if trade.bid_spot_rate else "N/A",
                                f"{trade.offer_spot_rate:.5f}" if trade.offer_spot_rate else "N/A",
                            ],
                            "Fwd Points": [
                                f"{trade.bid_fwd_points:+.6f}" if trade.bid_fwd_points is not None else "N/A",
                                f"{trade.offer_fwd_points:+.6f}" if trade.offer_fwd_points is not None else "N/A",
                            ],
                            "All-in Rate": [
                                f"{trade.near_leg_bid_rate:.6f}" if trade.near_leg_bid_rate else (f"{trade.bid_price:.6f}" if trade.bid_price else "N/A"),
                                f"{trade.near_leg_offer_rate:.6f}" if trade.near_leg_offer_rate else (f"{trade.offer_price:.6f}" if trade.offer_price else "N/A"),
                            ],
                        }
                        st.dataframe(near_data, use_container_width=True, hide_index=True)

                        st.markdown(f"##### {far_tenor} Leg")
                        far_data = {
                            "": ["Bid", "Offer"],
                            "Fwd Points": [
                                f"{trade.far_bid_fwd_points:+.6f}" if trade.far_bid_fwd_points is not None else "N/A",
                                f"{trade.far_offer_fwd_points:+.6f}" if trade.far_offer_fwd_points is not None else "N/A",
                            ],
                            "All-in Rate": [
                                f"{trade.far_leg_bid_rate:.6f}" if trade.far_leg_bid_rate else "N/A",
                                f"{trade.far_leg_offer_rate:.6f}" if trade.far_leg_offer_rate else "N/A",
                            ],
                        }
                        st.dataframe(far_data, use_container_width=True, hide_index=True)

                        st.markdown("##### Swap Points")
                        swap_data = {
                            "": ["Bid", "Offer"],
                            "Swap Points": [
                                f"{trade.bid_swap_points:+.6f}" if trade.bid_swap_points is not None else "N/A",
                                f"{trade.offer_swap_points:+.6f}" if trade.offer_swap_points is not None else "N/A",
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
                                f"{trade.bid_fwd_points:+.6f}" if trade.bid_fwd_points is not None else "N/A",
                                f"{trade.offer_fwd_points:+.6f}" if trade.offer_fwd_points is not None else "N/A",
                            ]
                        st.dataframe(quote_data, use_container_width=True, hide_index=True)

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
    st.markdown(
        "*FxFixParser - MIT License - Author: Chan Chun Yin Johnny*"
    )


if __name__ == "__main__":
    main()
