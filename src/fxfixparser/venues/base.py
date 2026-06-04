"""Abstract base class for venue handlers."""

from abc import ABC, abstractmethod

from fxfixparser.core.field import FixField, FixFieldDefinition
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


def _extract_leg_entries(message: FixMessage) -> list[dict[str, str]]:
    """Return parsed entries from the NoLegs (555) repeating group.

    Each entry is a {tag_str: value} dict containing only the tags
    present in that leg. Returns an empty list when no leg group is in
    the message.
    """
    entries: list[dict[str, str]] = []
    for sf in message.get_structured_fields():
        if sf.is_group and sf.group and sf.group.count_field.tag == 555:
            for entry in sf.group.entries:
                entries.append({str(f.tag): f.raw_value for f in entry.fields})
            break
    return entries


def _order_legs_near_far(
    legs: list[dict[str, str]],
) -> tuple[dict[str, str], dict[str, str]]:
    """Order leg entries as (near, far) by LegSettlDate (588).

    Falls back to the original group order when dates are missing or
    equal — venues typically emit near leg first.
    """
    dated = [(leg.get("588"), idx, leg) for idx, leg in enumerate(legs)]
    if all(d for d, _, _ in dated):
        # All have dates — sort by date, tie-break by original index
        dated.sort(key=lambda t: (t[0], t[1]))
    else:
        dated.sort(key=lambda t: t[1])
    return dated[0][2], dated[-1][2]


def _leg_action(leg: dict[str, str], base: str | None, term: str | None) -> str | None:
    """Build a leg action string from an explicit LegSide (624).

    LegCurrency (556) names the currency the side applies to. When the
    leg currency is the term currency, append the base-equivalent
    interpretation in parentheses.
    """
    side = leg.get("624")
    if side not in ("1", "2"):
        return None
    leg_ccy = (leg.get("556") or base or "").upper()
    if not leg_ccy:
        return None
    verb = "Buy" if side == "1" else "Sell"
    other = "Sell" if side == "1" else "Buy"
    action = f"{verb} {leg_ccy}"
    if base and term and leg_ccy == term:
        action += f" ({other} {base})"
    return action


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

    @property
    def enum_extensions(self) -> dict[int, dict[str, str]]:
        """Return venue-specific enum values to merge into existing field definitions.

        Use this to add proprietary enum codes (e.g. Bloomberg's PartySubIDType
        4025 = Legal Entity Identifier) without replacing the standard values
        for that tag. Mapping: ``{tag: {raw_value: description}}``.
        """
        return {}

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
        # Prefer an existing value (e.g. set from the NoLegs group for
        # swap shape (b)) over the tag-64 fallback.
        trade.settlement_date = trade.settlement_date or message.get_value(64)
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

        # Swap-shaped execution/order. Two industry-standard shapes:
        #   (a) Side-by-side fields: SettlDate2 (193) / OrderQty2 (192) /
        #       Price2 (640). Used by Smart Trade, FXGO, 360T.
        #   (b) NoLegs (555) repeating group with per-leg LegSide /
        #       LegSettlDate / LegLastPx. Used by Bloomberg DOR.
        leg_entries = _extract_leg_entries(message)
        if message.get_value(193) or message.get_value(192) or len(leg_entries) >= 2:
            self._extract_swap_execution_info(message, trade, side_field, leg_entries)

    def _extract_swap_execution_info(
        self,
        message: FixMessage,
        trade: ParsedTrade,
        side_field: FixField | None,
        leg_entries: list[dict[str, str]],
    ) -> None:
        """Populate swap-specific fields for an order/execution.

        Supports both swap shapes — side-by-side near/far tags
        (193/192/640) and the NoLegs (555) repeating group form.
        """
        trade.is_swap = True

        # Currencies
        base, term = parse_symbol(trade.symbol)
        trade.base_currency = base
        trade.term_currency = term
        trade_ccy = message.get_value(15)
        if trade_ccy:
            trade.trade_currency = trade_ccy

        # Leg data: prefer the explicit NoLegs group when present
        # because legs may carry their own sides; otherwise use the
        # parent tag shape.
        leg_near_action: str | None = None
        leg_far_action: str | None = None
        if len(leg_entries) >= 2:
            near, far = _order_legs_near_far(leg_entries)
            trade.settlement_date = near.get("588") or trade.settlement_date
            trade.far_settlement_date = far.get("588")
            trade.near_leg_price = _to_float(near.get("637") or near.get("566"))
            trade.far_leg_price = _to_float(far.get("637") or far.get("566"))
            trade.near_quantity = _to_float(near.get("687"))
            trade.far_quantity = _to_float(far.get("687"))
            # If the legs carry explicit sides, use them directly so we
            # don't need to derive from the parent Side tag.
            leg_near_action = _leg_action(near, base, term)
            leg_far_action = _leg_action(far, base, term)
        else:
            trade.far_settlement_date = message.get_value(193)
            near_price_str = message.get_value(31) or message.get_value(44)
            near_qty_str = message.get_value(32) or message.get_value(38)
            trade.near_leg_price = _to_float(near_price_str)
            trade.near_quantity = _to_float(near_qty_str)
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

        # Swap points precedence:
        #   1. Compute from far_price - near_price when both are known —
        #      most robust, works for any venue.
        #   2. Explicit tag 1071 LastSwapPoints (Bloomberg DOR, FIX 5.0).
        #   3. (641 - 195) when individual forward points are given but
        #      no Price2 is (LFX spec page 45 ExecutionReport).
        if trade.far_leg_price is not None and trade.near_leg_price is not None:
            trade.swap_points = trade.far_leg_price - trade.near_leg_price
        else:
            explicit = _to_float(message.get_value(1071))
            if explicit is not None:
                trade.swap_points = explicit
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

        # Side semantics — leg-level sides win when available; otherwise
        # derive from the parent Side tag using the trade currency.
        if leg_near_action and leg_far_action:
            trade.near_leg_action = leg_near_action
            trade.far_leg_action = leg_far_action
            trade.swap_side_source = "legs"
        else:
            side_code = side_field.raw_value if side_field is not None else None
            near_action, far_action = swap_side_actions(side_code, trade.trade_currency, base, term)
            trade.near_leg_action = near_action
            trade.far_leg_action = far_action
            if near_action or far_action:
                trade.swap_side_source = "parent"

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

    def claims_message(self, message: FixMessage) -> bool:
        """Return True if this handler recognises the message by its protocol
        or content, independent of CompID matching.

        ``VenueRegistry.detect_from_message`` consults this before falling back
        to CompID matching, letting a handler claim a message whose CompID is
        generic or ambiguous. The default abstains; only venues with a
        distinctive on-wire dialect override it.
        """
        return False
