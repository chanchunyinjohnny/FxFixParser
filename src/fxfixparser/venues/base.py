"""Abstract base class for venue handlers."""

from abc import ABC, abstractmethod

from fxfixparser.core.field import FixFieldDefinition
from fxfixparser.core.fx_math import parse_symbol, pip_size, swap_side_actions
from fxfixparser.core.message import FixMessage, ParsedTrade


def _to_float(value: str | None) -> float | None:
    """Parse a tag value as float, returning None on missing / invalid."""
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


class VenueHandler(ABC):
    """Abstract base class for venue-specific FIX message handling."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the venue name."""
        pass

    @property
    @abstractmethod
    def sender_comp_ids(self) -> list[str]:
        """Return list of SenderCompID values that identify this venue."""
        pass

    @property
    def custom_tags(self) -> list[FixFieldDefinition]:
        """Return list of venue-specific custom tag definitions."""
        return []

    def enhance_message(self, message: FixMessage) -> FixMessage:
        """Enhance the parsed message with venue-specific information."""
        message.venue = self.name
        return message

    def extract_trade(self, message: FixMessage) -> ParsedTrade:
        """Extract high-level trade information from a FIX message."""
        trade = ParsedTrade(venue=self.name)
        msg_type = message.msg_type

        # Extract common fields. Tag 55 may be missing or a sentinel
        # ("[N/A]") on venues like SGX Titan OTC that put the product code
        # in tag 48 (SecurityID); fall back to 48 -> 107 (SecurityDesc) ->
        # 1227 (ProductComplex).
        symbol = message.get_value(55)
        if symbol and symbol.strip() and symbol != "[N/A]":
            trade.symbol = symbol
        else:
            trade.symbol = (
                message.get_value(48) or message.get_value(107) or message.get_value(1227)
            )

        # Handle different message types
        if msg_type == "S":  # Quote
            self._extract_quote_info(message, trade)
        elif msg_type == "R":  # Quote Request
            self._extract_quote_request_info(message, trade)
        else:  # Execution Report, Orders, etc.
            self._extract_execution_info(message, trade)

        trade.currency = message.get_value(15) or message.get_value(
            8021
        )  # Currency or DealCurrency
        trade.settlement_date = message.get_value(64)
        trade.order_id = message.get_value(37) or message.get_value(11)  # OrderID or ClOrdID
        trade.exec_id = message.get_value(17)
        trade.trade_date = message.get_value(75)
        trade.settlement_currency = message.get_value(120)

        return trade

    def _extract_execution_info(self, message: FixMessage, trade: ParsedTrade) -> None:
        """Extract info from Execution Reports and Orders."""
        side_field = message.get_field(54)
        if side_field:
            trade.side = side_field.value_description or side_field.raw_value

        # Try LastQty (32) first (for executions), then OrderQty (38) (for orders)
        quantity_str = message.get_value(32) or message.get_value(38)
        if quantity_str:
            try:
                trade.quantity = float(quantity_str)
            except ValueError:
                pass

        # Try LastPx (31) first (for executions), then Price (44) (for orders)
        price_str = message.get_value(31) or message.get_value(44)
        if price_str:
            try:
                trade.price = float(price_str)
            except ValueError:
                pass

        # Swap-shaped execution/order: presence of SettlDate2 (193) or
        # OrderQty2 (192) marks two-leg structure.
        if message.get_value(193) or message.get_value(192):
            self._extract_swap_execution_info(message, trade, side_field)

    def _extract_swap_execution_info(
        self,
        message: FixMessage,
        trade: ParsedTrade,
        side_field: object,
    ) -> None:
        """Populate swap-specific fields for an order/execution.

        Near leg comes from the standard tags (44 Price / 31 LastPx,
        32 LastQty / 38 OrderQty, 64 SettlDate). Far leg comes from
        640 Price2 / OrderQty2 (192) / SettlDate2 (193), with venue
        fallbacks for Smart Trade (LastPx2 9091, LastQty2 9092).
        """
        trade.is_swap = True

        # Currencies
        base, term = parse_symbol(trade.symbol)
        trade.base_currency = base
        trade.term_currency = term
        trade_ccy = message.get_value(15)
        if trade_ccy:
            trade.trade_currency = trade_ccy

        # Settlement dates
        trade.far_settlement_date = message.get_value(193)

        # Near leg
        near_price_str = message.get_value(31) or message.get_value(44)
        near_qty_str = message.get_value(32) or message.get_value(38)
        trade.near_leg_price = _to_float(near_price_str)
        trade.near_quantity = _to_float(near_qty_str)

        # Far leg — FIX 4.4 Price2/OrderQty2, plus Smart Trade fallbacks
        far_price_str = message.get_value(640) or message.get_value(9091)
        far_qty_str = message.get_value(192) or message.get_value(9092)
        trade.far_leg_price = _to_float(far_price_str)
        trade.far_quantity = _to_float(far_qty_str)

        # Spot rate: tag 194 LastSpotRate is the fill spot rate for the
        # swap (a swap has a single common spot anchoring both legs).
        # Falls back to the near leg price, which equals the spot rate
        # when near = spot date.
        spot_str = message.get_value(194)
        trade.spot_rate = _to_float(spot_str) if spot_str else trade.near_leg_price

        # Swap points per LFX spec (page 45 ExecutionReport): tag 195
        # LastForwardPoints is the *near* leg forward points and tag 641
        # LastForwardPoints2 is the *far* leg forward points. Therefore
        # 195 alone is NOT swap points. The cleanest derivation is the
        # all-in price difference (far - near, which equals far_fwd -
        # near_fwd algebraically). Fall back to (641 - 195) when both
        # individual forward points are given but no Price2 is.
        if trade.far_leg_price is not None and trade.near_leg_price is not None:
            trade.swap_points = trade.far_leg_price - trade.near_leg_price
        else:
            near_fwd = _to_float(message.get_value(195))
            far_fwd = _to_float(message.get_value(641))
            if near_fwd is not None and far_fwd is not None:
                trade.swap_points = far_fwd - near_fwd

        # Pip conversion
        ps = pip_size(trade.symbol)
        trade.pip_size = ps
        if trade.swap_points is not None and ps:
            trade.swap_points_pips = trade.swap_points / ps

        # Side semantics
        side_code = side_field.raw_value if side_field is not None else None
        near_action, far_action = swap_side_actions(
            side_code, trade.trade_currency, base, term
        )
        trade.near_leg_action = near_action
        trade.far_leg_action = far_action

    def _extract_quote_info(self, message: FixMessage, trade: ParsedTrade) -> None:
        """Extract info from Quote messages (35=S)."""
        trade.is_quote = True

        # Extract bid/offer prices
        bid_px = message.get_value(132)
        offer_px = message.get_value(133)

        if bid_px:
            try:
                trade.bid_price = float(bid_px)
            except ValueError:
                pass
        if offer_px:
            try:
                trade.offer_price = float(offer_px)
            except ValueError:
                pass

        # Extract bid/offer sizes
        bid_size = message.get_value(134)
        offer_size = message.get_value(135)
        if bid_size:
            try:
                trade.bid_size = float(bid_size)
                trade.quantity = trade.bid_size  # Use bid size as default quantity
            except ValueError:
                pass
        if offer_size:
            try:
                trade.offer_size = float(offer_size)
            except ValueError:
                pass

        # Extract spot rates
        bid_spot = message.get_value(188)
        offer_spot = message.get_value(190)
        if bid_spot:
            try:
                trade.bid_spot_rate = float(bid_spot)
            except ValueError:
                pass
        if offer_spot:
            try:
                trade.offer_spot_rate = float(offer_spot)
            except ValueError:
                pass

        # Extract forward points (near leg)
        bid_fwd_pts = message.get_value(189)
        offer_fwd_pts = message.get_value(191)
        if bid_fwd_pts:
            try:
                trade.bid_fwd_points = float(bid_fwd_pts)
            except ValueError:
                pass
        if offer_fwd_pts:
            try:
                trade.offer_fwd_points = float(offer_fwd_pts)
            except ValueError:
                pass

        # Check if this is a swap (has far leg settlement date)
        far_settl_date = message.get_value(193)
        if far_settl_date:
            trade.is_swap = True
            trade.far_settlement_date = far_settl_date

            # Far leg forward points
            far_bid_fwd_pts = message.get_value(642)
            far_offer_fwd_pts = message.get_value(643)
            if far_bid_fwd_pts:
                try:
                    trade.far_bid_fwd_points = float(far_bid_fwd_pts)
                except ValueError:
                    pass
            if far_offer_fwd_pts:
                try:
                    trade.far_offer_fwd_points = float(far_offer_fwd_pts)
                except ValueError:
                    pass

            # Swap points
            bid_swap_pts = message.get_value(1065)
            offer_swap_pts = message.get_value(1066)
            if bid_swap_pts:
                try:
                    trade.bid_swap_points = float(bid_swap_pts)
                except ValueError:
                    pass
            if offer_swap_pts:
                try:
                    trade.offer_swap_points = float(offer_swap_pts)
                except ValueError:
                    pass

            # All-in rates (custom tags)
            near_bid_rate = message.get_value(8011)
            near_offer_rate = message.get_value(8012)
            far_bid_rate = message.get_value(8019)
            far_offer_rate = message.get_value(8020)
            if near_bid_rate:
                try:
                    trade.near_leg_bid_rate = float(near_bid_rate)
                except ValueError:
                    pass
            if near_offer_rate:
                try:
                    trade.near_leg_offer_rate = float(near_offer_rate)
                except ValueError:
                    pass
            if far_bid_rate:
                try:
                    trade.far_leg_bid_rate = float(far_bid_rate)
                except ValueError:
                    pass
            if far_offer_rate:
                try:
                    trade.far_leg_offer_rate = float(far_offer_rate)
                except ValueError:
                    pass

        # Set display values
        if trade.bid_price and trade.offer_price:
            trade.side = "Two-Way"
        elif trade.bid_price:
            trade.side = "Bid Only"
        elif trade.offer_price:
            trade.side = "Offer Only"

        # Use mid price for single price display
        if trade.bid_price and trade.offer_price:
            trade.price = (trade.bid_price + trade.offer_price) / 2
        elif trade.bid_price:
            trade.price = trade.bid_price
        elif trade.offer_price:
            trade.price = trade.offer_price

    def _extract_quote_request_info(self, message: FixMessage, trade: ParsedTrade) -> None:
        """Extract info from Quote Request messages (35=R)."""
        side_field = message.get_field(54)
        if side_field:
            trade.side = side_field.value_description or side_field.raw_value
        else:
            trade.side = "Request"

        quantity_str = message.get_value(38)  # OrderQty
        if quantity_str:
            try:
                trade.quantity = float(quantity_str)
            except ValueError:
                pass

    def matches_sender(self, sender_comp_id: str | None) -> bool:
        """Check if a SenderCompID matches this venue."""
        if not sender_comp_id:
            return False
        return sender_comp_id.upper() in [s.upper() for s in self.sender_comp_ids]
