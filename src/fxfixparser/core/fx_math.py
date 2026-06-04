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
