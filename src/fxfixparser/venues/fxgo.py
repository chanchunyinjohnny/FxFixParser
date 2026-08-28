"""Bloomberg FXGO venue handler.

Covers Bloomberg's three plain-FIX 4.4 FXGO interfaces, which share one
dialect and CompID (``BLP`` on the Bloomberg side, bilaterally-agreed on the
counterparty side):

- **FIXBOOK for Liquidity Providers**: streaming / RFS quoting, market data,
  batch RFQ, orders and executions between Bloomberg and price makers.
- **FXGO Algo (FXOM)**: algo order routing between Bloomberg and makers.
- **FXGO STP**: post-trade drop copy / allocation notification for all FX
  products including FX options.

The ORP/DOR order-routing protocol is the adjacent **Bloomberg DOR** venue —
FIXT.1.1/FIX 5.0 (or the MAP gateway's FIX 4.4 flavor) with its own CompIDs
(``BLPORP*`` / ``MAP_BLP*``) and routing markers, claimed by
``BloombergDORHandler`` before CompID matching reaches this handler. All
Bloomberg interfaces share one custom-tag space, so this handler layers the
FXGO-specific definitions over the shared Bloomberg core.
"""

from fxfixparser.core.field import FixFieldDefinition
from fxfixparser.core.message import FixMessage, ParsedTrade
from fxfixparser.venues.base import VenueHandler, _to_float
from fxfixparser.venues.bloomberg_dor import BLOOMBERG_CUSTOM_TAGS
from fxfixparser.venues.fxgo_tags import FXGO_CUSTOM_TAGS


class FXGOHandler(VenueHandler):
    """Handler for Bloomberg FXGO FIX messages."""

    @property
    def name(self) -> str:
        return "Bloomberg FXGO"

    @property
    def sender_comp_ids(self) -> list[str]:
        # BLP is the Bloomberg-side CompID fixed by the FIXBOOK and Algo
        # (FXOM) specs; the others are conventional aliases.
        return ["BLP", "FXGO", "BLOOMBERG", "BBG", "BFXGO"]

    @property
    def custom_tags(self) -> list[FixFieldDefinition]:
        """FXGO tag definitions layered over the shared Bloomberg core.

        ORP/DOR, FIXBOOK, Algo and STP are dialects of one Bloomberg tag
        space, so the DOR core (tenors, swap points, competing dealer
        quotes, regulatory IDs, reference prices, ...) applies here too;
        the FXGO-specific definitions win where both define a tag.
        """
        return list({**BLOOMBERG_CUSTOM_TAGS, **FXGO_CUSTOM_TAGS}.values())

    @property
    def enum_extensions(self) -> dict[int, dict[str, str]]:
        """Bloomberg-specific enum codes that extend standard FIX fields."""
        return {
            # PartySubIDType: Bloomberg private codes (same as DOR) — 4025
            # marks an LEI, 4046/4047 flag the party's liquidity role.
            803: {
                "4025": "Legal Entity Identifier",
                "4046": "Liquidity maker",
                "4047": "Liquidity taker",
            },
            # PartyRole: MiFID II investment-decision maker entries on
            # FIXBOOK batch messages.
            452: {"122": "Investment decision maker"},
            # TrdType: securities-financing indicator on regulatory trades.
            828: {"47": "Financing transaction"},
            # MiscFeeType: STP fee entries use the FIX 5.0 Markup code.
            139: {"8": "Markup (see MiscFeeRate (2216) / MiscFeeDesc (2713))"},
        }

    def _extract_quote_info(self, message: FixMessage, trade: ParsedTrade) -> None:
        """Extract FXGO quote info.

        FXGO swap quotes price both legs as flat all-in rates — BidPx (132) /
        OfferPx (133) for the near leg and the custom BidPx2 (6050) /
        OfferPx2 (6051) for the far leg — rather than the LFX custom tags or
        a NoLegs group the base extractor understands, so map those onto the
        leg-rate slots and derive swap points from them.
        """
        super()._extract_quote_info(message, trade)

        if not trade.is_swap:
            return

        if trade.near_leg_bid_rate is None:
            trade.near_leg_bid_rate = trade.bid_price
        if trade.near_leg_offer_rate is None:
            trade.near_leg_offer_rate = trade.offer_price
        if trade.far_leg_bid_rate is None:
            trade.far_leg_bid_rate = _to_float(message.get_value(6050))
        if trade.far_leg_offer_rate is None:
            trade.far_leg_offer_rate = _to_float(message.get_value(6051))

        # Swap points from the all-in rates (far - near), unless the venue
        # declared them explicitly (1065/1066 — handled by the base).
        if trade.bid_swap_points is None and trade.offer_swap_points is None:
            if trade.far_leg_bid_rate is not None and trade.near_leg_bid_rate is not None:
                trade.bid_swap_points = trade.far_leg_bid_rate - trade.near_leg_bid_rate
            if trade.far_leg_offer_rate is not None and trade.near_leg_offer_rate is not None:
                trade.offer_swap_points = trade.far_leg_offer_rate - trade.near_leg_offer_rate
            if trade.bid_swap_points is not None or trade.offer_swap_points is not None:
                trade.swap_points_source = "computed"
