"""FxFixParser CLI - Parse FIX messages from the command line."""

import json
import os
import sys

# Add src to path so imports work when running directly
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from fxfixparser.core.exceptions import ChecksumError, ParseError, ValidationError
from fxfixparser.core.parser import FixParser, ParserConfig
from fxfixparser.products.base import ProductRegistry
from fxfixparser.venues.registry import VenueRegistry


def parse_and_display(raw_message: str, output_format: str, venue_name: str | None,
                      strict_checksum: bool, strict_body_length: bool) -> bool:
    """Parse a FIX message and display the result. Returns True on success."""
    config = ParserConfig(
        strict_checksum=strict_checksum,
        strict_body_length=strict_body_length,
    )
    parser = FixParser(config=config)
    venue_registry = VenueRegistry.default()
    product_registry = ProductRegistry.default()

    try:
        message = parser.parse(raw_message, venue=venue_name)

        # Auto-detect venue from SenderCompID if not specified
        venue_handler = None
        if venue_name is None:
            venue_handler = venue_registry.get_by_sender_id(message.sender_comp_id)
            if venue_handler:
                message = venue_handler.enhance_message(message)
        else:
            venue_handler = venue_registry.get(venue_name)

        # Detect product type
        product_handler = product_registry.detect(message)
        if product_handler:
            message.product_type = product_handler.product_type

        # Output based on format
        if output_format == "json":
            print(json.dumps(message.to_dict(), indent=2))
        elif output_format == "table":
            print_table(message)
        else:
            print(message.to_human_readable())

        # Print trade summary if venue detected
        if venue_handler:
            trade = venue_handler.extract_trade(message)
            print()
            print_trade_summary(trade, message)

        return True

    except ChecksumError as e:
        print(f"Checksum Error: {e}", file=sys.stderr)
    except ValidationError as e:
        print(f"Validation Error: {e}", file=sys.stderr)
    except ParseError as e:
        print(f"Parse Error: {e}", file=sys.stderr)
    return False


def print_table(message):
    """Print parsed fields as an aligned table."""
    rows = []
    for sf in message.get_structured_fields():
        if not sf.is_group and sf.field:
            f = sf.field
            rows.append((str(f.tag), f.name, f.raw_value, f.value_description or ""))

    if not rows:
        return

    # Calculate column widths
    headers = ("Tag", "Field", "Value", "Description")
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*headers))
    print(fmt.format(*("-" * w for w in widths)))
    for row in rows:
        print(fmt.format(*row))

    # Print repeating groups
    for sf in message.get_structured_fields():
        if sf.is_group and sf.group:
            group = sf.group
            print(f"\n{group.count_field.name} ({group.count_field.tag}): {group.count} entries")
            print("=" * 40)
            for entry in group.entries:
                print(f"  [Entry {entry.index}]")
                for f in entry.fields:
                    print(f"    {f.tag:<6} {f.name:<30} {f.raw_value:<20} {f.value_description or ''}")


