"""FX math helpers — symbol parsing, pip sizing, swap-side semantics."""

from __future__ import annotations


def parse_symbol(symbol: str | None) -> tuple[str | None, str | None]:
    """Split an FX symbol into (base, term).

    Accepts "USD/CNH" or "USDCNH" forms. Returns (None, None) if it cannot
    be split into two ISO-like 3-letter codes.
    """
    if not symbol:
        return (None, None)
    s = symbol.strip().upper()
    if "/" in s:
        parts = s.split("/", 1)
        base, term = parts[0].strip(), parts[1].strip()
        if base and term:
            return (base, term)
        return (None, None)
    if len(s) == 6 and s.isalpha():
        return (s[:3], s[3:])
    return (None, None)


# Quote currencies whose rates are conventionally quoted to two decimal places,
# so a pip is 0.01 rather than 0.0001 (e.g. USD/JPY 148.50, USD/KRW 1320.50).
_TWO_DP_QUOTE_CCYS = {"JPY", "KRW"}


def pip_size(symbol: str | None) -> float:
    """Return the pip size for a currency pair.

    Pairs quoted to two decimals (term currency JPY or KRW) use 0.01; everything
    else uses 0.0001.
    """
    _, term = parse_symbol(symbol)
    if term in _TWO_DP_QUOTE_CCYS:
        return 0.01
    return 0.0001


def swap_side_actions(
    side_code: str | None,
    trade_currency: str | None,
    base: str | None,
    term: str | None,
) -> tuple[str | None, str | None]:
    """Return (near_action, far_action) strings for a swap.

    Convention: Side describes the action on the FAR leg in the trade
    currency. Near leg is the opposite. The returned strings name the
    trade currency (e.g. "Sell USD", "Buy CNH"). When the trade currency
    is the term currency, an extra base-equivalent is appended:
    "Buy CNH (Sell USD)".
    """
    if side_code not in ("1", "2"):
        return (None, None)
    if not trade_currency:
        return (None, None)

    trade_ccy = trade_currency.upper()
    far_verb = "Buy" if side_code == "1" else "Sell"
    near_verb = "Sell" if side_code == "1" else "Buy"

    def _format(verb: str, other_verb: str) -> str:
        action = f"{verb} {trade_ccy}"
        if base and term and trade_ccy == term:
            action += f" ({other_verb} {base})"
        return action

    near_action = _format(near_verb, far_verb)
    far_action = _format(far_verb, near_verb)
    return (near_action, far_action)


def classify_forward_points(
    declared: float | None,
    all_in: float | None,
    spot: float | None,
    pip: float | None,
    tol_pips: float = 0.03,
) -> tuple[str, float] | None:
    """Classify a declared forward-points value against its own quote.

    Venue specs (e.g. Bloomberg ORP/DOR) define forward-point tags as an
    unscaled decimal rate offset (8 pips on EUR/USD = 0.0008), but feeds
    are routinely observed sending market-convention pips (8) instead.
    This compares ``declared`` with the offset implied by the quote's own
    all-in rate and spot rate (``all_in - spot``) under both readings.

    Returns ``(convention, declared_in_pips)`` where ``convention`` is
    ``"decimal"`` or ``"pips"`` — the spec-compliant decimal reading wins
    when both fit (only possible near zero). Returns ``None`` when any
    input is missing, or when the declared value matches neither reading
    within ``tol_pips`` — i.e. the vendor's forward points disagree with
    the vendor's own all-in and spot rates.
    """
    if declared is None or all_in is None or spot is None or not pip:
        return None
    implied_pips = (all_in - spot) / pip
    if abs(declared / pip - implied_pips) <= tol_pips:
        return ("decimal", declared / pip)
    if abs(declared - implied_pips) <= tol_pips:
        return ("pips", declared)
    return None


def swap_quote_directions(
    bid_points: float | None,
    offer_points: float | None,
    base_currency: str | None = None,
) -> tuple[str | None, str | None]:
    """Label the price taker's direction on each side of a 2-way swap quote.

    In a coherent two-way FX swap quote, the side whose far-minus-near
    all-in differential is algebraically higher is the package where the
    maker sells the base currency on the far leg — i.e. the taker sells
    the base on the near leg and buys it back on the far leg (S/B); the
    other side is the reverse (B/S). Any other assignment would have the
    maker paying its own bid/offer spread to the taker in both
    directions, so the mapping is forced by the numbers and holds no
    matter which leg the venue's Bid/Offer labels anchor to: feeds
    labelled from the near leg (Bloomberg DOR's observed two-sided
    shape) show bid points above offer points, while points-market feeds
    labelled from the far leg show the same two-way with bid below
    offer.

    Returns ``(bid_direction, offer_direction)``, or ``(None, None)``
    when either side is missing or both sides are equal (a choice price
    carries no direction information).
    """
    if bid_points is None or offer_points is None or bid_points == offer_points:
        return (None, None)
    ccy = base_currency or "base"
    sell_buy = f"Sell {ccy} near / buy {ccy} far (S/B)"
    buy_sell = f"Buy {ccy} near / sell {ccy} far (B/S)"
    if bid_points > offer_points:
        return (sell_buy, buy_sell)
    return (buy_sell, sell_buy)
