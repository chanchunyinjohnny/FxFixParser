"""Abstract base class for venue handlers."""

from abc import ABC, abstractmethod

from fxfixparser.core.field import FixFieldDefinition
from fxfixparser.core.message import FixMessage, ParsedTrade


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

        # Extract common fields
        symbol = message.get_value(55)
        if symbol:
            trade.symbol = symbol

        # Handle different message types
        if msg_type == "S":  # Quote
            self._extract_quote_info(message, trade)
        elif msg_type == "R":  # Quote Request
            self._extract_quote_request_info(message, trade)
        else:  # Execution Report, Orders, etc.
            self._extract_execution_info(message, trade)

        trade.currency = message.get_value(15) or message.get_value(8021)  # Currency or DealCurrency
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