def print_trade_summary(trade, message):
    """Print a trade summary to the terminal."""
    print("-" * 50)
    if trade.is_quote:
        print("Quote Summary")
        print(f"  Symbol:   {trade.symbol or 'N/A'}")
        print(f"  Currency: {trade.currency or 'N/A'}")
        print(f"  Quantity: {trade.quantity:,.0f}" if trade.quantity else "  Quantity: N/A")
        print(f"  Product:  {message.product_type or 'N/A'}")

        if trade.is_swap:
            near_tenor = message.get_value(63) or "Near"
            far_tenor = message.get_value(8004) or message.get_value(8005) or "Far"

            print(f"\n  {near_tenor} Leg:")
            print(f"    Bid  Spot: {trade.bid_spot_rate:.5f}" if trade.bid_spot_rate else "    Bid  Spot: N/A")
            print(f"    Ask  Spot: {trade.offer_spot_rate:.5f}" if trade.offer_spot_rate else "    Ask  Spot: N/A")
            print(f"    Bid  Fwd Pts: {trade.bid_fwd_points:+.6f}" if trade.bid_fwd_points is not None else "    Bid  Fwd Pts: N/A")
            print(f"    Ask  Fwd Pts: {trade.offer_fwd_points:+.6f}" if trade.offer_fwd_points is not None else "    Ask  Fwd Pts: N/A")
            print(f"    Bid  All-in: {trade.near_leg_bid_rate:.6f}" if trade.near_leg_bid_rate else "    Bid  All-in: N/A")
            print(f"    Ask  All-in: {trade.near_leg_offer_rate:.6f}" if trade.near_leg_offer_rate else "    Ask  All-in: N/A")

            print(f"\n  {far_tenor} Leg:")
            print(f"    Bid  Fwd Pts: {trade.far_bid_fwd_points:+.6f}" if trade.far_bid_fwd_points is not None else "    Bid  Fwd Pts: N/A")
            print(f"    Ask  Fwd Pts: {trade.far_offer_fwd_points:+.6f}" if trade.far_offer_fwd_points is not None else "    Ask  Fwd Pts: N/A")
            print(f"    Bid  All-in: {trade.far_leg_bid_rate:.6f}" if trade.far_leg_bid_rate else "    Bid  All-in: N/A")
            print(f"    Ask  All-in: {trade.far_leg_offer_rate:.6f}" if trade.far_leg_offer_rate else "    Ask  All-in: N/A")

            print(f"\n  Swap Points:")
            print(f"    Bid:   {trade.bid_swap_points:+.6f}" if trade.bid_swap_points is not None else "    Bid:   N/A")
            print(f"    Offer: {trade.offer_swap_points:+.6f}" if trade.offer_swap_points is not None else "    Offer: N/A")
        else:
            print(f"\n  Bid:   {trade.bid_price:.5f}" if trade.bid_price else "\n  Bid:   N/A")
            print(f"  Offer: {trade.offer_price:.5f}" if trade.offer_price else "  Offer: N/A")
    else:
        print("Trade Summary")
        print(f"  Symbol:   {trade.symbol or 'N/A'}")
        print(f"  Side:     {trade.side or 'N/A'}")
        print(f"  Quantity: {trade.quantity:,.2f}" if trade.quantity else "  Quantity: N/A")
        print(f"  Price:    {trade.price:.5f}" if trade.price else "  Price:    N/A")
        print(f"  Venue:    {trade.venue or 'N/A'}")
        print(f"  Product:  {message.product_type or 'N/A'}")


def interactive_mode(output_format: str, venue_name: str | None,
                     strict_checksum: bool, strict_body_length: bool) -> None:
    """Run the parser in interactive mode, prompting for messages."""
    print("FxFixParser CLI - Interactive Mode")
    print("Paste a FIX message and press Enter to parse. Type 'quit' to exit.\n")

    while True:
        try:
            raw = input("FIX> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not raw or raw.lower() in ("quit", "exit", "q"):
            break

        parse_and_display(raw, output_format, venue_name, strict_checksum, strict_body_length)
        print()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="FxFixParser - Parse FIX 4.4 protocol messages for FX trading",
    )
    parser.add_argument("message", nargs="?", help="FIX message string to parse")
    parser.add_argument("-f", "--file", help="Read FIX message from a file")
    parser.add_argument("-o", "--output", choices=["human", "table", "json"], default="human",
                        help="Output format (default: human)")
    parser.add_argument("-v", "--venue", help="Venue name (auto-detected if not specified)")
    parser.add_argument("--strict-checksum", action="store_true", help="Enable strict checksum validation")
    parser.add_argument("--strict-body-length", action="store_true", help="Enable strict body length validation")

    args = parser.parse_args()

    # Determine input source
    if args.message:
        raw = args.message
    elif args.file:
        with open(args.file) as fh:
            raw = fh.read().strip()
    elif not sys.stdin.isatty():
        raw = sys.stdin.read().strip()
    else:
        interactive_mode(args.output, args.venue, args.strict_checksum, args.strict_body_length)
        return

    success = parse_and_display(raw, args.output, args.venue, args.strict_checksum, args.strict_body_length)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
